"""Support and resistance levels that can be used in rules.

All of these are safe from look-ahead bias:

* prev_day_*  / prev_week_*: the finished previous day (or week), so a level
  is only used after it has fully formed.
* swing_high / swing_low: a swing high is a bar whose high is the highest of
  `period` bars on each side. It can only be known `period` bars AFTER it
  happened, so the level appears with exactly that delay and is then carried
  forward until the next swing is confirmed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LEVEL_TYPES = (
    "prev_day_high", "prev_day_low", "prev_day_close",
    "prev_week_high", "prev_week_low",
    "swing_high", "swing_low",
)
SWING_TYPES = ("swing_high", "swing_low")


def _previous_period(df: pd.DataFrame, keys, agg_col: str, how: str) -> pd.Series:
    """Aggregate each period, shift by one period, and spread it over that period's bars."""
    grouped = df[agg_col].groupby(keys)
    agg = {"max": grouped.max, "min": grouped.min, "last": grouped.last}[how]()
    previous = agg.shift(1)
    return pd.Series(previous.reindex(keys).to_numpy(), index=df.index)


def prev_day(df: pd.DataFrame, which: str) -> pd.Series:
    """Previous trading day's high, low or close."""
    keys = df.index.normalize()
    col, how = {"high": ("high", "max"), "low": ("low", "min"), "close": ("close", "last")}[which]
    return _previous_period(df, keys, col, how)


def prev_week(df: pd.DataFrame, which: str) -> pd.Series:
    """Previous calendar week's (Mon to Sun) high or low."""
    keys = df.index.to_period("W")
    col, how = {"high": ("high", "max"), "low": ("low", "min")}[which]
    return _previous_period(df, keys, col, how)


def swing_high(df: pd.DataFrame, n: int) -> pd.Series:
    """Most recent CONFIRMED swing high (n bars on each side), known n bars later."""
    high = df["high"]
    window_max = high.rolling(2 * n + 1, center=True).max()
    is_swing = (high == window_max) & window_max.notna()
    confirmed = is_swing.shift(n, fill_value=False).astype(bool)
    level = high.shift(n).where(confirmed)
    return level.ffill()


def swing_low(df: pd.DataFrame, n: int) -> pd.Series:
    """Most recent CONFIRMED swing low (n bars on each side), known n bars later."""
    low = df["low"]
    window_min = low.rolling(2 * n + 1, center=True).min()
    is_swing = (low == window_min) & window_min.notna()
    confirmed = is_swing.shift(n, fill_value=False).astype(bool)
    level = low.shift(n).where(confirmed)
    return level.ffill()


def compute_level(df: pd.DataFrame, kind: str, period: int | None) -> pd.Series:
    if kind == "prev_day_high":
        return prev_day(df, "high")
    if kind == "prev_day_low":
        return prev_day(df, "low")
    if kind == "prev_day_close":
        return prev_day(df, "close")
    if kind == "prev_week_high":
        return prev_week(df, "high")
    if kind == "prev_week_low":
        return prev_week(df, "low")
    if kind == "swing_high":
        return swing_high(df, period)
    if kind == "swing_low":
        return swing_low(df, period)
    raise ValueError(f"unknown level type {kind}")
