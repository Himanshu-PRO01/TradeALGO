"""Market data: loading CSV files and generating synthetic test data.

The synthetic data is a random walk. It exists ONLY to test that the software
works end to end. It contains no real market behaviour, so results on it say
nothing about whether a strategy is any good.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class DataError(ValueError):
    """Raised when a data file has a problem the user should fix."""


TIME_COLUMNS = ("datetime", "timestamp", "date", "time")
PRICE_COLUMNS = ["open", "high", "low", "close"]


def validate_bars(df: pd.DataFrame) -> pd.DataFrame:
    """Check that price bars are clean. Bad data quietly ruins backtests."""
    if df.empty:
        raise DataError("The data has no rows.")
    if df[PRICE_COLUMNS].isna().any().any():
        raise DataError("The data has empty (missing) prices. Fix or remove those rows.")
    if (df[PRICE_COLUMNS] <= 0).any().any():
        raise DataError("The data has zero or negative prices.")
    tol = 1e-9
    if (df["high"] < df["low"] - tol).any():
        raise DataError("Some rows have high below low.")
    if (df["high"] < df[["open", "close"]].max(axis=1) - tol).any():
        raise DataError("Some rows have a high below the open or close.")
    if (df["low"] > df[["open", "close"]].min(axis=1) + tol).any():
        raise DataError("Some rows have a low above the open or close.")
    return df


def load_csv(path: str) -> pd.DataFrame:
    """Load OHLCV bars from a CSV file.

    Needed columns: a time column (datetime / timestamp / date / time), and
    open, high, low, close. A volume column is optional.
    """
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        raise DataError(f"Data file not found: {path}")
    df.columns = [str(c).strip().lower() for c in df.columns]

    time_col = next((c for c in TIME_COLUMNS if c in df.columns), None)
    if time_col is None:
        raise DataError(
            "The data needs a time column named one of: " + ", ".join(TIME_COLUMNS)
        )
    missing = [c for c in PRICE_COLUMNS if c not in df.columns]
    if missing:
        raise DataError("The data is missing columns: " + ", ".join(missing))

    try:
        df[time_col] = pd.to_datetime(df[time_col])
    except (ValueError, TypeError) as exc:
        raise DataError(f"Could not read the time column '{time_col}': {exc}")
    df = df.set_index(time_col).sort_index()
    df.index.name = "datetime"
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df[~df.index.duplicated(keep="first")]

    if "volume" not in df.columns:
        df["volume"] = 0.0
    df = df[PRICE_COLUMNS + ["volume"]].astype(float)
    return validate_bars(df)


def generate_sample_data(
    days: int = 60,
    bars_per_day: int = 75,
    minutes_per_bar: int = 5,
    start_price: float = 1000.0,
    drift: float = 0.0,
    vol_per_bar: float = 0.0008,
    start_date: str = "2025-01-01",
    seed: int = 42,
    autocorr: float = 0.0,
) -> pd.DataFrame:
    """Random-walk intraday bars (default: 75 five-minute bars, 09:15 to 15:25).

    autocorr > 0 plants a trend (each bar's move partly repeats the last one),
    < 0 plants mean reversion. It exists to test the audit: a checker must say
    "no edge" on pure noise AND recognise an edge when one truly exists.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start_date, periods=days)
    rows = []
    prev_close = float(start_price)
    last_return = 0.0
    for d in dates:
        gap = rng.normal(0.0, 0.003)
        returns = rng.normal(drift, vol_per_bar, bars_per_day)
        if autocorr:
            for k in range(bars_per_day):
                previous = returns[k - 1] if k else last_return
                returns[k] = returns[k] + autocorr * previous
            last_return = float(returns[-1])
        first_open = prev_close * (1.0 + gap)
        closes = first_open * np.exp(np.cumsum(returns))
        opens = np.concatenate([[first_open], closes[:-1]])
        wick_up = np.abs(rng.normal(0.0, vol_per_bar / 2.0, bars_per_day))
        wick_dn = np.abs(rng.normal(0.0, vol_per_bar / 2.0, bars_per_day))
        highs = np.maximum(opens, closes) * (1.0 + wick_up)
        lows = np.minimum(opens, closes) * (1.0 - wick_dn)
        volumes = rng.integers(1000, 20000, bars_per_day)
        day_start = pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=15)
        for k in range(bars_per_day):
            o, c = round(opens[k], 2), round(closes[k], 2)
            h = round(max(highs[k], o, c), 2)
            l = round(min(lows[k], o, c), 2)
            rows.append(
                (day_start + pd.Timedelta(minutes=minutes_per_bar * k), o, h, l, c, float(volumes[k]))
            )
        prev_close = float(closes[-1])
    df = pd.DataFrame(rows, columns=["datetime", "open", "high", "low", "close", "volume"])
    return df.set_index("datetime")
