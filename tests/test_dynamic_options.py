import pandas as pd

from algobot.dynamic_options import (
    generate_synthetic_option_chain,
    run_dynamic_strike_option_backtest,
)


def _bars():
    idx = pd.date_range("2025-01-06 09:15", periods=7, freq="5min")
    close = [24500, 24500, 24560, 24570, 24540, 24520, 24520]
    df = pd.DataFrame(
        {
            "open": close,
            "high": [x + 10 for x in close],
            "low": [x - 10 for x in close],
            "close": close,
        },
        index=idx,
    )
    df.index.name = "datetime"
    return df


def test_synthetic_chain_contains_both_ce_and_pe_contracts():
    df = generate_synthetic_option_chain(_bars(), strike_step=50, strikes_each_side=2)
    assert "CE_24500_open" in df.columns
    assert "CE_24500_close" in df.columns
    assert "PE_24500_open" in df.columns
    assert "PE_24500_close" in df.columns


def test_dynamic_ce_rolls_up_when_underlying_crosses_upper_trigger():
    df = generate_synthetic_option_chain(_bars(), strike_step=50, strikes_each_side=3)
    trades, events = run_dynamic_strike_option_backtest(
        df,
        contract_type="CE",
        quantity=1,
        strike_mode="ATM",
        strike_step=50,
        upper_trigger=50,
        lower_trigger=45,
        entry_time="09:20",
        exit_time="09:35",
        dynamic_strike=True,
    )
    assert len(trades) == 2
    assert trades.iloc[0]["contract"] == "CE 24500"
    assert trades.iloc[0]["exit_reason"] == "strike_roll"
    assert trades.iloc[1]["contract"] == "CE 24550"
    assert trades.iloc[1]["exit_reason"] == "time_exit"
    assert any("CE 24500 -> CE 24550" in event for event in events)


def test_dynamic_pe_can_be_selected_without_using_ce_contracts():
    df = generate_synthetic_option_chain(_bars(), strike_step=50, strikes_each_side=3)
    trades, _ = run_dynamic_strike_option_backtest(
        df,
        contract_type="PE",
        quantity=2,
        strike_mode="FIXED",
        initial_strike=24500,
        strike_step=50,
        upper_trigger=1000,
        lower_trigger=1000,
        entry_time="09:20",
        exit_time="09:35",
        dynamic_strike=False,
    )
    assert not trades.empty
    assert set(trades["contract"]) == {"PE 24500"}
    assert set(trades["qty"]) == {2}


def test_long_format_option_csv_is_normalized_into_wide_contracts(tmp_path):
    from algobot.dynamic_options import load_option_chain_csv

    rows = []
    idx = pd.date_range("2025-01-06 09:15", periods=3, freq="5min")
    for i, ts in enumerate(idx):
        spot = 24500 + i * 25
        for kind, premium in [("CE", 120 + i * 5), ("PE", 130 - i * 4)]:
            rows.append(
                {
                    "datetime": ts,
                    "strike": 24500,
                    "option_type": kind,
                    "open": premium,
                    "high": premium + 2,
                    "low": premium - 2,
                    "close": premium + 1,
                }
            )
    path = tmp_path / "long_chain.csv"
    frame = pd.DataFrame(rows)
    frame["underlying_open"] = [24500] * len(frame)
    frame["underlying_high"] = [24510] * len(frame)
    frame["underlying_low"] = [24490] * len(frame)
    frame["underlying_close"] = [24500 + i * 25 for i in range(3) for _ in range(2)]
    frame = frame.rename(
        columns={
            "underlying_open": "open_underlying",
            "underlying_high": "high_underlying",
            "underlying_low": "low_underlying",
            "underlying_close": "close_underlying",
        }
    )
    # The loader expects the standard underlying OHLC names alongside option rows.
    frame["open"] = [120, 130, 125, 126, 130, 122]
    frame["high"] = frame["open"] + 2
    frame["low"] = frame["open"] - 2
    frame["close"] = frame["open"] + 1
    frame.to_csv(path, index=False)

    loaded = load_option_chain_csv(path)
    assert "CE_24500_open" in loaded.columns
    assert "PE_24500_close" in loaded.columns
    assert len(loaded) == 3
