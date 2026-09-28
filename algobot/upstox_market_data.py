"""Upstox Market Data V3 adapter for TradeALGO research/paper use.

This module only consumes market data. It never places or modifies orders.
The access token is read from the environment or Streamlit secrets by the page,
and is never persisted in the repository.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Any

from .config import ConfigError


@dataclass(frozen=True)
class MarketTick:
    instrument_key: str
    ltp: float | None
    ltt: int | None
    received_ts: int | None
    bid_price: float | None = None
    ask_price: float | None = None
    bid_qty: int | None = None
    ask_qty: int | None = None
    oi: float | None = None
    volume: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    rho: float | None = None


class UpstoxMarketData:
    """Small process-local V3 WebSocket client with a bounded tick buffer."""

    def __init__(
        self,
        access_token: str,
        instrument_keys: list[str],
        mode: str = "full",
        max_ticks: int = 5000,
    ) -> None:
        if not access_token.strip():
            raise ConfigError("Upstox access token is empty.")
        if not instrument_keys:
            raise ConfigError("At least one Upstox instrument key is required.")
        if mode not in {"ltpc", "full", "full_d30", "option_greeks"}:
            raise ConfigError("Upstox feed mode must be ltpc, full, full_d30, or option_greeks.")

        try:
            import upstox_client
        except ImportError as exc:
            raise ConfigError(
                "The upstox-python-sdk package is not installed. Run: pip install -r requirements.txt"
            ) from exc

        self._sdk = upstox_client
        self.access_token = access_token.strip()
        self.instrument_keys = list(dict.fromkeys(k.strip() for k in instrument_keys if k.strip()))
        self.mode = mode
        self.max_ticks = max(100, int(max_ticks))
        self._queue: queue.Queue[MarketTick] = queue.Queue(maxsize=self.max_ticks)
        self._latest: dict[str, MarketTick] = {}
        self._lock = threading.Lock()
        self._streamer = None
        self._thread: threading.Thread | None = None
        self._connected = False
        self._last_error: str | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def _extract_tick(self, instrument_key: str, feed: Any, received_ts: int | None) -> MarketTick | None:
        # SDK versions expose generated protobuf objects differently. Convert to
        # a plain dict where possible, while also accepting dictionary payloads.
        if isinstance(feed, dict):
            root = feed
        elif hasattr(feed, "to_dict"):
            root = feed.to_dict()
        elif hasattr(feed, "__dict__"):
            root = dict(feed.__dict__)
        else:
            return None

        def first(*paths):
            for path in paths:
                value = root
                try:
                    for part in path.split("."):
                        if isinstance(value, dict):
                            value = value.get(part)
                        else:
                            value = getattr(value, part, None)
                    if value is not None:
                        return value
                except Exception:
                    continue
            return None

        ltp = first("ltpc.ltp", "firstLevelWithGreeks.ltpc.ltp", "fullFeed.ltpc.ltp", "ltp")
        ltt = first("ltpc.ltt", "firstLevelWithGreeks.ltpc.ltt", "fullFeed.ltpc.ltt")
        depth = first("firstLevelWithGreeks.firstDepth", "fullFeed.firstLevelWithGreeks.firstDepth", "firstDepth")
        greeks = first("firstLevelWithGreeks.optionGreeks", "fullFeed.optionGreeks", "optionGreeks")

        def nested(obj, key):
            if isinstance(obj, dict):
                return obj.get(key)
            return getattr(obj, key, None) if obj is not None else None

        bid = nested(depth, "bidP")
        ask = nested(depth, "askP")
        bid_q = nested(depth, "bidQ")
        ask_q = nested(depth, "askQ")

        volume = first("fullFeed.vtt", "vtt")
        oi = first("fullFeed.oi", "oi")
        return MarketTick(
            instrument_key=instrument_key,
            ltp=float(ltp) if ltp is not None else None,
            ltt=int(ltt) if ltt is not None else None,
            received_ts=int(received_ts) if received_ts is not None else None,
            bid_price=float(bid) if bid is not None else None,
            ask_price=float(ask) if ask is not None else None,
            bid_qty=int(bid_q) if bid_q is not None else None,
            ask_qty=int(ask_q) if ask_q is not None else None,
            oi=float(oi) if oi is not None else None,
            volume=float(volume) if volume is not None else None,
            delta=float(nested(greeks, "delta")) if nested(greeks, "delta") is not None else None,
            gamma=float(nested(greeks, "gamma")) if nested(greeks, "gamma") is not None else None,
            theta=float(nested(greeks, "theta")) if nested(greeks, "theta") is not None else None,
            vega=float(nested(greeks, "vega")) if nested(greeks, "vega") is not None else None,
            rho=float(nested(greeks, "rho")) if nested(greeks, "rho") is not None else None,
        )

    def _on_message(self, message: Any) -> None:
        received_ts = int(time.time() * 1000)
        payload = message.to_dict() if hasattr(message, "to_dict") else message
        feeds = payload.get("feeds", {}) if isinstance(payload, dict) else {}
        current_ts = payload.get("currentTs") if isinstance(payload, dict) else None
        if current_ts is not None:
            try:
                received_ts = int(current_ts)
            except (TypeError, ValueError):
                pass

        for key, feed in feeds.items():
            tick = self._extract_tick(key, feed, received_ts)
            if tick is None:
                continue
            with self._lock:
                self._latest[key] = tick
            try:
                self._queue.put_nowait(tick)
            except queue.Full:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self._queue.put_nowait(tick)
                except queue.Full:
                    pass

    def _on_error(self, error: Any) -> None:
        self._last_error = str(error)
        self._connected = False

    def _on_open(self) -> None:
        self._connected = True
        self._last_error = None
        self._streamer.subscribe(self.instrument_keys, self.mode)

    def _on_close(self, *args) -> None:
        self._connected = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        def run() -> None:
            try:
                configuration = self._sdk.Configuration()
                configuration.access_token = self.access_token
                api_client = self._sdk.ApiClient(configuration)
                self._streamer = self._sdk.MarketDataStreamerV3(api_client)
                self._streamer.on("open", self._on_open)
                self._streamer.on("message", self._on_message)
                self._streamer.on("error", self._on_error)
                self._streamer.on("close", self._on_close)
                self._streamer.connect()
            except Exception as exc:
                self._last_error = str(exc)
                self._connected = False

        self._thread = threading.Thread(target=run, name="tradealgo-upstox-feed", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        streamer = self._streamer
        if streamer is not None:
            try:
                streamer.disconnect()
            except Exception:
                pass
        self._connected = False

    def snapshot(self) -> dict[str, MarketTick]:
        with self._lock:
            return dict(self._latest)

    def drain(self, limit: int = 250) -> list[MarketTick]:
        ticks: list[MarketTick] = []
        for _ in range(max(1, int(limit))):
            try:
                ticks.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return ticks
