"""Real NSE candles for the dashboard's main chart, sourced from the operator's own
broker connection through OpenAlgo -- not from TradingView's widgets.

Why this exists: TradingView's free embeddable widgets can show BSE data but not NSE
data (NSE:NIFTY and friends come back "only available on TradingView" -- a data
redistribution restriction on TradingView's side, not a bug here). The fix is to stop
asking TradingView to redistribute NSE data at all, and instead chart the same candles
this toolkit already knows how to fetch from OpenAlgo (see openalgo_bridge.py) using
its own Altair candlestick renderer (see charts.py).

This needs OPENALGO_API_KEY (and optionally OPENALGO_HOST) configured -- as a local
.env file when run locally, or as a Streamlit secret when hosted. That is the site
OPERATOR's own broker connection, set once on the server; it is never requested from
a visitor in the UI, so this does not conflict with "the app never asks for broker
keys" -- that promise is about visitors, not about the operator's own server secrets.
When it is not configured (e.g. this dashboard's public demo deployment), every
function here returns None/False instead of raising, so the page can show a clear
"not connected" message instead of fake data standing in for a real symbol.
"""
from __future__ import annotations

import datetime as dt
import os
from typing import Optional

import pandas as pd
import streamlit as st

from .openalgo_bridge import OpenAlgoClient, OpenAlgoError, fetch_history_range

# Our TradingView-style dashboard symbols -> OpenAlgo (symbol, exchange).
SYMBOL_MAP: dict[str, tuple[str, str]] = {
    "NSE:NIFTY": ("NIFTY", "NSE_INDEX"),
    "NSE:BANKNIFTY": ("BANKNIFTY", "NSE_INDEX"),
    "NSE:FINNIFTY": ("FINNIFTY", "NSE_INDEX"),
    "NSE:MIDCPNIFTY": ("MIDCPNIFTY", "NSE_INDEX"),
    "NSE:RELIANCE": ("RELIANCE", "NSE"),
    "NSE:HDFCBANK": ("HDFCBANK", "NSE"),
    "NSE:ICICIBANK": ("ICICIBANK", "NSE"),
    # Continuous-futures symbols as offered by Trading_Desk.py's own symbol picker --
    # OpenAlgo has no separate "continuous future" concept, so these chart the underlying index.
    "NSE:NIFTY1!": ("NIFTY", "NSE_INDEX"),
    "NSE:BANKNIFTY1!": ("BANKNIFTY", "NSE_INDEX"),
}

# Our dashboard interval codes -> OpenAlgo interval strings.
INTERVAL_MAP: dict[str, str] = {
    "1": "1m", "5": "5m", "15": "15m", "30": "30m", "60": "1h", "D": "D", "W": "W",
}

# How many calendar days of history to pull for each interval, so intraday charts
# show a handful of recent sessions and daily/weekly charts show a longer run.
LOOKBACK_DAYS = {"1m": 5, "5m": 10, "15m": 15, "30m": 20, "1h": 30, "D": 365, "W": 1095}


def _secret(name: str) -> Optional[str]:
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def openalgo_configured() -> bool:
    """True once the operator has set an OpenAlgo API key (.env locally, or a Streamlit secret when hosted)."""
    return bool(os.environ.get("OPENALGO_API_KEY") or _secret("openalgo_api_key"))


def _client() -> OpenAlgoClient:
    api_key = os.environ.get("OPENALGO_API_KEY") or _secret("openalgo_api_key")
    host = os.environ.get("OPENALGO_HOST") or _secret("openalgo_host")
    return OpenAlgoClient(api_key=api_key, host=host)


@st.cache_data(ttl=60, show_spinner=False)
def _fetch(symbol: str, exchange: str, interval: str, start: str, end: str,
           api_key: str, host: Optional[str]) -> pd.DataFrame:
    """Cached for a minute so switching timeframes doesn't hammer the broker's API on every rerun."""
    client = OpenAlgoClient(api_key=api_key, host=host)
    return fetch_history_range(client, symbol, exchange, interval, start, end)


def fetch_candles(dashboard_symbol: str, dashboard_interval: str) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """Real candles for a dashboard symbol/interval, or (None, a human-readable reason why not).

    Never raises: any OpenAlgo/connection problem comes back as the second element instead.
    """
    if not openalgo_configured():
        return None, (
            "Not connected to OpenAlgo yet. Set OPENALGO_API_KEY (and OPENALGO_HOST if OpenAlgo isn't "
            "on this machine) in a local .env file, or as this app's Streamlit secrets when hosted -- "
            "see the README's \"Connecting to your OpenAlgo\" section."
        )
    mapping = SYMBOL_MAP.get(dashboard_symbol)
    if mapping is None:
        return None, f"{dashboard_symbol} isn't mapped to an OpenAlgo symbol/exchange yet."
    symbol, exchange = mapping
    interval = INTERVAL_MAP.get(dashboard_interval)
    if interval is None:
        return None, f"Timeframe {dashboard_interval!r} isn't mapped to an OpenAlgo interval yet."
    end = dt.date.today()
    start = end - dt.timedelta(days=LOOKBACK_DAYS.get(interval, 10))
    try:
        api_key = os.environ.get("OPENALGO_API_KEY") or _secret("openalgo_api_key")
        host = os.environ.get("OPENALGO_HOST") or _secret("openalgo_host")
        df = _fetch(symbol, exchange, interval, start.isoformat(), end.isoformat(), api_key, host)
    except OpenAlgoError as exc:
        return None, str(exc)
    except Exception as exc:  # pragma: no cover -- unexpected transport/library error, still shouldn't crash the page
        return None, f"Could not fetch candles from OpenAlgo: {exc}"
    if df is None or df.empty:
        return None, f"OpenAlgo returned no candles for {symbol} on {exchange} at {interval}."
    return df, None
