"""Shared helpers for building tiny, fully controlled test scenarios."""
import pandas as pd

from algobot.config import validate_config
from algobot.engine import run_backtest
from algobot.strategy import Strategy

ZERO_COSTS = dict(
    brokerage_pct=0, brokerage_cap=None, stt_sell_pct=0, exchange_txn_pct=0,
    sebi_fee_pct=0, stamp_buy_pct=0, gst_pct=0, slippage_bps=0,
)


def make_bars(rows, day="2025-01-06", start="09:15", minutes=5):
    """rows: list of (open, high, low, close) tuples."""
    idx = pd.date_range(f"{day} {start}", periods=len(rows), freq=f"{minutes}min")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = 1000.0
    df.index.name = "datetime"
    return df


def flat_rows(n, price=100.0):
    return [(price, price + 0.1, price - 0.1, price)] * n


def make_cfg(strategy=None, risk=None, costs=None):
    raw = {
        "capital": 100000,
        "strategy": {"quantity": 10, **(strategy or {})},
        "risk": risk or {},
        "costs": {**ZERO_COSTS, **(costs or {})},
    }
    return validate_config(raw)


class Scripted(Strategy):
    """Emits pre-arranged signals by bar number, so tests control everything."""

    def __init__(self, script):
        super().__init__({})
        self.script = script

    def on_bar(self, i, df, position):
        return self.script.get(i)


def run(df, script, **cfg_parts):
    cfg = make_cfg(**cfg_parts)
    return run_backtest(df, cfg, Scripted(script))
