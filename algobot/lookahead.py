"""Look-ahead checks.

Look-ahead bias means a backtest secretly used information from the future.
It is the most common reason a strategy looks brilliant in testing and fails
live. Unit tests can only check strategies someone thought of in advance, so
this module checks ANY strategy, including a rule the trader wrote this
morning:

1. Truncation: signals for the first k bars must be identical whether or not
   the later bars exist.
2. Future scramble: replace every bar after a cut point with random noise; the
   signals before the cut must not move.
3. Indicator columns: every column computed for the first k bars must be
   identical with and without the future.

`selftest()` feeds the checks a strategy that DELIBERATELY peeks one bar
ahead and requires them to fail. A checker nobody has tried to fool is not
evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd

from .strategy import BUY, SELL, Strategy, build_strategy

POSITIONS = (0, 1, -1)


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def _signals(factory: Callable[[], Strategy], df: pd.DataFrame) -> dict:
    strategy = factory()
    prepared = strategy.prepare(df.copy())
    n = len(prepared)
    return {pos: [strategy.on_bar(i, prepared, pos) for i in range(n)] for pos in POSITIONS}


def _first_difference(a: dict, b: dict, k: int) -> Optional[tuple]:
    for pos in POSITIONS:
        for i in range(k):
            if a[pos][i] != b[pos][i]:
                return pos, i
    return None


def check_truncation(factory, df: pd.DataFrame, cuts=(0.3, 0.55, 0.8)) -> Check:
    full = _signals(factory, df)
    for frac in cuts:
        k = max(int(len(df) * frac), 2)
        part = _signals(factory, df.iloc[:k])
        diff = _first_difference(part, full, k)
        if diff:
            pos, i = diff
            return Check(
                "signals do not change when later bars are removed", False,
                f"At bar {i} (position state {pos}) the signal differs when the data stops at bar {k}. "
                "The strategy is using information from after that bar.",
            )
    return Check("signals do not change when later bars are removed", True,
                 f"Identical at {len(cuts)} different cut points.")


def _alter_future(df: pd.DataFrame, k: int, mode: str, seed: int = 7) -> pd.DataFrame:
    """Keep bars [0, k) and replace everything after with a very different future.

    mode "up":    prices jump 50% higher and stay there
    mode "down":  prices fall 50% and stay there
    mode "noise": a random walk

    The two extreme modes matter: a strategy that peeks even one bar ahead will
    BUY under "up" and SELL under "down", so it cannot hide. Random noise alone
    can match the real future by luck and miss a one-bar peek about half the time.
    """
    out = df.copy()
    m = len(df) - k
    start = float(df["close"].iloc[k - 1])
    if mode == "noise":
        rng = np.random.default_rng(seed)
        closes = start * np.exp(np.cumsum(rng.normal(0.0, 0.01, m)))
        opens = np.concatenate([[start], closes[:-1]])
        highs = np.maximum(opens, closes) * (1 + np.abs(rng.normal(0, 0.005, m)))
        lows = np.minimum(opens, closes) * (1 - np.abs(rng.normal(0, 0.005, m)))
        volume = rng.integers(1000, 20000, m).astype(float)
    else:
        level = start * (1.5 if mode == "up" else 0.5)
        closes = np.full(m, level)
        opens = np.full(m, level)
        highs = np.full(m, level * 1.001)
        lows = np.full(m, level * 0.999)
        volume = np.full(m, 5000.0)
    for col, values in (("open", opens), ("high", highs), ("low", lows), ("close", closes), ("volume", volume)):
        out.iloc[k:, out.columns.get_loc(col)] = values
    return out


def check_future_scramble(factory, df: pd.DataFrame, cuts=(0.35, 0.6, 0.85)) -> Check:
    name = "signals do not change when the future is replaced"
    for frac in cuts:
        k = max(int(len(df) * frac), 3)
        baseline = _signals(factory, df)
        for mode in ("up", "down", "noise"):
            altered = _signals(factory, _alter_future(df, k, mode))
            diff = _first_difference(altered, baseline, k)
            if diff:
                pos, i = diff
                return Check(
                    name, False,
                    f"At bar {i} (position state {pos}) the signal changed when the bars after {k} were "
                    f"replaced by a '{mode}' future. The strategy is using information from the future.",
                )
    return Check(name, True,
                 f"Bars before each of {len(cuts)} cut points gave identical signals under an 'up', a 'down' and a random future.")


def check_indicator_columns(factory, df: pd.DataFrame, cut_frac: float = 0.6) -> Check:
    k = max(int(len(df) * cut_frac), 2)
    full = factory().prepare(df.copy())
    part = factory().prepare(df.iloc[:k].copy())
    name = "indicator values do not depend on later bars"
    try:
        pd.testing.assert_frame_equal(part, full.iloc[:k], check_exact=False, rtol=1e-9, atol=1e-12)
    except AssertionError as exc:
        first_line = str(exc).strip().splitlines()[0]
        return Check(name, False, f"Some indicator values for the first {k} bars change when later bars exist ({first_line}).")
    return Check(name, True, "All indicator columns are identical with and without the future.")


def run_lookahead_checks(cfg: dict, df: pd.DataFrame, max_bars: int = 4000) -> list[Check]:
    df = df.iloc[:max_bars]
    factory = lambda: build_strategy(cfg)  # noqa: E731
    return [
        check_truncation(factory, df),
        check_future_scramble(factory, df),
        check_indicator_columns(factory, df),
    ]


class LeakyStrategy(Strategy):
    """DELIBERATELY BROKEN: buys when the NEXT bar closes higher. For self-test only."""

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["next_close"] = df["close"].shift(-1)
        return df

    def on_bar(self, i: int, df: pd.DataFrame, position: int) -> Optional[str]:
        nxt = df["next_close"].iat[i]
        if pd.isna(nxt):
            return None
        return BUY if nxt > df["close"].iat[i] else SELL


def selftest(df: pd.DataFrame) -> list[Check]:
    """Run the checks on a strategy that cheats. Every check must FAIL."""
    df = df.iloc[:1500]
    factory = lambda: LeakyStrategy({})  # noqa: E731
    return [
        check_truncation(factory, df),
        check_future_scramble(factory, df),
        check_indicator_columns(factory, df),
    ]
