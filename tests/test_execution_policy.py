from algobot.execution_policy import ExecutionMode, get_execution_mode, live_trading_allowed, require_live_disabled
import os
import pytest

def test_live_trading_is_hard_disabled():
    assert live_trading_allowed() is False
    require_live_disabled()

def test_execution_mode_fails_closed(monkeypatch):
    monkeypatch.delenv("TRADEALGO_EXECUTION_MODE", raising=False)
    assert get_execution_mode() == ExecutionMode.LIVE_DISABLED
    
    monkeypatch.setenv("TRADEALGO_EXECUTION_MODE", "INVALID_MODE")
    assert get_execution_mode() == ExecutionMode.LIVE_DISABLED
    
    monkeypatch.setenv("TRADEALGO_EXECUTION_MODE", "RESEARCH")
    assert get_execution_mode() == ExecutionMode.RESEARCH

    monkeypatch.setenv("TRADEALGO_EXECUTION_MODE", "PAPER")
    assert get_execution_mode() == ExecutionMode.PAPER
