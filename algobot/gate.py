"""Pre-trade gate and alert message.

OpenAlgo (or TradingView) can tell the brother that price reached a level.
What no alert tells him is: "given today's trades and losses, and your own
limits, may you take this one, and how many lots fit?" That is the point where
most small accounts are lost, so this layer answers it and puts the answer in
the same message.

The gate cannot stop him from placing an order by hand. It makes the rule
visible at the moment it matters, and the journal review shows afterwards
whether the rule was followed.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Optional

from .journal import Journal
from .sizing import SizeResult, option_position_size


@dataclass
class GateResult:
    allowed: bool
    reasons: list = field(default_factory=list)
    trades_opened_today: int = 0
    net_pnl_today: float = 0.0
    open_positions: int = 0


def check_gate(journal: Journal, day: dt.date, max_trades_per_day: Optional[int] = None,
               max_daily_loss: Optional[float] = None) -> GateResult:
    opened_today = [t for t in journal.all_trades() if t.opened_date == day]
    pnl = sum(t.net_pnl for t in journal.closed_between(day, day))
    reasons = []
    if max_daily_loss is not None and pnl <= -max_daily_loss:
        reasons.append(f"The daily loss limit of Rs {max_daily_loss:,.0f} has been reached "
                       f"(today Rs {pnl:,.0f}). No more trades today.")
    if max_trades_per_day is not None and len(opened_today) >= max_trades_per_day:
        reasons.append(f"{len(opened_today)} trade(s) already opened today; the plan is at most {max_trades_per_day}.")
    return GateResult(allowed=not reasons, reasons=reasons, trades_opened_today=len(opened_today),
                      net_pnl_today=pnl, open_positions=len(journal.open_trades()))


def build_alert(
    instrument: str, entry_premium: float, stop_premium: float, lot_size: int, capital: float, max_loss: float,
    gate: GateResult, est_charges: float = 0.0, max_trades_per_day: Optional[int] = None,
    max_daily_loss: Optional[float] = None,
) -> tuple[str, bool, SizeResult]:
    """Returns (message, may_take_trade, sizing)."""
    size = option_position_size(max_loss=max_loss, entry_premium=entry_premium, stop_premium=stop_premium,
                                lot_size=lot_size, capital=capital, est_charges=est_charges)
    takeable = gate.allowed and size.lots > 0
    lines = [
        f"{instrument}: level alert",
        f"Plan: buy at {entry_premium:g}, stop at {stop_premium:g} "
        f"(risk {entry_premium - stop_premium:g} per unit).",
    ]
    if size.lots > 0:
        pct = size.loss_if_stopped / capital * 100.0
        lines += [
            f"Size: {size.lots} lot(s) = {size.quantity} units. Pay about Rs {size.premium_outlay:,.0f}.",
            f"Loss if the stop is hit: about Rs {size.loss_if_stopped:,.0f} ({pct:.1f}% of capital).",
        ]
    else:
        lines.append("Size: this trade does not fit your rules at this stop.")
    for w in size.warnings:
        lines.append("Note: " + w)
    limits = []
    if max_trades_per_day is not None:
        limits.append(f"max {max_trades_per_day} trades")
    if max_daily_loss is not None:
        limits.append(f"max loss Rs {max_daily_loss:,.0f}")
    lines.append(f"Today: {gate.trades_opened_today} trade(s) opened, net Rs {gate.net_pnl_today:,.0f}, "
                 f"{gate.open_positions} open position(s)." + (f" Limits: {', '.join(limits)}." if limits else ""))
    if takeable:
        lines.append("Check: OK by your own rules. You decide and place the order yourself.")
    else:
        why = gate.reasons or ["the size comes out at zero lots"]
        lines.append("Check: BLOCKED. " + " ".join(why))
    lines.append("Not advice. Estimates only.")
    return "\n".join(lines), takeable, size
