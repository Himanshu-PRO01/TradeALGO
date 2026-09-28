"""End-to-end smoke test for the deliberately fake demo strategy.

This test does not claim the strategy has trading value. It only proves:
config -> strategy -> engine -> trades/metrics.
"""
import numpy as np
import pandas as pd

from algobot.config import validate_config
from algobot.engine import run_backtest
from algobot.strategy import build_strategy


def _fake_bars():
    # Repeated ramps and drops force several 3/8 SMA crossovers.
    closes = []
    for base in (100, 110, 98, 112, 96, 115):
        closes.extend(np.linspace(base, base + 10, 12))
        closes.extend(np.linspace(base + 10, base - 2, 12))

    idx = pd.date_range("2026-01-05 09:15", periods=len(closes), freq="5min")
    close = np.asarray(closes, dtype=float)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1000,
        },
        index=idx,
    )


def test_fake_strategy_runs_from_config_through_engine():
    raw = {
        "name": "fake_smoke_test",
        "capital": 100000,
        "strategy": {
            "name": "sma_crossover",
            "params": {"fast": 3, "slow": 8},
            "quantity": 1,
            "allow_short": False,
            "stop_loss_pct": None,
            "target_pct": None,
        },
        "risk": {
            "max_daily_loss": 100000,
            "max_trades_per_day": 100,
            "max_position_value": 100000,
            "trading_start": "09:15",
            "no_new_entries_after": "15:00",
            "square_off_time": "15:15",
        },
        "costs": {
            "brokerage_pct": 0,
            "brokerage_cap": 0,
            "stt_sell_pct": 0,
            "exchange_txn_pct": 0,
            "sebi_fee_pct": 0,
            "stamp_buy_pct": 0,
            "gst_pct": 0,
            "slippage_bps": 0,
        },
    }
    cfg = validate_config(raw)
    strategy = build_strategy(cfg)
    result = run_backtest(_fake_bars(), cfg, strategy)

    assert result.trades is not None
    assert len(result.trades) >= 2
    assert result.metrics["trades"] == len(result.trades)
    assert result.metrics["net_pnl"] == result.trades["net_pnl"].sum()
