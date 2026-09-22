"""Backtest engine.

Rules of the simulation (kept deliberately conservative):

* A strategy decision is made at the CLOSE of a bar and filled at the OPEN of
  the NEXT bar of the same day. Nothing carries overnight: this is an
  intraday engine, and positions are squared off at `risk.square_off_time`.
* Market-type fills (entries, signal exits, stop-loss, square-off, kill
  switch) pay slippage. Target exits are treated as limit orders: no slippage.
* If a bar could have hit both the stop and the target, the STOP is assumed to
  have hit first (the pessimistic choice).
* If a bar gaps through a stop or target, the fill is at the open, not at the
  level you wished for.
* Every order pays the configured charges.

Not modelled yet: margin/leverage limits, partial fills, order rejections by
the broker, liquidity limits. Treat results as optimistic.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

from .costs import CostModel
from .metrics import compute_metrics
from .risk import RiskManager
from .strategy import BUY, EXIT, SELL, Strategy

TRADE_COLUMNS = [
    "entry_time", "exit_time", "side", "qty", "entry_price", "exit_price",
    "gross_pnl", "costs", "net_pnl", "exit_reason",
]


@dataclass
class BacktestResult:
    name: str
    trades: pd.DataFrame
    equity: pd.Series
    metrics: dict
    events: list = field(default_factory=list)
    rejections: dict = field(default_factory=dict)


class Backtester:
    def __init__(self, cfg: dict, strategy: Strategy):
        self.cfg = cfg
        self.strategy = strategy
        self.costs = CostModel(**cfg["costs"])
        self.risk = RiskManager(cfg["risk"])
        s = cfg["strategy"]
        self.qty: int = s["quantity"]
        self.allow_short: bool = s["allow_short"]
        self.stop_pct = s["stop_loss_pct"]
        self.target_pct = s["target_pct"]
        self.capital = float(cfg["capital"])
        self._reset_state()

    # ------------------------------------------------------------------ state
    def _reset_state(self) -> None:
        self.position = 0            # 1 long, -1 short, 0 flat
        self.entry_fill = 0.0
        self.entry_time = None
        self.entry_charges = 0.0
        self.stop = None
        self.target = None
        self.realized = 0.0          # cumulative net realised P&L (after charges)
        self.day_realized = 0.0
        self.trades: list[dict] = []
        self.events: list[str] = []
        self.rejections: Counter = Counter()

    # ---------------------------------------------------------------- actions
    def _enter(self, ts, raw_price: float, direction: int) -> None:
        side = "BUY" if direction == 1 else "SELL"
        fill = self.costs.slippage_price(raw_price, side)
        charges = self.costs.order_charges(side, fill, self.qty)
        self.realized -= charges
        self.day_realized -= charges
        self.position = direction
        self.entry_fill = fill
        self.entry_time = ts
        self.entry_charges = charges
        if self.stop_pct is not None:
            self.stop = fill * (1 - direction * self.stop_pct / 100.0)
        if self.target_pct is not None:
            self.target = fill * (1 + direction * self.target_pct / 100.0)
        self.risk.register_entry()

    def _exit(self, ts, raw_price: float, reason: str, slippage: bool = True) -> None:
        side = "SELL" if self.position == 1 else "BUY"
        fill = self.costs.slippage_price(raw_price, side) if slippage else raw_price
        charges = self.costs.order_charges(side, fill, self.qty)
        gross = self.position * (fill - self.entry_fill) * self.qty
        self.realized += gross - charges
        self.day_realized += gross - charges
        self.trades.append(
            {
                "entry_time": self.entry_time,
                "exit_time": ts,
                "side": "LONG" if self.position == 1 else "SHORT",
                "qty": self.qty,
                "entry_price": round(self.entry_fill, 4),
                "exit_price": round(fill, 4),
                "gross_pnl": gross,
                "costs": self.entry_charges + charges,
                "net_pnl": gross - self.entry_charges - charges,
                "exit_reason": reason,
            }
        )
        self.position = 0
        self.stop = None
        self.target = None

    def _try_enter(self, ts, raw_price: float, direction: int) -> None:
        notional = raw_price * self.qty
        ok, why = self.risk.can_enter(ts.time(), notional)
        if ok:
            self._enter(ts, raw_price, direction)
        else:
            self.rejections[why] += 1

    def _execute(self, action: str, reason: str, ts, open_price: float) -> None:
        """Carry out last bar's decision at this bar's open."""
        if action == EXIT:
            if self.position != 0:
                self._exit(ts, open_price, reason)
        elif action == BUY:
            if self.position == -1:
                self._exit(ts, open_price, "signal")
            elif self.position == 0:
                self._try_enter(ts, open_price, 1)
        elif action == SELL:
            if self.position == 1:
                self._exit(ts, open_price, "signal")
            elif self.position == 0 and self.allow_short:
                self._try_enter(ts, open_price, -1)

    def _check_stop_target(self, ts, o: float, h: float, l: float) -> None:
        if self.position == 1:
            if self.stop is not None:
                if o <= self.stop:
                    return self._exit(ts, o, "stop")
                if l <= self.stop:
                    return self._exit(ts, self.stop, "stop")
            if self.target is not None:
                if o >= self.target:
                    return self._exit(ts, o, "target", slippage=False)
                if h >= self.target:
                    return self._exit(ts, self.target, "target", slippage=False)
        elif self.position == -1:
            if self.stop is not None:
                if o >= self.stop:
                    return self._exit(ts, o, "stop")
                if h >= self.stop:
                    return self._exit(ts, self.stop, "stop")
            if self.target is not None:
                if o <= self.target:
                    return self._exit(ts, o, "target", slippage=False)
                if l <= self.target:
                    return self._exit(ts, self.target, "target", slippage=False)

    # -------------------------------------------------------------------- run
    def run(self, df: pd.DataFrame) -> BacktestResult:
        self._reset_state()
        self.risk = RiskManager(self.cfg["risk"])
        square_off = self.cfg["risk"]["square_off_time"]

        df = self.strategy.prepare(df.copy())
        idx = df.index
        O, H, L, C = (df[c].to_numpy() for c in ("open", "high", "low", "close"))

        pending = None
        pending_reason = "signal"
        current_date = None
        prev_ts, prev_close = None, None
        equity_values = []

        for i in range(len(df)):
            ts = idx[i]
            t = ts.time()

            if ts.date() != current_date:
                if self.position != 0:
                    # The previous day's data ended before square-off time.
                    self._exit(prev_ts, prev_close, "day_ended_before_square_off")
                current_date = ts.date()
                self.risk.new_day()
                self.day_realized = 0.0
                pending = None  # decisions never carry overnight

            # 1) Fill the decision made at the previous bar's close.
            if pending is not None:
                self._execute(pending, pending_reason, ts, O[i])
                pending = None

            # 2) Forced square-off.
            if self.position != 0 and t >= square_off:
                self._exit(ts, O[i], "square_off")

            # 3) Stop-loss / target inside this bar.
            if self.position != 0:
                self._check_stop_target(ts, O[i], H[i], L[i])

            # 4) Mark to market at the close.
            unrealized = self.position * (C[i] - self.entry_fill) * self.qty if self.position else 0.0
            equity_values.append(self.capital + self.realized + unrealized)

            # 5) Daily-loss kill switch.
            if self.risk.check_daily_loss(self.day_realized + unrealized):
                self.events.append(f"{ts.date()} {t.strftime('%H:%M')}: {self.risk.halt_reason}; trading stopped for the day")
                if self.position != 0:
                    pending, pending_reason = EXIT, "kill_switch"

            # 6) Ask the strategy what to do next (not while halted).
            if not self.risk.halted:
                pending = self.strategy.on_bar(i, df, self.position)
                pending_reason = "signal"

            prev_ts, prev_close = ts, C[i]

        if self.position != 0:
            self._exit(prev_ts, prev_close, "end_of_data")
            equity_values[-1] = self.capital + self.realized

        trades = pd.DataFrame(self.trades, columns=TRADE_COLUMNS)
        equity = pd.Series(equity_values, index=idx, name="equity")
        metrics = compute_metrics(trades, equity, self.capital)
        return BacktestResult(
            name=self.cfg["name"],
            trades=trades,
            equity=equity,
            metrics=metrics,
            events=self.events,
            rejections=dict(self.rejections),
        )


def run_backtest(df: pd.DataFrame, cfg: dict, strategy: Strategy) -> BacktestResult:
    return Backtester(cfg, strategy).run(df)
