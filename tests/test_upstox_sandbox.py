import pytest
from algobot.upstox_sandbox import SANDBOX_HOST, UpstoxSandboxClient, UpstoxSandboxError

TOKEN="sandbox-secret"
class Fake:
    def __init__(self): self.calls=[]
    def __call__(self,url,token,payload,timeout):
        self.calls.append((url,token,payload,timeout))
        return {"status":"success","data":{"order_id":"SBX-123"}}
def client(fake): return UpstoxSandboxClient(token=TOKEN,transport=fake)

def test_place_order_is_pinned_to_sandbox():
    fake=Fake()
    result=client(fake).place_order("NSE_FO|TEST",75,"BUY")
    assert result["data"]["order_id"]=="SBX-123"
    url,token,payload,_=fake.calls[0]
    assert url==f"{SANDBOX_HOST}/v2/order/place" and token==TOKEN
    assert payload["transaction_type"]=="BUY" and payload["quantity"]==75

def test_modify_and_cancel_are_sandbox_only():
    fake=Fake(); c=client(fake)
    c.modify_order("SBX-123",150,order_type="LIMIT",price=12.5)
    c.cancel_order("SBX-123")
    assert [x[0] for x in fake.calls]==[
        f"{SANDBOX_HOST}/v2/order/modify",f"{SANDBOX_HOST}/v2/order/cancel"]

@pytest.mark.parametrize("kwargs,message",[
    ({"instrument_token":"","quantity":1,"transaction_type":"BUY"},"Instrument token"),
    ({"instrument_token":"X","quantity":0,"transaction_type":"BUY"},"Quantity"),
    ({"instrument_token":"X","quantity":1,"transaction_type":"HOLD"},"Transaction type"),
])
def test_bad_orders_are_refused_before_network(kwargs,message):
    fake=Fake()
    with pytest.raises(UpstoxSandboxError,match=message): client(fake).place_order(**kwargs)
    assert fake.calls==[]

def test_missing_token_is_explained():
    with pytest.raises(UpstoxSandboxError,match="UPSTOX_SANDBOX_ACCESS_TOKEN"):
        UpstoxSandboxClient(token="",transport=Fake()).place_order("NSE_FO|TEST",75,"BUY")

def test_no_live_host_exists():
    assert SANDBOX_HOST=="https://sandbox.upstox.com"
    assert "api.upstox.com" not in SANDBOX_HOST
