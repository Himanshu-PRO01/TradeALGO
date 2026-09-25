"""Sandbox-only Upstox API client.

Uses Upstox's official Python SDK in explicit sandbox mode. There is no live
host/token switch in this module.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Callable, Optional

SANDBOX_HOST = "https://api-sandbox.upstox.com"
SANDBOX_TOKEN_ENV = "UPSTOX_SANDBOX_ACCESS_TOKEN"


class UpstoxSandboxError(RuntimeError):
    """A sandbox request failed or configuration is incomplete."""


def clean_token(raw: Optional[str]) -> Optional[str]:
    """Normalize a pasted token: strip whitespace/newlines, surrounding
    quotes, and an accidentally-included 'Bearer ' prefix.

    Streamlit secrets are pasted by hand, and every one of these mistakes
    produces a token that *looks* present (so the UI shows "detected") but
    still gets a 401 from Upstox because the literal string sent no longer
    matches the token they generated.
    """
    if raw is None:
        return None
    token = str(raw).strip()
    # Strip a matching pair of surrounding quotes, e.g. token = '"eyJ..."'
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
        token = token[1:-1].strip()
    # Strip an accidentally pasted "Bearer " prefix (case-insensitive).
    if token[:7].lower() == "bearer ":
        token = token[7:].strip()
    return token or None


def token_preview(token: Optional[str]) -> str:
    """A safe-to-display preview: length plus first/last few characters.

    Never returns enough of the token to reconstruct it, but is enough for
    a human to eyeball that it matches the token shown on the Upstox
    sandbox app page (right length, right prefix) and has no stray
    whitespace/quotes baked in.
    """
    if not token:
        return "(none)"
    if len(token) <= 8:
        return f"{len(token)} chars"
    return f"{token[:4]}…{token[-4:]} ({len(token)} chars)"


def sandbox_token() -> Optional[str]:
    return clean_token(os.environ.get(SANDBOX_TOKEN_ENV))


def _post(path: str, token: str, payload: dict, timeout: float = 20.0,
          transport: Optional[Callable] = None) -> dict:
    """Legacy transport used only by unit tests; production uses the SDK."""
    if not token:
        raise UpstoxSandboxError(
            f"No sandbox token found. Set {SANDBOX_TOKEN_ENV} in a private environment/secret."
        )
    url = f"{SANDBOX_HOST}{path}"
    if transport is not None:
        return transport(url, token, payload, timeout)
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
        except Exception:
            detail = {"message": str(exc.reason)}
        raise UpstoxSandboxError(
            f"Upstox Sandbox returned HTTP {exc.code}: "
            f"{detail.get('message') or detail}"
        )
    except urllib.error.URLError as exc:
        raise UpstoxSandboxError(f"Could not reach Upstox Sandbox: {exc.reason}")
    except TimeoutError:
        raise UpstoxSandboxError("Upstox Sandbox did not answer in time.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise UpstoxSandboxError("Upstox Sandbox returned a non-JSON response.")
    if not isinstance(data, dict):
        raise UpstoxSandboxError("Upstox Sandbox returned an unexpected response.")
    if data.get("status") not in (None, "success"):
        raise UpstoxSandboxError(
            f"Upstox Sandbox reported an error: {data.get('message') or data}"
        )
    return data


def _sdk_response_to_dict(response) -> dict:
    if hasattr(response, "to_dict"):
        data = response.to_dict()
    elif isinstance(response, dict):
        data = response
    else:
        data = {"response": str(response)}
    if not isinstance(data, dict):
        raise UpstoxSandboxError("Upstox Sandbox returned an unexpected response.")
    return data


def _sdk_order_api(token: str):
    """Create an Upstox OrderApi explicitly configured for sandbox mode."""
    if not token:
        raise UpstoxSandboxError(
            f"No sandbox token found. Set {SANDBOX_TOKEN_ENV} in a private environment/secret."
        )
    try:
        import upstox_client
    except ImportError as exc:
        raise UpstoxSandboxError(
            "Upstox SDK is not installed. Redeploy after adding "
            "upstox-python-sdk to requirements.txt."
        ) from exc
    try:
        configuration = upstox_client.Configuration(sandbox=True)
        configuration.access_token = token
        api_client = upstox_client.ApiClient(configuration)
        return upstox_client.OrderApiV3(api_client), upstox_client
    except Exception as exc:
        raise UpstoxSandboxError(
            f"Could not initialize the Upstox Sandbox SDK: {exc}"
        ) from exc


def _sdk_error(exc: Exception) -> UpstoxSandboxError:
    status = getattr(exc, "status", None)
    reason = getattr(exc, "reason", None)
    if status:
        detail = reason or getattr(exc, "body", None) or str(exc)
        return UpstoxSandboxError(
            f"Upstox Sandbox returned HTTP {status}: {detail}"
        )
    if isinstance(exc, TimeoutError):
        return UpstoxSandboxError("Upstox Sandbox did not answer in time.")
    if isinstance(exc, OSError):
        return UpstoxSandboxError(f"Could not reach Upstox Sandbox: {exc}")
    return UpstoxSandboxError(f"Upstox Sandbox request failed: {exc}")


class UpstoxSandboxClient:
    """Order client permanently configured for Upstox Sandbox mode."""

    def __init__(self, token: Optional[str] = None,
                 transport: Optional[Callable] = None,
                 timeout: float = 20.0):
        self.token = token or sandbox_token()
        self.transport = transport
        self.timeout = timeout

    def _validate_order(self, instrument_token: str, quantity: int,
                        transaction_type: str, order_type: str,
                        product: str, validity: str, price: float,
                        trigger_price: float,
                        disclosed_quantity: int) -> tuple:
        if not instrument_token.strip():
            raise UpstoxSandboxError("Instrument token is required.")
        if int(quantity) <= 0:
            raise UpstoxSandboxError("Quantity must be greater than zero.")
        transaction_type = transaction_type.upper()
        if transaction_type not in {"BUY", "SELL"}:
            raise UpstoxSandboxError("Transaction type must be BUY or SELL.")
        order_type = order_type.upper()
        if order_type not in {"MARKET", "LIMIT", "SL", "SL-M"}:
            raise UpstoxSandboxError("Unsupported order type.")
        if int(disclosed_quantity) < 0:
            raise UpstoxSandboxError("Disclosed quantity cannot be negative.")
        if int(disclosed_quantity) > int(quantity):
            raise UpstoxSandboxError("Disclosed quantity cannot exceed quantity.")
        product = product.upper()
        if product not in {"I", "D", "MTF"}:
            raise UpstoxSandboxError("Product must be I, D, or MTF.")
        validity = validity.upper()
        if validity not in {"DAY", "IOC"}:
            raise UpstoxSandboxError("Validity must be DAY or IOC.")
        if order_type == "LIMIT" and float(price) <= 0:
            raise UpstoxSandboxError("Limit price must be greater than zero.")
        if order_type in {"SL", "SL-M"} and float(trigger_price) <= 0:
            raise UpstoxSandboxError(
                "Trigger price must be greater than zero for stop orders."
            )
        return (transaction_type, order_type, product, validity, float(price),
                float(trigger_price), int(disclosed_quantity))

    def place_order(self, instrument_token: str, quantity: int,
                    transaction_type: str, order_type: str = "MARKET",
                    product: str = "D", validity: str = "DAY",
                    price: float = 0, trigger_price: float = 0,
                    disclosed_quantity: int = 0) -> dict:
        (transaction_type, order_type, product, validity, price,
         trigger_price, disclosed_quantity) = self._validate_order(
            instrument_token, quantity, transaction_type, order_type, product,
            validity, price, trigger_price, disclosed_quantity)

        payload = {
            "quantity": int(quantity), "product": product, "validity": validity,
            "price": price, "instrument_token": instrument_token.strip(),
            "order_type": order_type, "transaction_type": transaction_type,
            "disclosed_quantity": disclosed_quantity,
            "trigger_price": trigger_price,
        }
        if self.transport is not None:
            return _post("/v2/order/place", self.token or "", payload,
                         self.timeout, self.transport)

        api, sdk = _sdk_order_api(self.token or "")
        try:
            body = sdk.PlaceOrderV3Request(
                quantity=int(quantity), product=product, validity=validity,
                price=price, instrument_token=instrument_token.strip(),
                order_type=order_type, transaction_type=transaction_type,
                disclosed_quantity=disclosed_quantity,
                trigger_price=trigger_price, is_amo=False,
            )
            response = api.place_order(body)
            return _sdk_response_to_dict(response)
        except Exception as exc:
            raise _sdk_error(exc) from exc

    def modify_order(self, order_id: str, quantity: int, price: float = 0,
                     order_type: str = "MARKET", trigger_price: float = 0,
                     validity: str = "DAY",
                     disclosed_quantity: int = 0) -> dict:
        if not order_id.strip():
            raise UpstoxSandboxError("Order ID is required.")
        if int(quantity) <= 0:
            raise UpstoxSandboxError("Quantity must be greater than zero.")
        if int(disclosed_quantity) < 0:
            raise UpstoxSandboxError("Disclosed quantity cannot be negative.")
        if int(disclosed_quantity) > int(quantity):
            raise UpstoxSandboxError("Disclosed quantity cannot exceed quantity.")
        order_type = order_type.upper()
        validity = validity.upper()
        if order_type not in {"MARKET", "LIMIT", "SL", "SL-M"}:
            raise UpstoxSandboxError("Unsupported order type.")
        if validity not in {"DAY", "IOC"}:
            raise UpstoxSandboxError("Validity must be DAY or IOC.")
        if order_type == "LIMIT" and float(price) <= 0:
            raise UpstoxSandboxError("Limit price must be greater than zero.")
        if order_type in {"SL", "SL-M"} and float(trigger_price) <= 0:
            raise UpstoxSandboxError(
                "Trigger price must be greater than zero for stop orders."
            )

        if self.transport is not None:
            payload = {
                "quantity": int(quantity), "validity": validity,
                "price": float(price), "order_id": order_id.strip(),
                "order_type": order_type,
                "disclosed_quantity": int(disclosed_quantity),
                "trigger_price": float(trigger_price),
            }
            return _post("/v2/order/modify", self.token or "", payload,
                         self.timeout, self.transport)

        api, sdk = _sdk_order_api(self.token or "")
        try:
            body = sdk.ModifyOrderRequest(
                quantity=int(quantity), validity=validity, price=float(price),
                order_id=order_id.strip(), order_type=order_type,
                disclosed_quantity=int(disclosed_quantity),
                trigger_price=float(trigger_price),
            )
            response = api.modify_order(body)
            return _sdk_response_to_dict(response)
        except Exception as exc:
            raise _sdk_error(exc) from exc

    def cancel_order(self, order_id: str) -> dict:
        if not order_id.strip():
            raise UpstoxSandboxError("Order ID is required.")
        if self.transport is not None:
            return _post("/v2/order/cancel", self.token or "",
                         {"order_id": order_id.strip()}, self.timeout,
                         self.transport)
        api, _ = _sdk_order_api(self.token or "")
        try:
            response = api.cancel_order(order_id.strip())
            return _sdk_response_to_dict(response)
        except Exception as exc:
            raise _sdk_error(exc) from exc
