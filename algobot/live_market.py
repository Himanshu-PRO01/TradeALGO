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
        self._polling = False
        self._poll_ok = False
        self._poll_thread = None
        self._backfilled = set()
        self._history_error = ""
        self._history_bars = defaultdict(int)
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
        for key in keys:
            self._start_backfill(key)

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
                if "403" in str(error) or "forbidden" in str(error).lower():
                    self._start_polling(keys)

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
            self._start_polling(keys)
        finally:
            self._streamer = None

    def _start_polling(self, keys):
        with self._lock:
            if self._polling:
                return
            self._polling = True
            self._poll_thread = threading.Thread(
                target=self._poll_loop, args=(tuple(keys),), name="tradealgo-rest-poll", daemon=True
            )
            self._poll_thread.start()

    def _poll_loop(self, keys, interval: float = 3.0):
        import requests

        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.token}"}
        url = "https://api.upstox.com/v3/market-quote/ltp"
        while True:
            with self._lock:
                if self._connected:
                    self._polling = False
                    self._poll_ok = False
                    return
            try:
                resp = requests.get(url, headers=headers, params={"instrument_key": ",".join(keys)}, timeout=10)
                if resp.status_code != 200:
                    raise RuntimeError(f"REST quote HTTP {resp.status_code}: {resp.text[:120]}")
                self._ingest_rest(resp.json(), keys)
                with self._lock:
                    self._poll_ok = True
                    self._last_error = ""
            except Exception as exc:
                with self._lock:
                    self._poll_ok = False
                    self._last_error = f"REST fallback failed: {str(exc)[:250]}"
            time.sleep(interval)

    def _ingest_rest(self, payload, keys=(), now=None):
        data = (payload or {}).get("data") or {}
        if now is None:
            now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
        in_session = now.weekday() < 5 and (9, 0) <= (now.hour, now.minute) <= (15, 35)
        for key, item in data.items():
            if not isinstance(item, dict):
                continue
            price = _number(item.get("last_price"))
            if price is None:
                continue
            instrument = item.get("instrument_token") or str(key).replace(":", "|", 1)
            if keys and instrument not in keys and len(keys) == 1:
                instrument = keys[0]
            with self._lock:
                self._ticks[instrument].append({"datetime": now, "price": price, "quantity": 0.0})
                if in_session:
                    self._update_bar(instrument, now, price, 0.0)

    def _start_backfill(self, key):
        with self._lock:
            if key in self._backfilled:
                return
            self._backfilled.add(key)
        threading.Thread(
            target=self._backfill_history, args=(key,), name="tradealgo-backfill", daemon=True
        ).start()

    def _backfill_history(self, key):
        import requests
        from urllib.parse import quote

        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.token}"}
        base = "https://api.upstox.com/v3/historical-candle"
        enc = quote(key, safe="")
        today = pd.Timestamp.now(tz="Asia/Kolkata").date()
        urls = [
            f"{base}/{enc}/minutes/1/{today}/{today - pd.Timedelta(days=7)}",
            f"{base}/intraday/{enc}/minutes/1",
        ]
        rows, errors = {}, []
        endpoint_results = []
        for url in urls:
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:180]}")
                payload = resp.json()
                parsed = _parse_candles(payload)
                endpoint_results.append((url, len(parsed)))
                for row in parsed:
                    rows[row["datetime"]] = row
            except Exception as exc:
                endpoint_results.append((url, 0))
                errors.append(str(exc)[:180])

        if not rows and not errors:
            errors.append("Upstox returned 200 but no OHLC candles for this instrument/time range.")

        with self._lock:
            self._history_error = "; ".join(errors) if errors else ""
        if rows:
            self._merge_history(key, list(rows.values()))
            with self._lock:
                self._history_bars[key] = len(rows)
                self._history_error = ""

    def _merge_history(self, key, rows):
        with self._lock:
            merged = {row["datetime"]: row for row in rows}
            for bar in self._bars[key]:
                merged[bar["datetime"]] = bar
            self._bars[key] = deque(sorted(merged.values(), key=lambda b: b["datetime"]), maxlen=_MAX_BARS)

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

    def snapshot(self, instrument_key: str, max_bars: int = 300, interval_minutes: int = 1) -> pd.DataFrame:
        """Return Upstox OHLCV candles, optionally aggregated to a larger timeframe."""
        with self._lock:
            rows = list(self._bars.get(instrument_key, ()))
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.DataFrame(rows).drop_duplicates("datetime", keep="last").set_index("datetime").sort_index()
        interval_minutes = max(1, int(interval_minutes))
        if interval_minutes > 1:
            df = df.resample(f"{interval_minutes}min", origin="start_day").agg(
                open=("open", "first"),
                high=("high", "max"),
                low=("low", "min"),
                close=("close", "last"),
                volume=("volume", "sum"),
            ).dropna(subset=["open", "high", "low", "close"])
        return df.tail(max_bars)

    def latest(self, instrument_key: str) -> dict | None:
        with self._lock:
            ticks = self._ticks.get(instrument_key)
            if not ticks:
                return None
            return dict(ticks[-1])

    def status(self) -> dict:
        with self._lock:
            return {
                "connected": self._connected or self._poll_ok,
                "history_error": self._history_error,
                "history_bars": dict(self._history_bars),
                "mode": "websocket" if self._connected else ("rest-polling" if self._poll_ok else "none"),
                "started_at": self._started_at,
                "last_error": self._last_error,
                "ticks": sum(len(v) for v in self._ticks.values()),
            }


_HUBS = {}
_HUBS_LOCK = threading.Lock()


def get_market_hub(token: str) -> LiveMarketHub:
    if not token:
        raise ValueError("No Upstox market-data token is configured.")
    import hashlib

    key = hashlib.sha256(token.encode()).hexdigest()
    with _HUBS_LOCK:
        hub = _HUBS.get(key)
        if hub is None:
            hub = LiveMarketHub(token)
            _HUBS[key] = hub
        return hub


def _parse_candles(payload):
    """Upstox candle rows: [timestamp, open, high, low, close, volume, oi]."""
    candles = ((payload or {}).get("data") or {}).get("candles") or []
    out = []
    for c in candles:
        try:
            ts = pd.Timestamp(c[0])
            if ts.tzinfo is not None:
                ts = ts.tz_convert("Asia/Kolkata").tz_localize(None)
            out.append(
                {
                    "datetime": ts.floor("min"),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]) if len(c) > 5 and c[5] is not None else 0.0,
                }
            )
        except (TypeError, ValueError, IndexError):
            continue
    return out
