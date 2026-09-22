"""Practice room: trade Nifty options with fake money, for as long as you like.

This is a flight simulator for the brother's real product: bought CE/PE
options. The index path comes from a fake market (see worlds.py). Option prices
come from a pricing model, so what makes real option buying hard is all here:

  * time decay: the option loses value as the clock runs, even if price stands still,
  * the bid-ask spread: you buy at the ask and sell at the bid,
  * charges on every order,
  * stops that can be jumped through by a gap,
  * and your own rules (max trades, max daily loss), which you may break, and
    which the review will then show you.

You only ever see bars up to "now", never ahead, exactly like real trading.
When a session ends, every trade is split into what the MARKET MOVE earned,
what TIME DECAY took, and what the SPREAD and CHARGES took. Most beginners
discover that being right about direction is not enough.

Everything is in fake money. Prices come from a model, so the numbers show the
SHAPE of the problem, not exact real premiums. Prices never go below Rs 0.05,
the minimum tick.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .gate import check_gate
from .journal import Journal, behavior_flags
from .options import DEFAULT_RATE, bs_price
from .sizing import NIFTY_LOT_SIZE, option_position_size

MIN_TICK = 0.05


class PracticeError(ValueError):
    """Something the player should fix: not enough money, no position, expired option."""


class PracticeBlocked(PracticeError):
    """The player's own rules say no. Buying anyway needs override=True."""

    def __init__(self, reasons: list):
        super().__init__(" ".join(reasons))
        self.reasons = reasons


@dataclass
class PracticeSettings:
    capital: float = 10000.0
    lot_size: int = NIFTY_LOT_SIZE
    iv_pct: float = 14.0
    days_to_expiry: float = 3.0            # calendar days left at the first bar of the world
    spread_points: float = 0.6             # gap between buy and sell price, in premium points
    charges_per_order: float = 40.0        # rough all-in charges per order, in rupees
    strike_step: int = 50
    rate: float = DEFAULT_RATE
    max_loss_per_trade: float = 1000.0
    max_trades_per_day: Optional[int] = 2
    max_daily_loss: Optional[float] = 1500.0


def _kind(kind: str) -> str:
    k = str(kind).strip().upper()
    if k in ("CE", "CALL"):
        return "CE"
    if k in ("PE", "PUT"):
        return "PE"
    raise PracticeError("Choose CE (a bet on up) or PE (a bet on down).")


class PracticeSession:
    def __init__(self, bars: pd.DataFrame, settings: Optional[PracticeSettings] = None, start_index: int = 20):
        self.s = settings or PracticeSettings()
        if len(bars) < start_index + 2:
            raise PracticeError("The fake market is too short for this session.")
        if self.s.capital <= 0 or self.s.lot_size < 1 or self.s.days_to_expiry <= 0 or self.s.iv_pct <= 0:
            raise PracticeError("Capital, lot size, days to expiry and IV must all be above 0.")
        self.bars = bars
        self.i = start_index
        self.t0 = bars.index[0]
        self.cash = float(self.s.capital)
        self.position: Optional[dict] = None
        self.closed: list = []
        self.journal = Journal(":memory:", check_same_thread=False)   # kept alive across dashboard reruns
        self.blocked = 0
        self.overrides = 0

    # ------------------------------------------------------------------ time and prices
    @property
    def now(self) -> pd.Timestamp:
        return self.bars.index[self.i]

    @property
    def spot(self) -> float:
        return float(self.bars["close"].iloc[self.i])

    def revealed(self) -> pd.DataFrame:
        """The bars you are allowed to see: everything up to now, nothing ahead."""
        return self.bars.iloc[: self.i + 1]

    @property
    def at_end(self) -> bool:
        return self.i >= len(self.bars) - 1

    def dte(self, ts=None) -> float:
        ts = self.now if ts is None else ts
        return max(self.s.days_to_expiry - (ts - self.t0).total_seconds() / 86400.0, 0.0)

    @property
    def expired(self) -> bool:
        return self.dte() <= 0.0

    def atm_strike(self) -> int:
        step = self.s.strike_step
        return int(round(self.spot / step) * step)

    def strikes(self, each_side: int = 5) -> list:
        atm = self.atm_strike()
        return [atm + k * self.s.strike_step for k in range(-each_side, each_side + 1)]

    def mid(self, kind: str, strike: float, spot: Optional[float] = None, ts=None, dte: Optional[float] = None) -> float:
        d = self.dte(ts) if dte is None else dte
        price = bs_price(self.spot if spot is None else spot, strike, d, self.s.iv_pct / 100.0,
                         "call" if _kind(kind) == "CE" else "put", self.s.rate)
        return max(price, 0.0)

    def quote(self, kind: str, strike: float) -> tuple:
        """(bid, ask). You buy at the ask and sell at the bid."""
        mid = self.mid(kind, strike)
        if self.expired:
            return max(mid, MIN_TICK), max(mid, MIN_TICK)
        half = self.s.spread_points / 2.0
        return max(mid - half, MIN_TICK), max(mid + half, MIN_TICK)

    def premium_history(self, kind: str, strike: float, last: int = 150) -> pd.Series:
        rows = self.bars.iloc[max(0, self.i + 1 - last): self.i + 1]
        values = [self.mid(kind, strike, spot=float(r.close), ts=ts) for ts, r in rows.iterrows()]
        return pd.Series(values, index=rows.index, name=f"{kind} {strike} premium")

    def suggested_lots(self, kind: str, strike: float, stop_premium: float):
        _, ask = self.quote(kind, strike)
        try:
            return option_position_size(self.s.max_loss_per_trade, ask, stop_premium, self.s.lot_size,
                                        capital=self.cash, est_charges=2 * self.s.charges_per_order)
        except ValueError:
            return None

    # ------------------------------------------------------------------ trading
    def buy(self, kind: str, strike: float, lots: int, stop_premium: Optional[float] = None,
            override: bool = False, setup: str = "") -> dict:
        kind = _kind(kind)
        if self.position:
            raise PracticeError("Close the open position first (this room allows one at a time).")
        if self.expired:
            raise PracticeError("The option has expired. The session is effectively over.")
        if int(lots) != lots or lots < 1:
            raise PracticeError("Lots must be a whole number, 1 or more.")
        bid, ask = self.quote(kind, strike)
        qty = int(lots) * self.s.lot_size
        cost = ask * qty + self.s.charges_per_order
        if cost > self.cash:
            raise PracticeError(f"Not enough money: this needs Rs {cost:,.0f} and you have Rs {self.cash:,.0f}.")
        if stop_premium is not None and not (0 < stop_premium < ask):
            raise PracticeError(f"The stop must be above 0 and below the price you pay ({ask:.2f}).")

        gate = check_gate(self.journal, self.now.date(), self.s.max_trades_per_day, self.s.max_daily_loss)
        warnings = []
        if not gate.allowed:
            if not override:
                self.blocked += 1
                raise PracticeBlocked(gate.reasons)
            self.overrides += 1
            warnings.append("You broke your own rules: " + " ".join(gate.reasons))
        if stop_premium is None:
            warnings.append("No stop-loss was set.")
        else:
            planned = (ask - stop_premium) * qty
            if planned > self.s.max_loss_per_trade:
                warnings.append(f"If the stop is hit you lose about Rs {planned:,.0f}, more than your limit of "
                                f"Rs {self.s.max_loss_per_trade:,.0f}.")

        label = f"NIFTY {int(strike)} {kind} ({self.dte():.1f}DTE)"
        trade_id = self.journal.add_trade(label, "BUY", qty, ask, opened_at=self.now.isoformat(sep=" "),
                                          stop_price=stop_premium, setup=setup)
        self.cash -= cost
        self.position = {
            "id": trade_id, "label": label, "kind": kind, "strike": int(strike), "lots": int(lots), "qty": qty,
            "entry_ts": self.now, "entry_price": ask, "entry_mid": self.mid(kind, strike), "entry_spot": self.spot,
            "entry_dte": self.dte(), "stop": stop_premium, "charges_in": self.s.charges_per_order,
        }
        return {"trade_id": trade_id, "price": ask, "qty": qty, "cost": cost, "warnings": warnings}

    def _exit(self, price: float, reason: str, spot_at_exit: float, half_spread: float) -> dict:
        pos = self.position
        price = max(price, MIN_TICK)
        charges_out = self.s.charges_per_order
        qty, kind, strike = pos["qty"], pos["kind"], pos["strike"]
        side = "call" if kind == "CE" else "put"
        iv, r = self.s.iv_pct / 100.0, self.s.rate
        # Split the result exactly into: market move + time (everything else the fair price did) + spread + charges.
        move = (bs_price(spot_at_exit, strike, pos["entry_dte"], iv, side, r)
                - bs_price(pos["entry_spot"], strike, pos["entry_dte"], iv, side, r)) * qty
        total_mid_change = (price + half_spread - pos["entry_mid"]) * qty
        spread_cost = -((pos["entry_price"] - pos["entry_mid"]) + half_spread) * qty
        charges = -(pos["charges_in"] + charges_out)
        gross = (price - pos["entry_price"]) * qty
        record = {
            "id": pos["id"], "label": pos["label"], "kind": kind, "strike": strike, "lots": pos["lots"], "qty": qty,
            "entry_ts": pos["entry_ts"], "exit_ts": self.now, "entry_price": pos["entry_price"], "exit_price": price,
            "entry_spot": pos["entry_spot"], "exit_spot": spot_at_exit,
            "reason": reason, "gross": gross, "net": gross + charges, "move": move,
            "time": total_mid_change - move, "spread": spread_cost, "charges": charges,
            "held_minutes": (self.now - pos["entry_ts"]).total_seconds() / 60.0,
        }
        self.cash += price * qty - charges_out
        self.journal.close_trade(pos["id"], price, closed_at=self.now.isoformat(sep=" "),
                                 charges=pos["charges_in"] + charges_out)
        self.closed.append(record)
        self.position = None
        return record

    def close(self, reason: str = "manual") -> dict:
        if not self.position:
            raise PracticeError("There is no open position to close.")
        bid, _ = self.quote(self.position["kind"], self.position["strike"])
        half = 0.0 if self.expired else self.s.spread_points / 2.0
        return self._exit(bid, reason, self.spot, half)

    # ------------------------------------------------------------------ clock
    def _check_position(self, row) -> None:
        pos = self.position
        kind, strike, stop = pos["kind"], pos["strike"], pos["stop"]
        if self.dte() <= 0.0:                                         # expiry: settle at intrinsic value
            intrinsic = max(row.open - strike, 0.0) if kind == "CE" else max(strike - row.open, 0.0)
            self._exit(intrinsic, "expired", float(row.open), 0.0)
            return
        if stop is None:
            return
        half = self.s.spread_points / 2.0
        worst_spot = float(row.low) if kind == "CE" else float(row.high)
        worst_bid = max(self.mid(kind, strike, spot=worst_spot) - half, 0.0)
        if worst_bid <= stop:
            open_bid = max(self.mid(kind, strike, spot=float(row.open)) - half, 0.0)
            if open_bid <= stop:                                      # gapped through the stop: a worse fill
                self._exit(open_bid, "stop (gapped)", float(row.open), half)
            else:
                # The stop filled inside the bar: use the index level at which the price equals the stop,
                # so the split between market move and time decay stays exact.
                level = self._solve_spot(kind, strike, stop + half, worst_spot, float(row.open))
                self._exit(stop, "stop", level, half)

    def _solve_spot(self, kind: str, strike: float, target_mid: float, a: float, b: float) -> float:
        """Index level between a and b at which the option's fair price equals target_mid."""
        lo, hi = min(a, b), max(a, b)
        f_lo = self.mid(kind, strike, spot=lo) - target_mid
        for _ in range(60):
            mid_spot = 0.5 * (lo + hi)
            f_mid = self.mid(kind, strike, spot=mid_spot) - target_mid
            if (f_mid > 0) == (f_lo > 0):
                lo, f_lo = mid_spot, f_mid
            else:
                hi = mid_spot
        return 0.5 * (lo + hi)

    def next_bar(self) -> bool:
        """Reveal the next bar. Returns False at the end of the fake market."""
        if self.at_end:
            return False
        self.i += 1
        if self.position:
            self._check_position(self.bars.iloc[self.i])
        return True

    def advance(self, n: int) -> int:
        done = 0
        for _ in range(int(n)):
            if not self.next_bar():
                break
            done += 1
        return done

    def advance_to_day_end(self) -> int:
        day = self.now.date()
        done = 0
        while not self.at_end and self.bars.index[self.i + 1].date() == day:
            self.next_bar()
            done += 1
        return done

    # ------------------------------------------------------------------ results
    def equity(self) -> float:
        if not self.position:
            return self.cash
        bid, _ = self.quote(self.position["kind"], self.position["strike"])
        return self.cash + bid * self.position["qty"]

    def unrealized(self) -> float:
        if not self.position:
            return 0.0
        bid, _ = self.quote(self.position["kind"], self.position["strike"])
        p = self.position
        return (bid - p["entry_price"]) * p["qty"] - p["charges_in"]

    def finish(self) -> dict:
        """End the session: close any open position and build the review."""
        if self.position:
            self.close("end of session")
        flags = behavior_flags(self.journal.all_trades(), self.s.max_loss_per_trade, self.s.max_trades_per_day,
                               self.s.max_daily_loss)
        trades = self.closed
        totals = {k: sum(t[k] for t in trades) for k in ("move", "time", "spread", "charges", "net")}
        return {"trades": trades, "totals": totals, "flags": flags, "blocked": self.blocked,
                "overrides": self.overrides, "net_pnl": self.cash - self.s.capital,
                "final_equity": self.cash, "start_capital": self.s.capital}


def format_practice_report(rep: dict, regime_note: str = "") -> str:
    t = rep["totals"]
    lines = ["PRACTICE ROOM REVIEW (fake money)", "=" * 64]
    if not rep["trades"]:
        lines.append("You took no trades. Sitting out is a position too.")
    for k, tr in enumerate(rep["trades"], start=1):
        lines.append(f"#{k} {tr['label']}  {tr['lots']} lot(s), held {tr['held_minutes']:.0f} min, exit: {tr['reason']}")
        lines.append(f"    bought {tr['entry_price']:.2f}, sold {tr['exit_price']:.2f}  ->  net Rs {tr['net']:,.0f}")
        lines.append(f"    market move Rs {tr['move']:+,.0f} | time decay Rs {tr['time']:+,.0f} | "
                     f"spread Rs {tr['spread']:+,.0f} | charges Rs {tr['charges']:+,.0f}")
    lines += ["-" * 64,
              f"Net result: Rs {rep['net_pnl']:,.0f} on Rs {rep['start_capital']:,.0f} "
              f"({rep['net_pnl'] / rep['start_capital'] * 100:+.1f}%)"]
    if rep["trades"]:
        lines.append(f"Where it went: market move Rs {t['move']:+,.0f}, time decay Rs {t['time']:+,.0f}, "
                     f"spread Rs {t['spread']:+,.0f}, charges Rs {t['charges']:+,.0f}.")
        friction = t["spread"] + t["charges"]
        lines.append(f"Spread and charges alone cost Rs {-friction:,.0f}. The market had to earn that back "
                     "before you made a rupee.")
        if t["move"] > 0 and t["move"] + t["time"] <= 0:
            lines.append("You were right about direction on balance, and still lost: time decay ate the gain. "
                         "That is the option buyer's problem.")
    lines.append(f"Limit blocks: {rep['blocked']}. Times you broke your own rules on purpose: {rep['overrides']}.")
    if rep["flags"]:
        lines.append("Behaviour checks:")
        lines += [f"  ! {f}" for f in rep["flags"]]
    else:
        lines.append("Behaviour checks: no rule breaks found.")
    if regime_note:
        lines.append(regime_note)
    lines.append("Fake money, model prices: this shows the shape of the problem, not real premiums or real profit.")
    return "\n".join(lines)
