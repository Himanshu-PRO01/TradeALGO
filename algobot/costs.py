"""Trading costs and slippage.

Costs are the most common reason a strategy that looks good in a backtest
loses money live, so every simulated order pays them. All rates are settings
in the config file (the defaults are only EXAMPLES: check your broker's
charge calculator and edit them).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CostModel:
    brokerage_pct: float = 0.03           # percent of order value
    brokerage_cap: Optional[float] = 20.0  # max brokerage per order (None = no cap)
    brokerage_flat: Optional[float] = None  # if set, flat brokerage per order instead
    stt_buy_pct: float = 0.0
    stt_sell_pct: float = 0.025
    exchange_txn_pct: float = 0.003
    sebi_fee_pct: float = 0.0001
    stamp_buy_pct: float = 0.003
    gst_pct: float = 18.0                 # on brokerage + exchange + SEBI fees
    slippage_bps: float = 2.0             # 1 bps = 0.01 percent

    def slippage_price(self, price: float, side: str) -> float:
        """Price after adverse slippage: buyers pay more, sellers receive less."""
        move = price * self.slippage_bps / 10000.0
        return price + move if side == "BUY" else price - move

    def order_charges(self, side: str, price: float, qty: int) -> float:
        """Total charges in rupees for one order (one side of a trade)."""
        if side not in ("BUY", "SELL"):
            raise ValueError(f"side must be BUY or SELL, got {side!r}")
        value = price * qty
        if self.brokerage_flat is not None:
            brokerage = self.brokerage_flat
        else:
            brokerage = value * self.brokerage_pct / 100.0
            if self.brokerage_cap is not None:
                brokerage = min(brokerage, self.brokerage_cap)
        stt_pct = self.stt_buy_pct if side == "BUY" else self.stt_sell_pct
        stt = value * stt_pct / 100.0
        exchange = value * self.exchange_txn_pct / 100.0
        sebi = value * self.sebi_fee_pct / 100.0
        stamp = value * self.stamp_buy_pct / 100.0 if side == "BUY" else 0.0
        gst = (brokerage + exchange + sebi) * self.gst_pct / 100.0
        return brokerage + stt + exchange + sebi + stamp + gst
