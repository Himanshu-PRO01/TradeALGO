"""Bridge to a self-hosted OpenAlgo instance.

OpenAlgo (open source, AGPL-3.0) already handles broker login, live and
historical data, Telegram alerts and much more. This toolkit does not copy any
of its code: it talks to it over its documented HTTP API, as a separate program.

By design this client can READ data and SEND NOTIFICATIONS. It has no function
that places, changes or cancels an order. The brother wants alerts, not
automatic orders, and a tool that cannot send orders cannot send a wrong one.

Endpoints used (from OpenAlgo's API documentation):
  POST /api/v1/history           candles: apikey, symbol, exchange, interval, start_date, end_date [, source]
  POST /api/v1/symbol            instrument details including lot size
  POST /api/v1/telegram/notify   a message to a linked Telegram user

SECURITY: the API key comes from the OPENALGO_API_KEY environment variable
(for example from a private .env file). It is never printed and is scrubbed
from error messages. Never paste it into a chat, a config file or Git.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time
import urllib.error
import urllib.request
from typing import Callable, Optional

import pandas as pd

from .data import DataError, validate_bars

DEFAULT_HOST = "http://127.0.0.1:5000"

# The intervals OpenAlgo's history endpoint accepts (a broker may support fewer).
INTERVALS = (
    "1s", "5s", "10s", "15s", "30s", "45s",
    "1m", "2m", "3m", "5m", "10m", "15m", "20m", "30m",
    "1h", "2h", "3h", "4h",
    "D", "W", "M", "Q", "Y",
)
DAILY_OR_LONGER = ("D", "W", "M", "Q", "Y")
# How many days to ask for per call. The docs say intraday data is typically only
# available for the last 30 to 90 days, so long ranges are fetched in pieces.
CHUNK_DAYS = {"seconds": 5, "minutes": 25, "hours": 80, "daily": 365}


class OpenAlgoError(RuntimeError):
    """Something a person can fix: OpenAlgo not running, wrong key, bad request."""


def load_env(path: str = ".env") -> None:
    """Read KEY=VALUE lines from a private .env file into the environment.

    Values already set in the environment win. Nothing is printed.
    """
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _http_post(url: str, body: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            detail = str(payload.get("message") or payload)
        except Exception:
            detail = exc.reason if isinstance(exc.reason, str) else ""
        raise OpenAlgoError(f"OpenAlgo answered with HTTP {exc.code}. {detail}".strip())
    except urllib.error.URLError as exc:
        raise OpenAlgoError(f"Could not reach OpenAlgo at {url.split('/api/')[0]} ({exc.reason}). "
                            "Is OpenAlgo running, and is the broker logged in for today?")
    except TimeoutError:
        raise OpenAlgoError("OpenAlgo did not answer in time.")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise OpenAlgoError("OpenAlgo sent something that is not JSON. Check OPENALGO_HOST.")


def _check_date(value: str, label: str) -> str:
    try:
        return dt.date.fromisoformat(str(value)).isoformat()
    except ValueError:
        raise OpenAlgoError(f"{label} must look like 2026-09-21 (got {value!r}).")


class OpenAlgoClient:
    def __init__(self, api_key: Optional[str] = None, host: Optional[str] = None,
                 transport: Optional[Callable] = None, timeout: float = 30.0):
        self.api_key = api_key or os.environ.get("OPENALGO_API_KEY")
        if not self.api_key:
            raise OpenAlgoError(
                "No OpenAlgo API key found. Put OPENALGO_API_KEY=... in a private .env file next to the "
                "program (never in a config file, in Git, or in a chat).")
        self.host = (host or os.environ.get("OPENALGO_HOST") or DEFAULT_HOST).rstrip("/")
        self._transport = transport or _http_post
        self.timeout = timeout

    # -------------------------------------------------------------- plumbing
    def _scrub(self, text: str) -> str:
        return text.replace(self.api_key, "***") if self.api_key else text

    def _post(self, path: str, payload: dict) -> dict:
        try:
            data = self._transport(f"{self.host}{path}", {"apikey": self.api_key, **payload}, self.timeout)
        except OpenAlgoError as exc:
            raise OpenAlgoError(self._scrub(str(exc)))
        if not isinstance(data, dict) or data.get("status") != "success":
            message = data.get("message") if isinstance(data, dict) else None
            raise OpenAlgoError(self._scrub(f"OpenAlgo reported a problem: {message or data}"))
        return data

    # ------------------------------------------------------------------ data
    def history(self, symbol: str, exchange: str, interval: str, start: str, end: str,
                source: str = "api") -> pd.DataFrame:
        """Candles as a DataFrame in this toolkit's format (naive India time, open/high/low/close/volume)."""
        if interval not in INTERVALS:
            raise OpenAlgoError(f"interval must be one of: {', '.join(INTERVALS)} (got {interval!r}).")
        if source not in ("api", "db"):
            raise OpenAlgoError("source must be 'api' (from the broker) or 'db' (OpenAlgo's stored history).")
        payload = {"symbol": symbol, "exchange": exchange, "interval": interval,
                   "start_date": _check_date(start, "start date"), "end_date": _check_date(end, "end date")}
        if source == "db":
            payload["source"] = "db"
        rows = self._post("/api/v1/history", payload).get("data") or []
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"],
                                index=pd.DatetimeIndex([], name="datetime"))
        df = pd.DataFrame(rows)
        # Timestamps are Unix epoch seconds. Convert to India time, then drop the zone label.
        stamps = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        if interval in DAILY_OR_LONGER:
            stamps = stamps.dt.normalize()
        df.index = pd.DatetimeIndex(stamps, name="datetime")
        if "volume" not in df.columns:
            df["volume"] = 0.0
        df = df[["open", "high", "low", "close", "volume"]].astype(float).sort_index()
        df = df[~df.index.duplicated(keep="first")]
        try:
            return validate_bars(df)
        except DataError as exc:
            raise OpenAlgoError(f"OpenAlgo sent price data that failed the checks: {exc}")

    def symbol_info(self, symbol: str, exchange: str) -> dict:
        return self._post("/api/v1/symbol", {"symbol": symbol, "exchange": exchange}).get("data") or {}

    def lot_size(self, symbol: str, exchange: str) -> int:
        """Lot size straight from OpenAlgo's instrument list, so it never goes stale here."""
        info = self.symbol_info(symbol, exchange)
        size = info.get("lotsize")
        if not isinstance(size, (int, float)) or size < 1:
            raise OpenAlgoError(f"OpenAlgo did not return a lot size for {symbol} on {exchange}.")
        return int(size)

    # ---------------------------------------------------------- notifications
    def telegram_notify(self, username: str, message: str, wait_for_delivery: bool = False) -> None:
        """Send a message through OpenAlgo's Telegram bot. The user must already be linked to the bot.

        With the default asynchronous mode, success means the message was queued, not confirmed delivered.
        """
        if not username or not message:
            raise OpenAlgoError("A Telegram username and a message are both needed.")
        self._post("/api/v1/telegram/notify",
                   {"username": username, "message": message, "wait_for_delivery": wait_for_delivery})


def fetch_history_range(
    client: OpenAlgoClient, symbol: str, exchange: str, interval: str, start: str, end: str,
    source: str = "api", chunk_days: Optional[int] = None, pause: float = 0.4,
    sleep: Callable[[float], None] = time.sleep,
) -> pd.DataFrame:
    """Fetch a long range in pieces and stitch it together (duplicates removed, sorted)."""
    first, last = dt.date.fromisoformat(_check_date(start, "start date")), dt.date.fromisoformat(_check_date(end, "end date"))
    if last < first:
        raise OpenAlgoError("The end date is before the start date.")
    if chunk_days is None:
        if interval.endswith("s"):
            chunk_days = CHUNK_DAYS["seconds"]
        elif interval.endswith("m"):
            chunk_days = CHUNK_DAYS["minutes"]
        elif interval.endswith("h"):
            chunk_days = CHUNK_DAYS["hours"]
        else:
            chunk_days = CHUNK_DAYS["daily"]
    if chunk_days < 1:
        raise OpenAlgoError("chunk_days must be 1 or more.")
    pieces, cursor, first_call = [], first, True
    while cursor <= last:
        window_end = min(cursor + dt.timedelta(days=chunk_days - 1), last)
        if not first_call:
            sleep(pause)                        # be gentle: OpenAlgo rate-limits its API
        first_call = False
        piece = client.history(symbol, exchange, interval, cursor.isoformat(), window_end.isoformat(), source)
        if len(piece):
            pieces.append(piece)
        cursor = window_end + dt.timedelta(days=1)
    if not pieces:
        raise OpenAlgoError("OpenAlgo returned no candles for that range. Intraday history is usually limited "
                            "to the last 30 to 90 days, and the broker must be logged in.")
    df = pd.concat(pieces).sort_index()
    return df[~df.index.duplicated(keep="first")]
