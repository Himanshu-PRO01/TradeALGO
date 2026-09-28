"""Shared real-time market-data hub for TradeALGO.

The LLM is never the source of market prices. Upstox Market Data Feed V3 supplies
the ticks; this module keeps a small thread-safe rolling cache that Streamlit
sessions can read concurrently. Paper-trading state remains session-scoped.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

import pandas as pd


INSTRUMENTS = {
    "Nifty 50": "NSE_INDEX|Nifty 50",
    "Nifty Bank": "NSE_INDEX|Nifty Bank",
    "Sensex": "BSE_INDEX|SENSEX",
    "India VIX": "NSE_INDEX|India VIX",
}

_MAX_TICKS = 12000
_MAX_BARS = 1200


def _secret(name: str):
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None


def market_data_token() -> str:
    """Read a read-only market-data token without ever rendering it."""
    value = os.environ.get("UPSTOX_ANALYTICS_TOKEN") or _secret("UPSTOX_ANALYTICS_TOKEN")
    if not value:
        value = os.environ.get("UPSTOX_ACCESS_TOKEN") or _secret("UPSTOX_ACCESS_TOKEN")
    return str(value).strip() if value else ""


def _as_dict(value):
    if isinstance(value, dict):
        return value
    for name in ("to_dict", "toDict"):
        fn = getattr(value, name, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    if isinstance(value, (bytes, bytearray)):
        try:
            return json.loads(value.decode("utf-8"))
        except Exception:
            return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None
    return None


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class LiveMarketHub:
    """One market stream per process, shared by all Streamlit sessions.

    Each browser session only reads this cache; its fake-money ledger remains
    isolated in Streamlit Session State.
    """

    def __init__(self, token: str):
        self.token = token
        self._lock = threading.RLock()
        self._thread = None
        self._streamer = None
        self._started_at = None
        self._connected = False
        self._last_error = ""
        self._ticks = defaultdict(lambda: deque(maxlen=_MAX_TICKS))
        self._bars = defaultdict(lambda: deque(maxlen=_MAX_BARS))

    def start(self, instrument_keys=None):
        keys = tuple(instrument_keys or [INSTRUMENTS["Nifty 50"]])
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._started_at = datetime.now(timezone.utc)
            self._last_error = ""
            self._thread = threading.Thread(
                target=self._run, args=(keys,), name="tradealgo-market-feed", daemon=True
            )
            self._thread.start()

    def _run(self, keys):
        try:
            import upstox_client
        except ImportError as exc:
            with self._lock:
                self._last_error = "upstox-python-sdk is not installed."
            return

        try:
            configuration = upstox_client.Configuration()
            configuration.access_token = self.token
            streamer = upstox_client.MarketDataStreamerV3(
                upstox_client.ApiClient(configuration), list(keys), "full"
            )
            self._streamer = streamer

            def on_open():
                with self._lock:
                    self._connected = True
                    self._last_error = ""
                # Re-subscribe explicitly after reconnect/open.
                try:
                    streamer.subscribe(list(keys), "full")
                except Exception:
                    pass

            def on_close(*_):
                with self._lock:
                    self._connected = False

            def on_error(error):
                with self._lock:
                    self._connected = False
                    self._last_error = str(error)[:300]

            def on_message(message):
                self._ingest(message)

            streamer.on("open", on_open)
            streamer.on("close", on_close)
            streamer.on("error", on_error)
            streamer.on("message", on_message)
            try:
                streamer.auto_reconnect(True, 5, 20)
            except Exception:
                pass
            streamer.connect()
        except Exception as exc:
            with self._lock:
                self._connected = False
                self._last_error = str(exc)[:300]
        finally:
            self._streamer = None

    def _ingest(self, raw):
        payload = _as_dict(raw)
        if not isinstance(payload, dict):
            return
        feeds = payload.get("feeds") or {}
        now_ms = payload.get("currentTs") or int(time.time() * 1000)
        for instrument, feed in feeds.items():
            if not isinstance(feed, dict):
                continue
            ltpc = feed.get("ltpc") or {}
            price = _number(ltpc.get("ltp"))
            if price is None:
                # Some SDK payloads nest LTPC under fullFeed/marketFF.
                full = feed.get("fullFeed") or {}
                market = full.get("marketFF") or {}
                ltpc = market.get("ltpc") or {}
                price = _number(ltpc.get("ltp"))
            if price is None:
                continue
            ts_ms = _number(ltpc.get("ltt")) or _number(now_ms)
            timestamp = pd.to_datetime(int(ts_ms), unit="ms", utc=True).tz_convert("Asia/Kolkata").tz_localize(None)
            qty = _number(ltpc.get("ltq")) or 0.0
            tick = {"datetime": timestamp, "price": price, "quantity": qty}
            with self._lock:
                self._ticks[instrument].append(tick)
                self._update_bar(instrument, timestamp, price, qty)

    def _update_bar(self, instrument, timestamp, price, quantity):
        minute = timestamp.floor("min")
        bars = self._bars[instrument]
        if bars and bars[-1]["datetime"] == minute:
            bar = bars[-1]
            bar["high"] = max(bar["high"], price)
            bar["low"] = min(bar["low"], price)
            bar["close"] = price
            bar["volume"] += quantity
        else:
            bars.append(
                {
                    "datetime": minute,
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": quantity,
                }
            )

    def snapshot(self, instrument_key: str, max_bars: int = 300) -> pd.DataFrame:
        with self._lock:
            rows = list(self._bars.get(instrument_key, ()))
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.DataFrame(rows).drop_duplicates("datetime", keep="last").set_index("datetime")
        return df.tail(max_bars).sort_index()

    def latest(self, instrument_key: str) -> dict | None:
        with self._lock:
            ticks = self._ticks.get(instrument_key)
            if not ticks:
                return None
            return dict(ticks[-1])

    def status(self) -> dict:
        with self._lock:
            return {
                "connected": self._connected,
                "started_at": self._started_at,
                "last_error": self._last_error,
                "ticks": sum(len(v) for v in self._ticks.values()),
            }


_HUBS = {}
_HUBS_LOCK = threading.Lock()


def get_market_hub(token: str) -> LiveMarketHub:
    if not token:
        raise ValueError("No Upstox market-data token is configured.")
    # A token hash is used only as an in-process cache key; the token itself is
    # never logged or returned.
    import hashlib

    key = hashlib.sha256(token.encode()).hexdigest()
    with _HUBS_LOCK:
        hub = _HUBS.get(key)
        if hub is None:
            hub = LiveMarketHub(token)
            _HUBS[key] = hub
        return hub
