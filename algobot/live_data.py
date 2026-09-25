"""Delayed market data for the Live Markets page.

Uses Yahoo Finance via `yfinance`. This is FREE data that is typically
15-20 minutes delayed for NSE/BSE indices -- it is NOT a live tick feed and
is completely separate from the Upstox Sandbox page (which only tests order
placement, never prices). Nothing in this module places an order or talks
to a broker; it only reads prices to draw a chart.
"""
from __future__ import annotations

import pandas as pd

MARKETS: dict[str, str] = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "Bank Nifty": "^NSEBANK",
    "Nifty IT": "^CNXIT",
    "Nifty Midcap 100": "^NSEMDCP",
    "India VIX": "^INDIAVIX",
    "USD/INR": "INR=X",
}

# label -> (yfinance interval, yfinance period). Yahoo limits how far back
# intraday intervals go (1m: ~7 days, 5m/15m: ~60 days), hence the periods.
INTERVALS: dict[str, tuple[str, str]] = {
    "1 minute (scalping)": ("1m", "1d"),
    "5 minutes (intraday)": ("5m", "5d"),
    "15 minutes": ("15m", "1mo"),
    "1 hour": ("60m", "3mo"),
    "1 day": ("1d", "1y"),
}


class LiveDataError(RuntimeError):
    """Market data could not be fetched."""


def fetch_ohlc(ticker: str, interval: str, period: str) -> pd.DataFrame:
    """OHLCV bars for `ticker` at `interval` over `period`, via Yahoo Finance."""
    try:
        import yfinance as yf
    except ImportError as exc:
        raise LiveDataError(
            "yfinance is not installed. Redeploy after adding yfinance to requirements.txt."
        ) from exc
    try:
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=False)
    except Exception as exc:
        raise LiveDataError(f"Could not fetch data for {ticker}: {exc}") from exc
    if df is None or df.empty:
        raise LiveDataError(
            f"No data returned for {ticker}. Markets may be closed, or Yahoo Finance has no "
            "data for this symbol/interval right now."
        )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns=str.lower)
    df.index.name = "datetime"
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)
    keep = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
    df = df[keep].astype(float)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df
