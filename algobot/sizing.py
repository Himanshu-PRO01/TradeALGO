"""Position sizing for BOUGHT options, from a maximum loss per trade.

The question this answers: "If I risk at most Rs X on this trade, and my
stop-loss is at premium S while I buy at premium E, how many lots may I take?"

Rules the calculator enforces:
  * the loss if the stop is hit must not exceed the maximum loss,
  * the total premium paid must not exceed the capital,
  * whichever is smaller decides the number of lots.

If the answer is zero lots, it says why and what would have to change. That is
useful information: it is better to learn that a trade does not fit the
account BEFORE clicking buy.

Lot size changes over time. NSE's contract file is the official source; the
Nifty 50 default below (65, from the January 2026 series) is only a default.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

NIFTY_LOT_SIZE = 65


@dataclass
class SizeResult:
    lots: int
    quantity: int
    premium_outlay: float
    loss_if_stopped: float
    risk_pct_of_capital: float | None
    loss_per_lot: float
    cost_per_lot: float
    warnings: list = field(default_factory=list)


def option_position_size(
    max_loss: float,
    entry_premium: float,
    stop_premium: float,
    lot_size: int = NIFTY_LOT_SIZE,
    capital: float | None = None,
    est_charges: float = 0.0,
) -> SizeResult:
    """Lots allowed for a bought option.

    est_charges: your broker's estimate of round-trip charges for the trade,
    in rupees. It is subtracted from the loss budget so charges are not a surprise.
    """
    if max_loss <= 0:
        raise ValueError("max_loss must be above 0")
    if entry_premium <= 0 or stop_premium < 0:
        raise ValueError("entry_premium must be above 0 and stop_premium cannot be negative")
    if stop_premium >= entry_premium:
        raise ValueError("For a bought option the stop premium must be BELOW the entry premium")
    if lot_size < 1 or int(lot_size) != lot_size:
        raise ValueError("lot_size must be a whole number, 1 or more")
    if capital is not None and capital <= 0:
        raise ValueError("capital must be above 0")

    loss_per_lot = (entry_premium - stop_premium) * lot_size
    cost_per_lot = entry_premium * lot_size
    budget = max_loss - est_charges
    warnings: list[str] = []

    lots_by_risk = math.floor(budget / loss_per_lot) if budget > 0 else 0
    lots_by_capital = math.floor(capital / cost_per_lot) if capital is not None else lots_by_risk
    lots = max(min(lots_by_risk, lots_by_capital), 0)

    if lots == 0:
        if lots_by_risk == 0:
            longest_stop = budget / lot_size if budget > 0 else 0
            warnings.append(
                f"One lot would lose Rs {loss_per_lot:,.0f} at your stop, more than your "
                f"Rs {max_loss:,.0f} limit (after charges). The stop would have to be within "
                f"{longest_stop:,.2f} premium points of the entry, or the trade should be skipped."
            )
        if capital is not None and lots_by_capital == 0:
            warnings.append(
                f"One lot costs Rs {cost_per_lot:,.0f}, which is more than your capital of Rs {capital:,.0f}."
            )
    elif capital is not None and lots_by_capital < lots_by_risk:
        warnings.append("Capital, not the loss limit, is what limits the size of this trade.")

    risk_pct = None
    if capital is not None:
        risk_pct = max_loss / capital * 100.0
        if risk_pct > 5:
            warnings.append(
                f"Your loss limit is {risk_pct:.0f}% of capital per trade. Losing streaks are normal; "
                f"three losses in a row would cost about {min(3 * risk_pct, 100):.0f}% of the account."
            )
        if lots and cost_per_lot * lots > 0.8 * capital:
            warnings.append(
                f"This trade ties up {cost_per_lot * lots / capital * 100:.0f}% of your capital."
            )

    return SizeResult(
        lots=lots,
        quantity=lots * int(lot_size),
        premium_outlay=lots * cost_per_lot,
        loss_if_stopped=lots * loss_per_lot,
        risk_pct_of_capital=risk_pct,
        loss_per_lot=loss_per_lot,
        cost_per_lot=cost_per_lot,
        warnings=warnings,
    )


def format_size(result: SizeResult, lot_size: int) -> str:
    lines = [
        f"Lots allowed:        {result.lots}  ({result.quantity} units, lot size {lot_size})",
        f"Cost per lot:        Rs {result.cost_per_lot:,.2f}",
        f"Loss per lot at stop: Rs {result.loss_per_lot:,.2f}",
    ]
    if result.lots:
        lines += [
            f"Premium you pay:     Rs {result.premium_outlay:,.2f}",
            f"Loss if stop is hit: Rs {result.loss_if_stopped:,.2f}",
        ]
    for w in result.warnings:
        lines.append("Note: " + w)
    return "\n".join(lines)
