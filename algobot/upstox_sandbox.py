"""Sandbox-only Upstox API client.

Pinned to Upstox's sandbox host. No live host or live-token switch exists.
Keep UPSTOX_SANDBOX_ACCESS_TOKEN in a private environment/Streamlit secret.
"""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request
from typing import Callable, Optional

SANDBOX_HOST = "https://sandbox.upstox.com"
SANDBOX_TOKEN_ENV = "UPSTOX_SANDBOX_ACCESS_TOKEN"

class UpstoxSandboxError(RuntimeError):
    """A sandbox request failed or configuration is incomplete."""

def sandbox_token() -> Optional[str]:
    token = os.environ.get(SANDBOX_TOKEN_ENV)
    return token.strip() if token else None

def _post(path: str, token: str, payload: dict, timeout: float = 20.0,
          transport: Optional[Callable] = None) -> dict:
    if not token:
        raise UpstoxSandboxError(
            f"No sandbox token found. Set {SANDBOX_TOKEN_ENV} in a private environment/secret."
        )
    url = f"{SANDBOX_HOST}{path}"
    if transport is not None:
        return transport(url, token, payload, timeout)
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Accept":"application/json","Content-Type":"application/json",
                 "Authorization":f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw=response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try: detail=json.loads(exc.read().decode("utf-8"))
        except Exception: detail={"message":str(exc.reason)}
        raise UpstoxSandboxError(f"Upstox Sandbox returned HTTP {exc.code}: {detail.get('message') or detail}")
    except urllib.error.URLError as exc:
        raise UpstoxSandboxError(f"Could not reach Upstox Sandbox: {exc.reason}")
    except TimeoutError:
        raise UpstoxSandboxError("Upstox Sandbox did not answer in time.")
    try: data=json.loads(raw)
    except json.JSONDecodeError:
        raise UpstoxSandboxError("Upstox Sandbox returned a non-JSON response.")
    if not isinstance(data, dict):
        raise UpstoxSandboxError("Upstox Sandbox returned an unexpected response.")
    if data.get("status") not in (None, "success"):
        raise UpstoxSandboxError(f"Upstox Sandbox reported an error: {data.get('message') or data}")
    return data

class UpstoxSandboxClient:
    """Order client permanently pinned to Upstox's sandbox environment."""
    def __init__(self, token: Optional[str] = None, transport: Optional[Callable] = None,
                 timeout: float = 20.0):
        self.token=token or sandbox_token()
        self.transport=transport
        self.timeout=timeout

    def place_order(self, instrument_token: str, quantity: int, transaction_type: str,
                    order_type: str="MARKET", product: str="D", validity: str="DAY",
                    price: float=0, trigger_price: float=0, disclosed_quantity: int=0) -> dict:
        if not instrument_token.strip(): raise UpstoxSandboxError("Instrument token is required.")
        if int(quantity)<=0: raise UpstoxSandboxError("Quantity must be greater than zero.")
        transaction_type=transaction_type.upper()
        if transaction_type not in {"BUY","SELL"}: raise UpstoxSandboxError("Transaction type must be BUY or SELL.")
        order_type=order_type.upper()
        if order_type not in {"MARKET","LIMIT","SL","SL-M"}: raise UpstoxSandboxError("Unsupported order type.")
        if int(disclosed_quantity)<0: raise UpstoxSandboxError("Disclosed quantity cannot be negative.")
        payload={"quantity":int(quantity),"product":product,"validity":validity,"price":float(price),
                 "instrument_token":instrument_token.strip(),"order_type":order_type,
                 "transaction_type":transaction_type,"disclosed_quantity":int(disclosed_quantity),
                 "trigger_price":float(trigger_price)}
        return _post("/v2/order/place",self.token or "",payload,self.timeout,self.transport)

    def modify_order(self, order_id: str, quantity: int, price: float=0,
                     order_type: str="MARKET", trigger_price: float=0,
                     validity: str="DAY", disclosed_quantity: int=0) -> dict:
        if not order_id.strip(): raise UpstoxSandboxError("Order ID is required.")
        if int(quantity)<=0: raise UpstoxSandboxError("Quantity must be greater than zero.")
        payload={"quantity":int(quantity),"validity":validity,"price":float(price),
                 "order_id":order_id.strip(),"order_type":order_type.upper(),
                 "disclosed_quantity":int(disclosed_quantity),"trigger_price":float(trigger_price)}
        return _post("/v2/order/modify",self.token or "",payload,self.timeout,self.transport)

    def cancel_order(self, order_id: str) -> dict:
        if not order_id.strip(): raise UpstoxSandboxError("Order ID is required.")
        return _post("/v2/order/cancel",self.token or "",{"order_id":order_id.strip()},
                     self.timeout,self.transport)
