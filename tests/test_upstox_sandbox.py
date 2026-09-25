import sys
from types import SimpleNamespace

import pytest

from algobot.upstox_sandbox import (
    SANDBOX_API_VERSION,
    SANDBOX_HOST,
    UpstoxSandboxClient,
    UpstoxSandboxError,
    _sdk_order_api,
)


TOKEN = "sandbox-secret"


class Fake:
    def __init__(self):
        self.calls = []

    def __call__(self, url, token, payload, timeout):
        self.calls.append((url, token, payload, timeout))
        return {"status": "success", "data": {"order_id": "SBX-123"}}


def client(fake):
    return UpstoxSandboxClient(token=TOKEN, transport=fake)


def test_place_order_is_pinned_to_sandbox():
    fake = Fake()
    result = client(fake).place_order("NSE_FO|TEST", 75, "BUY")
    assert result["data"]["order_id"] == "SBX-123"
    url, token, payload, _ = fake.calls[0]
    assert url == f"{SANDBOX_HOST}/v2/order/place"
    assert token == TOKEN
    assert payload["transaction_type"] == "BUY"
    assert payload["quantity"] == 75


def test_modify_and_cancel_are_sandbox_only():
    fake = Fake()
    c = client(fake)
    c.modify_order("SBX-123", 150, order_type="LIMIT", price=12.5)
    c.cancel_order("SBX-123")
    assert [x[0] for x in fake.calls] == [
        f"{SANDBOX_HOST}/v2/order/modify",
        f"{SANDBOX_HOST}/v2/order/cancel",
    ]


@pytest.mark.parametrize(
    "kwargs,message",
    [
        (
            {"instrument_token": "", "quantity": 1, "transaction_type": "BUY"},
            "Instrument token",
        ),
        (
            {"instrument_token": "X", "quantity": 0, "transaction_type": "BUY"},
            "Quantity",
        ),
        (
            {"instrument_token": "X", "quantity": 1, "transaction_type": "HOLD"},
            "Transaction type",
        ),
    ],
)
def test_bad_orders_are_refused_before_network(kwargs, message):
    fake = Fake()
    with pytest.raises(UpstoxSandboxError, match=message):
        client(fake).place_order(**kwargs)
    assert fake.calls == []


def test_missing_token_is_explained():
    with pytest.raises(
        UpstoxSandboxError, match="UPSTOX_SANDBOX_ACCESS_TOKEN"
    ):
        UpstoxSandboxClient(token="", transport=Fake()).place_order(
            "NSE_FO|TEST", 75, "BUY"
        )


def test_sandbox_host_matches_official_sdk_sandbox_host():
    assert SANDBOX_HOST == "https://api-sandbox.upstox.com"
    assert "api.upstox.com" not in SANDBOX_HOST
    assert "api-hft.upstox.com" not in SANDBOX_HOST


def test_sdk_client_is_explicitly_sandbox_only(monkeypatch):
    class FakeConfiguration:
        def __init__(self, sandbox=False):
            self.sandbox = sandbox
            self.access_token = ""

    class FakeApiClient:
        def __init__(self, configuration):
            self.configuration = configuration

    class FakeOrderApi:
        def __init__(self, api_client):
            self.api_client = api_client

    fake_sdk = SimpleNamespace(
        Configuration=FakeConfiguration,
        ApiClient=FakeApiClient,
        OrderApi=FakeOrderApi,
    )
    monkeypatch.setitem(sys.modules, "upstox_client", fake_sdk)

    api, sdk = _sdk_order_api(TOKEN)

    assert sdk is fake_sdk
    assert api.api_client.configuration.sandbox is True
    assert api.api_client.configuration.access_token == TOKEN


def test_order_validation_rejects_invalid_price_and_disclosed_quantity():
    fake = Fake()
    with pytest.raises(UpstoxSandboxError, match="Limit price"):
        client(fake).place_order(
            "NSE_FO|TEST", 75, "BUY", order_type="LIMIT", price=0
        )
    with pytest.raises(UpstoxSandboxError, match="Disclosed quantity"):
        client(fake).place_order(
            "NSE_FO|TEST", 75, "BUY", disclosed_quantity=76
        )
    assert fake.calls == []


def test_sdk_uses_v2_api_version_header():
    assert SANDBOX_API_VERSION == "2.0"
