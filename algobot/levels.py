"""Support and resistance levels that can be used in rules.

All of these are safe from look-ahead bias:

* prev_day_*  / prev_week_*: the finished previous day (or week), so a level
  is only used after it has fully formed.
* swing_high / swing_low: a swing high is a bar whose high is the highest of
  `period` bars on each side. It can only be known `period` bars AFTER it
  happened, so the level appears with exactly that delay and is then carried
  forward until the next swing is confirmed.
* opening_range_high / opening_range_low: the highest high / lowest low of
  the first `period` MINUTES of each trading day (the "opening range"). The
  level is blank (NaN) while that window is still forming and only appears,
  frozen for the rest of the day, on the first bar after the window closes -
  so a rule can never use a range that hasn't finished forming yet.
* pivot, pivot_r1..r3, pivot_s1..s3: classic floor-trader pivot points,
  built only from the previous (finished) day's high/low/close, the same
  no-look-ahead source as prev_day_high/low/close.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LEVEL_TYPES = (
    "prev_day_high", "prev_day_low", "prev_day_close",
    "prev_week_high", "prev_week_low",
    "swing_high", "swing_low",
    "opening_range_high", "opening_range_low",
    "pivot", "pivot_r1", "pivot_r2", "pivot_r3", "pivot_s1", "pivot_s2", "pivot_s3",
)
SWING_TYPES = ("swing_high", "swing_low")
OPENING_RANGE_TYPES = ("opening_range_high", "opening_range_low")
PIVOT_TYPES = ("pivot", "pivot_r1", "pivot_r2", "pivot_r3", "pivot_s1", "pivot_s2", "pivot_s3")


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


def opening_range(df: pd.DataFrame, minutes: int, which: str) -> pd.Series:
    """Highest high / lowest low of the first `minutes` of each trading day.

    Blank while the window is still forming (using an unfinished range would
    be look-ahead: price could still make a new high/low before the window
    closes). Freezes at the value observed when the window closes and holds
    that value for the rest of the day.
    """
    day = df.index.normalize()
    session_start = pd.Series(df.index, index=df.index).groupby(day).transform("first")
    elapsed = pd.Series(df.index, index=df.index) - session_start
    in_window = elapsed < pd.Timedelta(minutes=minutes)

    col, how = {"high": ("high", "max"), "low": ("low", "min")}[which]
    windowed = df[col].where(in_window)
    cum = windowed.groupby(day).cummax() if how == "max" else windowed.groupby(day).cummin()
    frozen = cum.groupby(day).ffill()
    return frozen.where(~in_window)


def pivot_points(df: pd.DataFrame, which: str) -> pd.Series:
    """Classic floor-trader pivot points from the previous (finished) day's H/L/C.

    P = (H + L + C) / 3, then R1/R2/R3 and S1/S2/S3 fan out from P using the
    previous day's range. Same source data (and same no-look-ahead guarantee)
    as prev_day_high/low/close.
    """
    ph, pl, pc = prev_day(df, "high"), prev_day(df, "low"), prev_day(df, "close")
    p = (ph + pl + pc) / 3.0
    rng = ph - pl
    return {
        "p": p,
        "r1": 2 * p - pl,
        "s1": 2 * p - ph,
        "r2": p + rng,
        "s2": p - rng,
        "r3": ph + 2 * (p - pl),
        "s3": pl - 2 * (ph - p),
    }[which]


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
    if kind == "opening_range_high":
        return opening_range(df, period, "high")
    if kind == "opening_range_low":
        return opening_range(df, period, "low")
    if kind in PIVOT_TYPES:
        which = "p" if kind == "pivot" else kind.removeprefix("pivot_")
        return pivot_points(df, which)
    raise ValueError(f"unknown level type {kind}")
