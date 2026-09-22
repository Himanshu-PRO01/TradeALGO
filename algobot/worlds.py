"""Fake markets ("worlds") with different personalities.

Real markets change character: some weeks trend, some chop sideways, some crash,
some jump on news. A strategy that only ever met one kind of market has only
been half tested. These worlds let you meet as many as you like, instantly and
for free, and see which ones a strategy or a trader survives.

WHAT THIS IS FOR: finding bugs, testing risk rules and learning how a strategy
behaves in different conditions.
WHAT THIS CANNOT DO: create a real edge. Prices here are made up. In the
"noise" world no strategy can win on average, and tuning a strategy until it
wins on made-up prices only teaches it to fit noise.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Regime:
    name: str
    description: str
    autocorr: float = 0.0          # >0 moves tend to continue, <0 tend to reverse
    vol_per_bar: float = 0.0008
    drift_per_bar: float = 0.0
    gap_sigma: float = 0.003       # size of overnight gaps
    gap_mean: float = 0.0          # average overnight gap (negative = tends to open lower)
    shock_prob: float = 0.0        # chance per day of a sudden news jump
    shock_sigma: float = 0.0       # size of that jump


REGIMES = {r.name: r for r in [
    Regime("noise", "Pure random moves. No edge exists here: the honest baseline."),
    Regime("trend", "Moves tend to continue. Trend-following works; reversal strategies suffer.",
           autocorr=0.45, vol_per_bar=0.0012),
    Regime("mean_reversion", "Moves tend to reverse. Buying dips works; chasing breakouts suffers.",
           autocorr=-0.45, vol_per_bar=0.0012),
    Regime("chop", "Quiet, range-bound and slightly reversing. Little to earn; costs dominate.",
           autocorr=-0.15, vol_per_bar=0.0004, gap_sigma=0.002),
    Regime("volatile", "Big swings both ways and wide gaps. Stops get hit; oversized bets hurt.",
           vol_per_bar=0.002, gap_sigma=0.006),
    Regime("crash", "A falling market with down gaps and panic days.",
           autocorr=0.1, vol_per_bar=0.0015, drift_per_bar=-0.00012, gap_sigma=0.004, gap_mean=-0.006,
           shock_prob=0.15, shock_sigma=0.02),
    Regime("shocks", "Mostly quiet, with sudden news jumps that gap straight through stops.",
           shock_prob=0.25, shock_sigma=0.015),
]}


def get_regime(regime) -> Regime:
    if isinstance(regime, Regime):
        return regime
    if regime not in REGIMES:
        raise ValueError(f"Unknown regime '{regime}'. Choose from: {', '.join(REGIMES)}")
    return REGIMES[regime]


def _generate(regime: Regime, days: int, rng: np.random.Generator, start_price: float, start_date,
              bars_per_day: int, minutes_per_bar: int, last_return: float = 0.0) -> tuple:
    dates = pd.bdate_range(start_date, periods=days)
    rows = []
    prev_close = float(start_price)
    for d in dates:
        gap = rng.normal(regime.gap_mean, regime.gap_sigma)
        eps = rng.normal(regime.drift_per_bar, regime.vol_per_bar, bars_per_day)
        if regime.autocorr:
            for k in range(bars_per_day):
                previous = eps[k - 1] if k else last_return
                eps[k] = eps[k] + regime.autocorr * previous
        last_return = float(eps[-1])
        if regime.shock_prob and rng.random() < regime.shock_prob:
            eps[int(rng.integers(5, bars_per_day - 5))] += rng.normal(0.0, regime.shock_sigma)
        first_open = max(prev_close * (1.0 + gap), 1.0)
        closes = first_open * np.exp(np.cumsum(eps))
        opens = np.concatenate([[first_open], closes[:-1]])
        wick = max(regime.vol_per_bar, 1e-4) / 2.0
        highs = np.maximum(opens, closes) * (1.0 + np.abs(rng.normal(0.0, wick, bars_per_day)))
        lows = np.minimum(opens, closes) * (1.0 - np.abs(rng.normal(0.0, wick, bars_per_day)))
        volumes = rng.integers(1000, 20000, bars_per_day).astype(float)
        day_start = pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=15)
        for k in range(bars_per_day):
            o, c = round(float(opens[k]), 2), round(float(closes[k]), 2)
            h = round(float(max(highs[k], o, c)), 2)
            l = round(float(min(lows[k], o, c)), 2)
            rows.append((day_start + pd.Timedelta(minutes=minutes_per_bar * k), o, h, l, c, float(volumes[k])))
        prev_close = float(closes[-1])
    df = pd.DataFrame(rows, columns=["datetime", "open", "high", "low", "close", "volume"]).set_index("datetime")
    return df, prev_close, last_return


def generate_world(regime, days: int = 15, seed: int = 1, start_price: float = 1000.0, bars_per_day: int = 75,
                   minutes_per_bar: int = 5, start_date: str = "2025-01-01") -> pd.DataFrame:
    """One fake market of the chosen personality. Same seed, same world."""
    if days < 1:
        raise ValueError("days must be 1 or more")
    df, _, _ = _generate(get_regime(regime), days, np.random.default_rng(seed), start_price, start_date,
                         bars_per_day, minutes_per_bar)
    return df


def generate_mixed_world(days: int = 30, seed: int = 1, start_price: float = 1000.0, regimes: Optional[list] = None,
                         segment_days: tuple = (3, 8), bars_per_day: int = 75, minutes_per_bar: int = 5,
                         start_date: str = "2025-01-01") -> tuple:
    """A market that changes character every few days, like the real one. Returns (prices, segments).

    segments is a list of (regime name, first bar time, last bar time).
    """
    if days < 1:
        raise ValueError("days must be 1 or more")
    rng = np.random.default_rng(seed)
    names = list(regimes or REGIMES)
    frames, segments = [], []
    price, last_return, cursor, remaining = float(start_price), 0.0, pd.Timestamp(start_date), days
    while remaining > 0:
        length = min(int(rng.integers(segment_days[0], segment_days[1] + 1)), remaining)
        regime = get_regime(names[int(rng.integers(0, len(names)))])
        df, price, last_return = _generate(regime, length, rng, price, cursor, bars_per_day, minutes_per_bar, last_return)
        frames.append(df)
        segments.append((regime.name, df.index[0], df.index[-1]))
        cursor = pd.Timestamp(df.index[-1].normalize()) + pd.offsets.BDay(1)
        remaining -= length
    return pd.concat(frames), segments
