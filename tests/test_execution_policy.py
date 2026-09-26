import pytest

from algobot.execution_policy import ExecutionMode, get_execution_mode, live_trading_allowed, require_live_enabled


def test_live_trading_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("TRADEALGO_EXECUTION_MODE", raising=False)
    assert live_trading_allowed() is False


def test_live_mode_requires_explicit_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("TRADEALGO_EXECUTION_MODE", "LIVE")
    monkeypatch.setenv("TRADEALGO_KILL_SWITCH_DB", str(tmp_path / "kill.sqlite"))
    assert get_execution_mode() is ExecutionMode.LIVE
    assert live_trading_allowed() is True
    require_live_enabled()


def test_kill_switch_blocks_live_mode(monkeypatch, tmp_path):
    from algobot.kill_switch import KillSwitch

    path = tmp_path / "kill.sqlite"
    switch = KillSwitch(str(path))
    switch.halt("test", by="pytest")
    monkeypatch.setenv("TRADEALGO_EXECUTION_MODE", "LIVE")
    assert live_trading_allowed(switch) is False
    with pytest.raises(RuntimeError, match="blocked"):
        require_live_enabled(switch)
    switch.close_db()


def test_execution_mode_fails_closed(monkeypatch):
    monkeypatch.delenv("TRADEALGO_EXECUTION_MODE", raising=False)
    assert get_execution_mode() == ExecutionMode.LIVE_DISABLED
    monkeypatch.setenv("TRADEALGO_EXECUTION_MODE", "INVALID_MODE")
    assert get_execution_mode() == ExecutionMode.LIVE_DISABLED
    monkeypatch.setenv("TRADEALGO_EXECUTION_MODE", "RESEARCH")
    assert get_execution_mode() == ExecutionMode.RESEARCH
    monkeypatch.setenv("TRADEALGO_EXECUTION_MODE", "PAPER")
    assert get_execution_mode() == ExecutionMode.PAPER
