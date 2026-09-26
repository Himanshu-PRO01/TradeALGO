from algobot.auto_tester import (
    build_candidate_grid,
    build_period_values,
    estimate_candidate_count,
    make_candidate,
)


def test_period_range_is_validated_and_built():
    assert build_period_values(5, 15, 5) == [5, 10, 15]


def test_period_range_rejects_reversed_bounds():
    try:
        build_period_values(20, 10, 5)
    except ValueError as exc:
        assert "less than or equal" in str(exc)
    else:
        raise AssertionError("Expected reversed period bounds to fail")


def test_empty_indicator_selection_has_one_period_combination():
    candidates = build_candidate_grid([5, 10, 15], [], [0.5, 1.0], [1.0], 20, None, None)
    assert candidates == [((), 0.5, 1.0), ((), 1.0, 1.0)]


def test_candidate_grid_is_capped_deterministically():
    candidates = build_candidate_grid(
        [5, 10, 15], ["fast", "slow"], [0.5, 1.0], [1.0, 2.0], 5, None, None
    )
    assert len(candidates) == 5
    assert candidates[0] == ((5, 5), 0.5, 1.0)
    assert candidates[-1] == ((5, 15), 0.5, 1.0)


def test_estimate_does_not_fake_period_dimension_when_none_selected():
    assert estimate_candidate_count([5, 10, 15], 0, 2, 2) == 4


def test_make_candidate_does_not_mutate_base_config():
    base = {
        "name": "base", "capital": 100000, "data": {"path": None},
        "strategy": {
            "name": "sma_crossover",
            "params": {"indicators": [{"name": "fast", "period": 10}]},
            "quantity": 1, "allow_short": False, "stop_loss_pct": 1.0, "target_pct": 2.0,
        },
        "risk": {
            "max_daily_loss": None, "max_trades_per_day": None, "max_position_value": None,
            "trading_start": "09:15", "no_new_entries_after": "15:00", "square_off_time": "15:15",
        },
        "costs": {
            "brokerage_pct": 0, "brokerage_cap": 20, "brokerage_flat": None,
            "stt_buy_pct": 0, "stt_sell_pct": 0, "exchange_txn_pct": 0,
            "sebi_fee_pct": 0, "stamp_buy_pct": 0, "gst_pct": 0, "slippage_bps": 0,
        },
    }
    candidate = make_candidate(base, ["fast"], [20], 0.5, 1.5, 7)
    assert candidate["name"] == "auto_7"
    assert candidate["strategy"]["params"]["indicators"][0]["period"] == 20
    assert candidate["strategy"]["stop_loss_pct"] == 0.5
    assert base["strategy"]["params"]["indicators"][0]["period"] == 10
