"""Dynamic CE/PE option contract selection and strike-rolling backtest.

This module is deliberately separate from the normal OHLC strategy engine because an
option strategy changes the traded contract during a run. It supports real option-chain
CSV data and an explicitly labelled synthetic chain for UI/testing.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import pandas as pd

from .config import ConfigError

_OHLC = ("open", "high", "low", "close")
_CONTRACT_RE = re.compile(
    r"(?i)(?:^|_)(ce|pe)[_\-]?([0-9]+(?:\.[0-9]+)?)[_\-]?(open|high|low|close)$"
)
_CONTRACT_RE_2 = re.compile(
    r"(?i)(?:^|_)([0-9]+(?:\.[0-9]+)?)[_\-]?(ce|pe)[_\-]?(open|high|low|close)$"
)


@dataclass(frozen=True)
class OptionContract:
    kind: str
    strike: float

    @property
    def label(self) -> str:
        strike = int(self.strike) if float(self.strike).is_integer() else self.strike
        return f"{self.kind} {strike}"


def _norm_contract(kind: str, strike: str) -> OptionContract:
    return OptionContract(kind.upper(), float(strike))


def discover_contracts(df: pd.DataFrame) -> list[OptionContract]:
    found: set[OptionContract] = set()
    for col in df.columns:
        name = str(col).strip()
        match = _CONTRACT_RE.search(name)
        if match:
            found.add(_norm_contract(match.group(1), match.group(2)))
            continue
        match = _CONTRACT_RE_2.search(name)
        if match:
            found.add(_norm_contract(match.group(2), match.group(1)))
    return sorted(found, key=lambda c: (c.kind, c.strike))


def _column_candidates(contract: OptionContract, field: str) -> list[str]:
    strike = int(contract.strike) if contract.strike.is_integer() else contract.strike
    return [
        f"{contract.kind}_{strike}_{field}",
        f"{contract.kind}_{strike:g}_{field}",
        f"{strike}_{contract.kind}_{field}",
        f"{strike:g}_{contract.kind}_{field}",
    ]


def contract_columns(df: pd.DataFrame, contract: OptionContract) -> dict[str, str]:
    lower = {str(c).strip().lower(): c for c in df.columns}
    result = {}
    for field in _OHLC:
        for candidate in _column_candidates(contract, field):
            if candidate.lower() in lower:
                result[field] = lower[candidate.lower()]
                break
    if len(result) != 4:
        missing = [field for field in _OHLC if field not in result]
        raise ConfigError(f"{contract.label} is missing columns: {', '.join(missing)}")
    return result


def validate_option_chain(df: pd.DataFrame) -> list[OptionContract]:
    required = {"open", "high", "low", "close"}
    missing = required - {str(c).strip().lower() for c in df.columns}
    if missing:
        raise ConfigError(
            "The underlying data must contain open, high, low and close columns."
        )
    contracts = discover_contracts(df)
    if not contracts:
        raise ConfigError(
            "No option contracts found. Use columns like CE_24500_open, CE_24500_high, "
            "CE_24500_low, CE_24500_close and the equivalent PE columns."
        )
    for contract in contracts:
        contract_columns(df, contract)
    return contracts


def load_option_chain_csv(file_obj) -> pd.DataFrame:
    try:
        df = pd.read_csv(file_obj)
    except Exception as exc:
        raise ConfigError(f"Could not read the option-chain CSV: {exc}") from exc
    df.columns = [str(c).strip().lower() for c in df.columns]
    time_col = next((c for c in ("datetime", "timestamp", "date", "time") if c in df.columns), None)
    if time_col is None:
        raise ConfigError("The CSV needs a datetime, timestamp, date or time column.")
    try:
        df[time_col] = pd.to_datetime(df[time_col])
    except (ValueError, TypeError) as exc:
        raise ConfigError(f"Could not parse '{time_col}' as dates: {exc}") from exc
    df = df.set_index(time_col).sort_index()
    df.index.name = "datetime"
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    for field in _OHLC:
        if field not in df.columns:
            raise ConfigError(f"The underlying data is missing '{field}'.")
        df[field] = pd.to_numeric(df[field], errors="coerce")
    if df[["open", "high", "low", "close"]].isna().any().any():
        raise ConfigError("The underlying OHLC columns contain missing or non-numeric values.")
    validate_option_chain(df)
    return df


def _synthetic_option_price(spot: float, strike: float, kind: str, t: float, iv: float) -> float:
    intrinsic = max(spot - strike, 0.0) if kind == "CE" else max(strike - spot, 0.0)
    time_value = max(spot * iv * math.sqrt(max(t, 1 / 3650)) * 0.40, 0.50)
    return max(intrinsic + time_value, 0.50)


def generate_synthetic_option_chain(
    underlying: pd.DataFrame,
    strike_step: int = 50,
    strikes_each_side: int = 6,
    iv: float = 0.18,
    days_to_expiry: int = 7,
) -> pd.DataFrame:
    """Create clearly-labelled synthetic CE/PE prices for exercising the selector."""
    if strike_step <= 0 or strikes_each_side < 1 or iv <= 0 or days_to_expiry < 1:
        raise ConfigError("Synthetic-chain settings must be positive.")
    spot0 = float(underlying["close"].iloc[0])
    center = round(spot0 / strike_step) * strike_step
    strikes = [center + k * strike_step for k in range(-strikes_each_side, strikes_each_side + 1)]
    out = underlying.copy()
    expiry = pd.Timestamp(out.index[0]).normalize() + pd.Timedelta(days=days_to_expiry)
    for strike in strikes:
        for kind in ("CE", "PE"):
            for field in _OHLC:
                values = []
                for ts, row in out.iterrows():
                    remaining = max(
                        (expiry - pd.Timestamp(ts)).total_seconds() / (365.0 * 24 * 3600),
                        1 / 3650,
                    )
                    values.append(
                        _synthetic_option_price(float(row[field]), strike, kind, remaining, iv)
                    )
                out[f"{kind}_{int(strike)}_{field}"] = values
    return out


def _nearest_strike(spot: float, strikes: list[float], requested: float | None = None) -> float:
    if not strikes:
        raise ConfigError("No contracts are available for the selected CE/PE side.")
    target = spot if requested is None else requested
    return min(strikes, key=lambda strike: (abs(strike - target), strike))


def run_dynamic_strike_option_backtest(
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
    """Buy one CE/PE contract, optionally roll it as the underlying crosses strike bands.

    Signal decisions use the current completed bar. Entries and rolls execute at the
    next bar's option open. This keeps the option backtest causal and avoids using
    the current bar's close as an executable fill.
    """
    if contract_type not in {"CE", "PE"}:
        raise ConfigError("Contract type must be CE or PE.")
    if quantity < 1 or strike_step <= 0 or upper_trigger < 0 or lower_trigger < 0:
        raise ConfigError("Quantity and strike step must be positive; triggers cannot be negative.")
    if strike_mode not in {"ATM", "FIXED"}:
        raise ConfigError("Strike mode must be ATM or FIXED.")
    contracts = validate_option_chain(df)
    available = sorted({c.strike for c in contracts if c.kind == contract_type})
    if not available:
        raise ConfigError(f"No {contract_type} contracts are available in the dataset.")

    entry_clock = pd.Timestamp(entry_time).time()
    exit_clock = pd.Timestamp(exit_time).time()
    times = pd.to_datetime(df.index)
    trades: list[dict] = []
    events: list[str] = []

    def price(contract: OptionContract, i: int, field: str) -> float:
        col = contract_columns(df, contract)[field]
        value = float(df[col].iloc[i])
        if not math.isfinite(value) or value <= 0:
            raise ConfigError(f"Invalid {contract.label} {field} price at {times[i]}.")
        return value

    position: OptionContract | None = None
    pending: tuple[str, float] | None = None
    entry_price = None
    entry_time_actual = None
    entry_strike = None
    rolls = 0

    for i, ts in enumerate(times):
        current_time = ts.time()

        # Fill decisions from the previous completed bar.
        if pending is not None:
            action, target = pending
            contract = OptionContract(contract_type, target)
            open_price = price(contract, i, "open")
            if action == "ENTER":
                position = contract
                entry_price = open_price
                entry_time_actual = ts
                entry_strike = target
                rolls = 0
            else:
                old = position
                old_exit = price(old, i, "open")
                trades.append({
                    "entry_time": entry_time_actual,
                    "exit_time": ts,
                    "side": "LONG",
                    "contract": old.label,
                    "qty": quantity,
                    "entry_price": round(entry_price, 4),
                    "exit_price": round(old_exit, 4),
                    "gross_pnl": round((old_exit - entry_price) * quantity, 4),
                    "rolls": rolls,
                    "exit_reason": "strike_roll",
                })
                position = contract
                entry_price = open_price
                entry_time_actual = ts
                entry_strike = target if entry_strike is None else entry_strike
                rolls += 1
            pending = None

        if position is not None:
            if current_time >= exit_clock:
                exit_price = price(position, i, "close")
                trades.append({
                    "entry_time": entry_time_actual,
                    "exit_time": ts,
                    "side": "LONG",
                    "contract": position.label,
                    "qty": quantity,
                    "entry_price": round(entry_price, 4),
                    "exit_price": round(exit_price, 4),
                    "gross_pnl": round((exit_price - entry_price) * quantity, 4),
                    "rolls": rolls,
                    "exit_reason": "time_exit",
                })
                position = None
                entry_price = None
                continue

            if dynamic_strike:
                spot = float(df["close"].iloc[i])
                current_strike = position.strike
                target = None
                reason = ""
                if spot >= current_strike + upper_trigger:
                    target = current_strike + strike_step
                    reason = "upper trigger"
                elif spot <= current_strike - lower_trigger:
                    target = current_strike - strike_step
                    reason = "lower trigger"
                if target is not None:
                    if target in available and target != current_strike:
                        pending = ("ROLL", float(target))
                        events.append(
                            f"{ts}: {position.label} -> {contract_type} {target:g} ({reason})"
                        )
                    else:
                        events.append(
                            f"{ts}: requested {contract_type} {target:g} is unavailable; kept {position.label}"
                        )

        elif entry_clock <= current_time < exit_clock:
            spot = float(df["close"].iloc[i])
            requested = initial_strike if strike_mode == "FIXED" else None
            target = _nearest_strike(spot, available, requested)
            pending = ("ENTER", target)

    if position is not None:
        exit_price = price(position, len(df) - 1, "close")
        trades.append({
            "entry_time": entry_time_actual,
            "exit_time": times[-1],
            "side": "LONG",
            "contract": position.label,
            "qty": quantity,
            "entry_price": round(entry_price, 4),
            "exit_price": round(exit_price, 4),
            "gross_pnl": round((exit_price - entry_price) * quantity, 4),
            "rolls": rolls,
            "exit_reason": "end_of_data",
        })

    return pd.DataFrame(trades), events
