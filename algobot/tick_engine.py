"""Tick-driven CE/PE strategy engine for research and paper rehearsal.

The engine evaluates each underlying price tick instead of waiting for a candle close.
It never places broker orders. Fills are simulated from option-price columns on the
next available tick, keeping the model causal.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import pandas as pd

from .config import ConfigError

_CONTRACT_RE = re.compile(
    r"(?i)(?:^|_)(ce|pe)[_\-]?([0-9]+(?:\.[0-9]+)?)(?:[_\-]?(last_price|ltp|price))?$"
)
_CONTRACT_RE_2 = re.compile(
    r"(?i)(?:^|_)([0-9]+(?:\.[0-9]+)?)[_\-]?(ce|pe)(?:[_\-]?(last_price|ltp|price))?$"
)


@dataclass(frozen=True)
class TickContract:
    kind: str
    strike: float

    @property
    def label(self) -> str:
        strike = int(self.strike) if self.strike.is_integer() else self.strike
        return f"{self.kind} {strike}"


def _find_option_columns(df: pd.DataFrame) -> dict[TickContract, str]:
    found: dict[TickContract, str] = {}
    for col in df.columns:
        name = str(col).strip()
        match = _CONTRACT_RE.search(name)
        if match:
            kind, strike, suffix = match.groups()
            if suffix:
                found[TickContract(kind.upper(), float(strike))] = col
            continue
        match = _CONTRACT_RE_2.search(name)
        if match:
            strike, kind, suffix = match.groups()
            if suffix:
                found[TickContract(kind.upper(), float(strike))] = col
    return found


def load_tick_csv(file_obj) -> pd.DataFrame:
    """Load underlying ticks plus wide option last-price columns.

    Required:
      datetime,tick_price
    or:
      datetime,last_price

    Option columns can be CE_24500, CE_24500_last_price, PE_24500_ltp, etc.
    """
    try:
        df = pd.read_csv(file_obj)
    except Exception as exc:
        raise ConfigError(f"Could not read tick CSV: {exc}") from exc

    df.columns = [str(c).strip().lower() for c in df.columns]
    time_col = next((c for c in ("datetime", "timestamp", "time", "date") if c in df.columns), None)
    price_col = next((c for c in ("last_price", "tick_price", "ltp", "price") if c in df.columns), None)
    if time_col is None or price_col is None:
        raise ConfigError("Tick CSV needs datetime/timestamp and last_price (or tick_price/ltp).")

    try:
        df[time_col] = pd.to_datetime(df[time_col])
    except (ValueError, TypeError) as exc:
        raise ConfigError(f"Could not parse '{time_col}' as dates: {exc}") from exc

    df = df.rename(columns={time_col: "datetime", price_col: "last_price"})
    df = df.sort_values("datetime").drop_duplicates("datetime", keep="last").set_index("datetime")
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)

    df["last_price"] = pd.to_numeric(df["last_price"], errors="coerce")
    if df["last_price"].isna().any() or (df["last_price"] <= 0).any():
        raise ConfigError("Underlying last_price contains missing or non-positive values.")

    contracts = _find_option_columns(df)
    if not contracts:
        raise ConfigError(
            "No option tick columns found. Use columns like CE_24500_last_price and PE_24500_last_price."
        )
    for contract, col in contracts.items():
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _nearest_strike(spot: float, strikes: list[float], requested: float | None = None) -> float:
    if not strikes:
        raise ConfigError("No option contracts are available for the selected CE/PE side.")
    target = spot if requested is None else requested
    return min(strikes, key=lambda strike: (abs(strike - target), strike))


def run_tick_strategy(
    df: pd.DataFrame,
    *,
    contract_type: str = "CE",
    quantity: int = 1,
    strike_mode: str = "ATM",
    initial_strike: float | None = None,
    strike_step: float = 50,
    upper_trigger: float = 50,
    lower_trigger: float = 45,
    entry_time: str = "09:30",
    exit_time: str = "15:15",
    dynamic_strike: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    """Run a tick-by-tick dynamic-strike long CE/PE strategy.

    Trigger evaluation happens on every underlying tick. A trigger schedules the
    rollover for the next available tick, so the trigger tick itself is never
    treated as an executable fill.
    """
    if contract_type not in {"CE", "PE"}:
        raise ConfigError("Contract type must be CE or PE.")
    if quantity < 1 or strike_step <= 0 or upper_trigger < 0 or lower_trigger < 0:
        raise ConfigError("Quantity and strike step must be positive; triggers cannot be negative.")
    if strike_mode not in {"ATM", "FIXED"}:
        raise ConfigError("Strike mode must be ATM or FIXED.")
    if not isinstance(df.index, pd.DatetimeIndex) or df.empty:
        raise ConfigError("Tick data must have a non-empty DatetimeIndex.")

    option_columns = _find_option_columns(df)
    available = sorted(c.strike for c in option_columns if c.kind == contract_type)
    if not available:
        raise ConfigError(f"No {contract_type} option ticks are available.")

    entry_clock = pd.Timestamp(entry_time).time()
    exit_clock = pd.Timestamp(exit_time).time()
    times = pd.to_datetime(df.index)

    def option_price(contract: TickContract, i: int) -> float:
        col = option_columns.get(contract)
        if col is None:
            raise ConfigError(f"Missing tick-price column for {contract.label}.")
        value = float(df[col].iloc[i])
        if not math.isfinite(value) or value <= 0:
            raise ConfigError(f"Invalid {contract.label} option price at {times[i]}.")
        return value

    trades: list[dict] = []
    events: list[str] = []
    position: TickContract | None = None
    entry_price: float | None = None
    entry_ts = None
    rolls = 0
    pending: TickContract | None = None

    for i, ts in enumerate(times):
        now = ts.time()

        if pending is not None:
            fill = option_price(pending, i)
            if position is None:
                position = pending
                entry_price = fill
                entry_ts = ts
                rolls = 0
            else:
                old = position
                old_fill = option_price(old, i)
                trades.append({
                    "entry_time": entry_ts,
                    "exit_time": ts,
                    "side": "LONG",
                    "contract": old.label,
                    "qty": quantity,
                    "entry_price": round(float(entry_price), 4),
                    "exit_price": round(old_fill, 4),
                    "gross_pnl": round((old_fill - float(entry_price)) * quantity, 4),
                    "rolls": rolls,
                    "exit_reason": "tick_strike_roll",
                })
                position = pending
                entry_price = fill
                entry_ts = ts
                rolls += 1
            pending = None

        if position is None:
            if entry_clock <= now < exit_clock:
                target = _nearest_strike(
                    float(df["last_price"].iloc[i]),
                    available,
                    initial_strike if strike_mode == "FIXED" else None,
                )
                pending = TickContract(contract_type, target)
            continue

        if now >= exit_clock:
            fill = option_price(position, i)
            trades.append({
                "entry_time": entry_ts,
                "exit_time": ts,
                "side": "LONG",
                "contract": position.label,
                "qty": quantity,
                "entry_price": round(float(entry_price), 4),
                "exit_price": round(fill, 4),
                "gross_pnl": round((fill - float(entry_price)) * quantity, 4),
                "rolls": rolls,
                "exit_reason": "time_exit",
            })
            position = None
            entry_price = None
            continue

        if dynamic_strike:
            spot = float(df["last_price"].iloc[i])
            current = position.strike
            target = None
            reason = None
            if spot >= current + upper_trigger:
                target = current + strike_step
                reason = "upper tick trigger"
            elif spot <= current - lower_trigger:
                target = current - strike_step
                reason = "lower tick trigger"

            candidate = TickContract(contract_type, float(target)) if target is not None else None
            if candidate is not None:
                if candidate.strike in available and candidate.strike != current:
                    pending = candidate
                    events.append(
                        f"{ts}: {position.label} -> {candidate.label} ({reason}; underlying={spot:g})"
                    )
                else:
                    events.append(
                        f"{ts}: requested {candidate.label} unavailable; kept {position.label} (underlying={spot:g})"
                    )

    if position is not None:
        fill = option_price(position, len(df) - 1)
        trades.append({
            "entry_time": entry_ts,
            "exit_time": times[-1],
            "side": "LONG",
            "contract": position.label,
            "qty": quantity,
            "entry_price": round(float(entry_price), 4),
            "exit_price": round(fill, 4),
            "gross_pnl": round((fill - float(entry_price)) * quantity, 4),
            "rolls": rolls,
            "exit_reason": "end_of_data",
        })

    return pd.DataFrame(trades), events
