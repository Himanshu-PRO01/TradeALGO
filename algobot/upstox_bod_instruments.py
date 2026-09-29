"""Read-only Upstox BOD instrument lookup for sandbox order forms.

The sandbox order API expects the instrument_token/instrument_key of the exact
contract. Upstox publishes BOD instrument JSON files containing those keys.
This resolver does not authenticate or place orders.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from .config import ConfigError


@dataclass(frozen=True)
class InstrumentRef:
    instrument_key: str
    trading_symbol: str
    instrument_type: str
    strike_price: float | None
    expiry: str | None
    lot_size: int | None


class UpstoxBODResolver:
    URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def _download(self) -> list[dict[str, Any]]:
        try:
            response = requests.get(self.URL, timeout=self.timeout)
            response.raise_for_status()
            raw = gzip.decompress(response.content)
            payload = json.loads(raw.decode("utf-8"))
        except (requests.RequestException, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ConfigError(f"Could not download the Upstox NSE instrument file: {exc}") from exc

        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            rows = payload.get("data") or payload.get("instruments") or []
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        raise ConfigError("Upstox NSE instrument file has an unexpected format.")

    @staticmethod
    def _expiry(value: Any) -> str | None:
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            # BOD examples use epoch milliseconds.
            try:
                return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).date().isoformat()
            except (OverflowError, OSError, ValueError):
                return None
        text = str(value)
        if "T" in text:
            return text.split("T", 1)[0]
        return text[:10]

    def find_options(
        self,
        option_type: str,
        expiry: str,
        strike: float | None = None,
        limit: int = 300,
    ) -> list[InstrumentRef]:
        kind = option_type.upper()
        if kind not in {"CE", "PE"}:
            raise ConfigError("Option type must be CE or PE.")

        rows = self._download()
        matches: list[InstrumentRef] = []
        for row in rows:
            if row.get("segment") != "NSE_FO" or row.get("instrument_type") != kind:
                continue
            if str(row.get("underlying_symbol", "")).upper() != "NIFTY":
                continue
            exp = self._expiry(row.get("expiry"))
            if expiry not in {"all", ""} and exp != expiry:
                continue
            try:
                strike_price = float(row["strike_price"])
            except (KeyError, TypeError, ValueError):
                continue
            if strike is not None and strike_price != float(strike):
                continue
            key = str(row.get("instrument_key", "")).strip()
            symbol = str(row.get("trading_symbol", "")).strip()
            if not key or not symbol:
                continue
            lot = row.get("lot_size")
            matches.append(
                InstrumentRef(
                    instrument_key=key,
                    trading_symbol=symbol,
                    instrument_type=kind,
                    strike_price=strike_price,
                    expiry=exp,
                    lot_size=int(lot) if lot is not None else None,
                )
            )

        matches.sort(key=lambda x: (x.expiry or "", x.strike_price or 0))
        return matches[: max(1, int(limit))]

    def expiries(self) -> list[str]:
        rows = self._download()
        values = {
            self._expiry(row.get("expiry"))
            for row in rows
            if row.get("segment") == "NSE_FO"
            and row.get("instrument_type") in {"CE", "PE"}
            and str(row.get("underlying_symbol", "")).upper() == "NIFTY"
        }
        return sorted(v for v in values if v)
