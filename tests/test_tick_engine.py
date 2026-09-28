import pandas as pd

from algobot.tick_engine import run_tick_strategy


def _ticks():
    idx = pd.to_datetime([
        "2025-01-06 09:20:00.000",
        "2025-01-06 09:20:00.100",
        "2025-01-06 09:20:00.200",
        "2025-01-06 09:20:00.300",
        "2025-01-06 09:21:00.000",
    ])
    df = pd.DataFrame(
        {
            "last_price": [24500, 24501, 24551, 24560, 24560],
            "CE_24500_last_price": [100, 101, 110, 111, 112],
            "CE_24550_last_price": [80, 81, 82, 90, 92],
            "PE_24500_last_price": [100, 99, 98, 97, 96],
        },
        index=idx,
    )
    return df


def test_tick_trigger_rolls_without_waiting_for_candle_close():
    trades, events = run_tick_strategy(
        _ticks(),
        contract_type="CE",
        entry_time="09:20",
        exit_time="09:21",
        strike_step=50,
        upper_trigger=50,
        lower_trigger=45,
    )
    assert len(trades) == 2
    assert trades.iloc[0]["contract"] == "CE 24500"
    assert trades.iloc[1]["contract"] == "CE 24550"
    assert trades.iloc[0]["exit_reason"] == "tick_strike_roll"
    assert any("CE 24500 -> CE 24550" in e for e in events)


def test_tick_engine_selects_pe_independently():
    trades, _ = run_tick_strategy(
        _ticks(),
        contract_type="PE",
        strike_mode="FIXED",
        initial_strike=24500,
        dynamic_strike=False,
        entry_time="09:20",
        exit_time="09:21",
    )
    assert not trades.empty
    assert set(trades["contract"]) == {"PE 24500"}
