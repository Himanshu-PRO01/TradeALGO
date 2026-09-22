"""Risk rules that sit between the strategy and the market.

The strategy can ask for anything; the risk manager decides what is allowed.
The same class will be used unchanged for paper and live trading later, so
the rules that protect money are tested once and reused.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional


class RiskManager:
    def __init__(self, risk_cfg: dict):
        self.cfg = risk_cfg
        self.halted = False
        self.halt_reason: Optional[str] = None
        self.trades_today = 0

    def new_day(self) -> None:
        """Reset the daily counters and lift any daily halt."""
        self.halted = False
        self.halt_reason = None
        self.trades_today = 0

    def can_enter(self, t: dt.time, notional: float) -> tuple[bool, str]:
        """May a NEW position be opened now? Returns (allowed, reason if not)."""
        c = self.cfg
        if self.halted:
            return False, "halted_for_the_day"
        if t < c["trading_start"]:
            return False, "before_trading_start"
        if t > c["no_new_entries_after"]:
            return False, "after_last_entry_time"
        if c["max_trades_per_day"] is not None and self.trades_today >= c["max_trades_per_day"]:
            return False, "max_trades_per_day"
        if c["max_position_value"] is not None and notional > c["max_position_value"]:
            return False, "position_too_large"
        return True, ""

    def register_entry(self) -> None:
        self.trades_today += 1

    def check_daily_loss(self, day_pnl: float) -> bool:
        """Kill switch. day_pnl includes open profit/loss. True if it just tripped."""
        limit = self.cfg["max_daily_loss"]
        if limit is not None and not self.halted and day_pnl <= -limit:
            self.halted = True
            self.halt_reason = f"daily loss limit of {limit:,.0f} reached"
            return True
        return False
