from algobot.config import validate_config
from algobot.agent_simulation import AgentProfile, simulate_agents


def cfg():
    return validate_config({
        "name": "agent-demo",
        "capital": 100000,
        "data": {"path": ""},
        "strategy": {"name": "rules", "params": {
            "indicators": [{"name": "ema_fast", "type": "ema", "period": 9},
                           {"name": "ema_slow", "type": "ema", "period": 21}],
            "entry_long": "ema_fast > ema_slow",
            "exit_long": "ema_fast < ema_slow",
            "entry_short": "ema_fast < ema_slow",
            "exit_short": "ema_fast > ema_slow"},
            "quantity": 1, "allow_short": True, "stop_loss_pct": 1.0, "target_pct": 2.0},
        "risk": {"max_daily_loss": 3000, "max_trades_per_day": 4,
                 "max_position_value": 100000, "trading_start": "09:20",
                 "no_new_entries_after": "14:45", "square_off_time": "15:15"},
        "costs": {"brokerage_pct": 0.03, "brokerage_cap": 20, "stt_sell_pct": 0.025,
                  "exchange_txn_pct": 0.003, "sebi_fee_pct": 0.0001,
                  "stamp_buy_pct": 0.003, "gst_pct": 18, "slippage_bps": 2},
    })


def test_agent_simulation_is_bounded_and_reproducible():
    profiles = (AgentProfile("test", .5, 1.0, 1.0),)
    a = simulate_agents(cfg(), worlds=1, days=2, profiles=profiles)
    b = simulate_agents(cfg(), worlds=1, days=2, profiles=profiles)
    assert a == b
    assert len(a.agents) == 7
    assert a.worlds_tested == 7


def test_agent_simulation_rejects_invalid_bounds():
    try:
        simulate_agents(cfg(), worlds=0)
    except ValueError as exc:
        assert "at least 1" in str(exc)
    else:
        raise AssertionError("expected ValueError")
