from algobot.execution_policy import LIVE_TRADING_ENABLED, live_trading_allowed, require_live_disabled


def test_live_trading_is_hard_disabled():
    assert LIVE_TRADING_ENABLED is False
    assert live_trading_allowed() is False
    require_live_disabled()
