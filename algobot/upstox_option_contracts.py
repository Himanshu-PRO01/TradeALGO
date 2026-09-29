"""Automatic Upstox NIFTY option-contract discovery.

Read-only helper: resolves current option contracts to Upstox instrument keys.
It never places or modifies orders.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import requests

from .config import ConfigError


@dataclass(frozen=True)
class OptionContractRef:
    instrument_key: str
    trading_symbol: str
    strike_price: float
    instrument_type: str
    expiry: str
    lot_size: int | None = None
    weekly: bool | None = None


class UpstoxOptionContracts:
    URL = "https://api.upstox.com/v2/option/contract"

    def __init__(self, access_token: str, underlying_key: str = "NSE_INDEX|Nifty 50", timeout: float = 10.0):
        token = access_token.strip()
        if not token:
            raise ConfigError("Upstox access token is empty.")
        self.access_token = token
        self.underlying_key = underlying_key.strip()
        self.timeout = float(timeout)
        if not self.underlying_key:
            raise ConfigError("Underlying instrument key is required.")

    def fetch(self, expiry_date: str | None = "current_week") -> list[OptionContractRef]:
        params = {"instrument_key": self.underlying_key}
        if expiry_date:
            params["expiry_date"] = expiry_date
        try:
            response = requests.get(
                self.URL,
                params=params,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.access_token}",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload: Any = response.json()
        except requests.RequestException as exc:
            raise ConfigError(f"Upstox option-contract lookup failed: {exc}") from exc
        except ValueError as exc:
            raise ConfigError("Upstox option-contract lookup returned invalid JSON.") from exc

        rows = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            raise ConfigError("Upstox option-contract response has an unexpected format.")

        contracts: list[OptionContractRef] = []
        for row in rows:
            if not isinstance(row, dict) or row.get("instrument_type") not in {"CE", "PE"}:
                continue
            try:
                contracts.append(
                    OptionContractRef(
                        instrument_key=str(row["instrument_key"]),
                        trading_symbol=str(row.get("trading_symbol", "")),
                        strike_price=float(row["strike_price"]),
                        instrument_type=str(row["instrument_type"]),
                        expiry=str(row["expiry"]),
                        lot_size=int(row["lot_size"]) if row.get("lot_size") is not None else None,
                        weekly=bool(row["weekly"]) if row.get("weekly") is not None else None,
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue

        if not contracts:
            raise ConfigError("No CE/PE option contracts were returned by Upstox.")
        return sorted(contracts, key=lambda c: (c.expiry, c.strike_price, c.instrument_type))

    def strikes(self, contracts: list[OptionContractRef], option_type: str) -> list[float]:
        kind = option_type.upper()
        return sorted({c.strike_price for c in contracts if c.instrument_type == kind})

    def by_strike(self, contracts: list[OptionContractRef], option_type: str) -> dict[float, OptionContractRef]:
        kind = option_type.upper()
        return {
            c.strike_price: c
            for c in contracts
            if c.instrument_type == kind
        }

    @staticmethod
    def nearest_strike(strikes: list[float], target: float) -> float:
        if not strikes:
            raise ConfigError("No strikes are available.")
        return min(strikes, key=lambda strike: (abs(strike - target), strike))
