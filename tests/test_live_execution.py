import datetime as dt

import pytest

from algobot.execution_policy import LIVE_TRADING_ENABLED
from algobot.kill_switch import KillSwitch
from algobot.live_execution import ExecutionRequest, LiveExecutionService
from algobot.openalgo_bridge import OpenAlgoError
from algobot.risk import RiskManager


class FakeClient:
    def __init__(self):
        self.orders = []

    @staticmethod
    def execution_enabled():
        return True

    def place_order(self, **kwargs):
        self.orders.append(kwargs)
        return {"orderid": "TEST-1", "status": "success"}


def risk():
    return RiskManager({
        "trading_start": dt.time(9, 15),
        "no_new_entries_after": dt.time(15, 0),
        "max_trades_per_day": 2,
        "max_position_value": 100000,
        "max_daily_loss": 2000,
    })


def request(**overrides):
    data = dict(
        strategy="TradeALGO",
        symbol="NIFTYTEST",
        exchange="NFO",
        action="BUY",
        quantity=50,
        notional=50000,
    )
    data.update(overrides)
    return ExecutionRequest(**data)


def enable_test_execution_policy(monkeypatch):
    """Enable only the module-local gate for unit-testing downstream guards."""
    monkeypatch.setattr("algobot.execution_policy.LIVE_TRADING_ENABLED", True)


def test_live_policy_remains_disabled_by_default():
    assert LIVE_TRADING_ENABLED is False


def test_confirmation_is_required(monkeypatch):
    client = FakeClient()
    service = LiveExecutionService(client, KillSwitch(), risk(), confirm_live=True)
    with pytest.raises(OpenAlgoError, match="confirmation"):
        service.place(request(), now=dt.datetime(2026, 10, 5, 10, 0))
    assert client.orders == []


def test_kill_switch_blocks_order(monkeypatch):
    enable_test_execution_policy(monkeypatch)
    monkeypatch.setenv("TRADEALGO_LIVE_CONFIRM", "I_UNDERSTAND_LIVE_TRADING")
    client = FakeClient()
    switch = KillSwitch()
    switch.halt("manual test")
    service = LiveExecutionService(client, switch, risk(), confirm_live=True)
    with pytest.raises(OpenAlgoError, match="blocked"):
        service.place(request(), now=dt.datetime(2026, 10, 5, 10, 0))
    assert client.orders == []


def test_risk_manager_blocks_new_buy(monkeypatch):
    enable_test_execution_policy(monkeypatch)
    monkeypatch.setenv("TRADEALGO_LIVE_CONFIRM", "I_UNDERSTAND_LIVE_TRADING")
    client = FakeClient()
    cfg = risk()
    cfg.trades_today = 2
    service = LiveExecutionService(client, KillSwitch(), cfg, confirm_live=True)
    with pytest.raises(OpenAlgoError, match="max_trades_per_day"):
        service.place(request(), now=dt.datetime(2026, 10, 5, 10, 0))
    assert client.orders == []


def test_risk_rejects_buy_outside_entry_window(monkeypatch):
    enable_test_execution_policy(monkeypatch)
    monkeypatch.setenv("TRADEALGO_LIVE_CONFIRM", "I_UNDERSTAND_LIVE_TRADING")
    client = FakeClient()
    service = LiveExecutionService(client, KillSwitch(), risk(), confirm_live=True)
    with pytest.raises(OpenAlgoError, match="before_trading_start"):
        service.place(request(), now=dt.datetime(2026, 10, 5, 9, 0))
    assert client.orders == []


def test_sell_exit_is_allowed_after_new_entries_close(monkeypatch):
    enable_test_execution_policy(monkeypatch)
    monkeypatch.setenv("TRADEALGO_LIVE_CONFIRM", "I_UNDERSTAND_LIVE_TRADING")
    client = FakeClient()
    service = LiveExecutionService(client, KillSwitch(), risk(), confirm_live=True)
    result = service.place(
        request(action="SELL", notional=50000),
        now=dt.datetime(2026, 10, 5, 15, 5),
    )
    assert result["orderid"] == "TEST-1"
    assert len(client.orders) == 1


def test_successful_buy_registers_one_entry(monkeypatch):
    enable_test_execution_policy(monkeypatch)
    monkeypatch.setenv("TRADEALGO_LIVE_CONFIRM", "I_UNDERSTAND_LIVE_TRADING")
    client = FakeClient()
    cfg = risk()
    service = LiveExecutionService(client, KillSwitch(), cfg, confirm_live=True)
    service.place(request(), now=dt.datetime(2026, 10, 5, 10, 0))
    assert cfg.trades_today == 1
