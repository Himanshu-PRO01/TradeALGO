from datetime import datetime, timezone
from algobot.india_market import IndiaCostModel, is_regular_session


def test_india_session_uses_ist():
    assert is_regular_session(datetime(2026, 10, 5, 9, 30, tzinfo=timezone.utc)) is True
    assert is_regular_session(datetime(2026, 10, 5, 4, 0, tzinfo=timezone.utc)) is False


def test_india_cost_model_is_positive():
    assert IndiaCostModel().estimate_round_trip(100000, 101000) > 0
