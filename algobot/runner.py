"""One-call helpers used by the dashboard (and handy for scripts)."""
from __future__ import annotations

import pandas as pd

from .config import validate_config
from .engine import BacktestResult, run_backtest
from .strategy import build_strategy


def run_from_dict(raw: dict, df: pd.DataFrame) -> BacktestResult:
    """Validate a settings dictionary, build its strategy and run a backtest."""
    cfg = validate_config(raw)
    return run_backtest(df, cfg, build_strategy(cfg))


def check_strategy(cfg: dict) -> None:
    """Dry-run the strategy on a few days of sample data.

    Building a strategy does not evaluate its rules; that only happens once
    prices arrive. This catches unknown column names, forbidden syntax and bad
    indicator settings straight away, before the trader waits for a full run.
    """
    from .data import generate_sample_data

    strategy = build_strategy(cfg)
    strategy.prepare(generate_sample_data(days=3, seed=1))
