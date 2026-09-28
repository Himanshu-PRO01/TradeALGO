import numpy as np
import pandas as pd

from algobot.strategy import NewEraStrategy, REGISTRY, build_strategy


def make_bars(n=80):
    idx = pd.date_range("2026-01-05 09:15", periods=n, freq="15min")
    base = np.linspace(100, 110, n)
    return pd.DataFrame(
        {
            "open": base,
            "high": base + 1,
            "low": base - 1,
            "close": base + 0.2,
            "volume": np.full(n, 1000),
        },
        index=idx,
    )


def test_new_era_is_registered():
    assert REGISTRY["new_era_1_0"] is NewEraStrategy


def test_new_era_prepare_adds_source_indicators():
    strategy = NewEraStrategy({"sl_max_points_percent": 0, "target_ratio": 2})
    prepared = strategy.prepare(make_bars())

    for column in (
        "rsi_5",
        "rsi_smooth_5",
        "cci_14",
        "cci_smooth_5",
        "ema_9",
        "ema_33",
        "ema_smooth_9",
        "hma_18",
        "hma_22",
        "hma_27",
        "formation_pe",
        "formation_ce",
    ):
        assert column in prepared.columns


def test_new_era_builds_from_config():
    cfg = {
        "strategy": {
            "name": "new_era_1_0",
            "params": {"sl_max_points_percent": 0, "target_ratio": 2},
        }
    }
    strategy = build_strategy(cfg)
    assert isinstance(strategy, NewEraStrategy)


def test_new_era_has_no_pending_levels_before_signal():
    strategy = NewEraStrategy({"sl_max_points_percent": 0, "target_ratio": 2})
    strategy.prepare(make_bars())
    assert strategy.take_pending_levels() is None
