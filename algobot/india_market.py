"""India-first market calendar and cost assumptions for research simulations."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class IndiaMarketProfile:
    name: str = "NSE Equity"
    timezone: str = "Asia/Kolkata"
    regular_open: time = time(9, 15)
    regular_close: time = time(15, 30)
    currency: str = "INR"
    lot_size: int = 1


@dataclass(frozen=True)
class IndiaCostModel:
    """Research approximation; broker/exchange charges must be refreshed before trading."""
    brokerage_per_order: float = 20.0
    exchange_txn_bps: float = 0.30
    stamp_buy_bps: float = 0.30
    stt_sell_bps: float = 3.0
    gst_rate: float = 0.18
    slippage_bps: float = 2.0

    def estimate_round_trip(self, buy_value: float, sell_value: float) -> float:
        brokerage = 2 * self.brokerage_per_order
        txn = (buy_value + sell_value) * self.exchange_txn_bps / 10_000
        stamp = buy_value * self.stamp_buy_bps / 10_000
        stt = sell_value * self.stt_sell_bps / 10_000
        gst_base = brokerage + txn
        gst = gst_base * self.gst_rate
        slippage = (buy_value + sell_value) * self.slippage_bps / 10_000
        return brokerage + txn + stamp + stt + gst + slippage


def is_regular_session(ts: datetime) -> bool:
    local = ts.astimezone(IST)
    if local.weekday() >= 5:
        return False
    profile = IndiaMarketProfile()
    return profile.regular_open <= local.time() < profile.regular_close
