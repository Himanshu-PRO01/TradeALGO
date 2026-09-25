"""Indicators that can be used in rule expressions.

Every indicator only looks at the current and past bars, never the future.
`highest` and `lowest` look at the PREVIOUS n bars (excluding the current one)
so that a breakout rule like "close > highest_20" can actually be true.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ConfigError
from .levels import LEVEL_TYPES, SWING_TYPES, OPENING_RANGE_TYPES, compute_level

BASE_COLUMNS = ("open", "high", "low", "close", "volume")
INDICATOR_TYPES = ("sma", "ema", "rsi", "atr", "highest", "lowest", "vwap") + LEVEL_TYPES
_NEEDS_PERIOD = SWING_TYPES + OPENING_RANGE_TYPES
NEEDS_NO_PERIOD = ("vwap",) + tuple(k for k in LEVEL_TYPES if k not in _NEEDS_PERIOD)


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(s: pd.Series, n: int) -> pd.Series:
    """Wilder's RSI."""
    delta = s.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    # No losses at all in the window means RSI is 100.
    out = out.where(~((avg_loss == 0.0) & avg_gain.notna()), 100.0)
    # A perfectly flat price has no direction at all: call it neutral.
    out = out.where(~((avg_loss == 0.0) & (avg_gain == 0.0)), 50.0)
    return out


def atr(df: pd.DataFrame, n: int) -> pd.Series:
    """Average true range (Wilder smoothing)."""
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def highest(df: pd.DataFrame, n: int) -> pd.Series:
    """Highest high of the previous n bars (current bar excluded)."""
    return df["high"].rolling(n).max().shift(1)


def lowest(df: pd.DataFrame, n: int) -> pd.Series:
    """Lowest low of the previous n bars (current bar excluded)."""
    return df["low"].rolling(n).min().shift(1)


def vwap(df: pd.DataFrame) -> pd.Series:
    """Volume-weighted average price, restarting every day."""
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    day = df.index.normalize()
    cum_pv = (typical * df["volume"]).groupby(day).cumsum()
    cum_v = df["volume"].groupby(day).cumsum()
    return cum_pv / cum_v.replace(0.0, np.nan)


def add_indicators(df: pd.DataFrame, specs: list) -> pd.DataFrame:
    """Add one column per indicator spec, e.g. {name: ema_fast, type: ema, period: 9}."""
    if specs is None:
        specs = []
    if not isinstance(specs, list):
        raise ConfigError("'indicators' must be a list, one item per indicator.")
    df = df.copy()
    for i, spec in enumerate(specs, start=1):
        if not isinstance(spec, dict):
            raise ConfigError(f"Indicator #{i} must have settings like: name, type, period.")
        unknown = set(spec) - {"name", "type", "period", "source"}
        if unknown:
            raise ConfigError(
                f"Indicator #{i} has unknown settings: {', '.join(sorted(unknown))}. "
                "Allowed: name, type, period, source."
            )
        name, kind = spec.get("name"), spec.get("type")
        if not isinstance(name, str) or not name.isidentifier():
            raise ConfigError(
                f"Indicator #{i} needs a 'name' made of letters, digits and underscores "
                "(for example ema_fast)."
            )
        if name in df.columns or name in BASE_COLUMNS or name.endswith("_prev"):
            raise ConfigError(f"Indicator name '{name}' is already used or not allowed.")
        if kind not in INDICATOR_TYPES:
            raise ConfigError(
                f"Indicator '{name}' has unknown type {kind!r}. "
                f"Allowed types: {', '.join(INDICATOR_TYPES)}."
            )
        period = spec.get("period")
        if kind not in NEEDS_NO_PERIOD:
            if isinstance(period, bool) or not isinstance(period, int) or period < 1:
                raise ConfigError(f"Indicator '{name}' needs a whole-number 'period' of 1 or more.")
        source = spec.get("source", "close")
        if source not in BASE_COLUMNS:
            raise ConfigError(f"Indicator '{name}': 'source' must be one of {', '.join(BASE_COLUMNS)}.")

        if kind == "sma":
            df[name] = sma(df[source], period)
        elif kind == "ema":
            df[name] = ema(df[source], period)
        elif kind == "rsi":
            df[name] = rsi(df[source], period)
        elif kind == "atr":
            df[name] = atr(df, period)
        elif kind == "highest":
            df[name] = highest(df, period)
        elif kind == "lowest":
            df[name] = lowest(df, period)
        elif kind == "vwap":
            df[name] = vwap(df)
        elif kind in LEVEL_TYPES:
            df[name] = compute_level(df, kind, period)
    return df


def add_prev_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add <column>_prev (the previous bar's value) for every column.

    This is how rules detect crossovers, for example:
    "ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev".
    """
    df = df.copy()
    for col in list(df.columns):
        if not col.endswith("_prev"):
            df[f"{col}_prev"] = df[col].shift(1)
    return df
