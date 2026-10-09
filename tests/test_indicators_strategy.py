import numpy as np
import pandas as pd
import pytest

from algobot.config import ConfigError
from algobot.data import generate_sample_data
from algobot.indicators import add_indicators, add_prev_columns, cci, hma, mfi, rsi, sma, wma
from algobot.strategy import RuleStrategy, SmaCrossover, build_strategy, evaluate_rule
from helpers import make_bars, make_cfg

SPECS = [
    {"name": "s5", "type": "sma", "period": 5},
    {"name": "e8", "type": "ema", "period": 8},
    {"name": "r6", "type": "rsi", "period": 6},
    {"name": "a5", "type": "atr", "period": 5},
    {"name": "hi4", "type": "highest", "period": 4},
    {"name": "lo4", "type": "lowest", "period": 4},
    {"name": "vw", "type": "vwap"},
    {"name": "w5", "type": "wma", "period": 5},
    {"name": "h9", "type": "hma", "period": 9},
    {"name": "mf7", "type": "mfi", "period": 7},
    {"name": "c5", "type": "cci", "period": 5},
]


def test_sma_matches_hand_calculation():
    s = pd.Series([1.0, 2, 3, 4, 5])
    assert sma(s, 3).tolist()[2:] == [2.0, 3.0, 4.0]


def test_rsi_is_100_when_price_only_rises_and_stays_in_range():
    up = pd.Series(np.arange(1.0, 40.0))
    assert rsi(up, 14).dropna().eq(100.0).all()
    df = generate_sample_data(days=3)
    r = rsi(df["close"], 14).dropna()
    assert ((r >= 0) & (r <= 100)).all()


def test_wma_weights_recent_bars_more_than_old_ones():
    s = pd.Series([1.0, 1.0, 1.0, 1.0, 10.0])   # a spike on the most recent bar
    plain_average = s.tail(5).mean()
    weighted = wma(s, 5).iloc[-1]
    assert weighted > plain_average   # the recent spike should count for more


def test_hma_tracks_price_more_closely_than_a_plain_moving_average():
    """The classic HMA selling point: less lag than an SMA/WMA of the same length.
    (It can briefly overshoot the new level right after a sharp step -- see hma()'s
    own docstring -- so this checks how SOON each one gets near the new price,
    not the error at one arbitrarily chosen bar, which could land inside that
    overshoot and give a misleading answer.)"""
    s = pd.Series(np.concatenate([np.full(40, 100.0), np.full(40, 120.0)]))  # one step up
    h, w = hma(s, 10), wma(s, 10)
    # Average error over the first 10 bars right after the step: HMA's overshoot
    # wobble still nets out to catching up faster than a plain WMA does.
    window = slice(40, 50)
    assert (120.0 - h[window]).abs().mean() < (120.0 - w[window]).abs().mean()


def test_mfi_is_high_when_rising_price_is_backed_by_volume_and_bounded_0_to_100():
    df = generate_sample_data(days=4, seed=2)
    f = mfi(df, 14).dropna()
    assert ((f >= 0) & (f <= 100)).all()
    # All-rising typical price with steady volume: no selling pressure in the
    # window at all, so the index should sit at its maximum.
    up = pd.DataFrame({
        "open": np.arange(1.0, 30.0), "high": np.arange(1.5, 30.5), "low": np.arange(0.5, 29.5),
        "close": np.arange(1.0, 30.0), "volume": np.full(29, 1000.0),
    })
    assert mfi(up, 14).dropna().eq(100.0).all()


def test_cci_matches_formula_and_detects_channels():
    # Standard Lambert calculation verification
    bars = [
        (10, 12, 9, 11),
        (11, 13, 10, 12),
        (12, 14, 11, 13),
        (13, 15, 12, 14),
        (14, 16, 13, 15),
    ]
    df = make_bars(bars)
    c = cci(df, 5).dropna()
    assert len(c) == 1
    # Constant progression: TP = 11, 12, 13, 14, 15 (mean = 13, mad = 1.2, TP_last - mean = 2)
    # CCI = 2 / (0.015 * 1.2) = 111.111111...
    assert pytest.approx(c.iloc[0], 0.001) == 111.111


def test_cci_flat_series_returns_zero():
    # If price doesn't deviate from mean at all, CCI should be 0.0 without division by zero error
    flat = make_bars([(100, 100, 100, 100)] * 10)
    c = cci(flat, 5).dropna()
    assert (c == 0.0).all()


def test_indicator_supports_cci_80_from_user_rule():
    # Explicitly test cci_80 as reported by the user
    df = generate_sample_data(days=10, seed=1)
    spec = [{"name": "cci_80", "type": "cci", "period": 80}]
    out = add_indicators(df, spec)
    assert "cci_80" in out.columns
    assert not out["cci_80"].dropna().empty


def test_indicators_never_look_into_the_future():
    """Values computed on a truncated history must equal the same rows of the full history."""
    df = generate_sample_data(days=6, seed=3)
    full = add_indicators(df, SPECS)
    for k in (40, 111, 200):
        part = add_indicators(df.iloc[:k], SPECS)
        pd.testing.assert_frame_equal(part, full.iloc[:k], check_exact=False, rtol=1e-9)


def test_prev_columns_are_shifted_by_one_bar():
    df = add_prev_columns(make_bars([(1, 2, 0.5, 1.5), (2, 3, 1.5, 2.5), (3, 4, 2.5, 3.5)]))
    assert np.isnan(df["close_prev"].iloc[0])
    assert df["close_prev"].tolist()[1:] == [1.5, 2.5]


def test_indicator_config_errors_are_friendly():
    df = make_bars([(1, 2, 0.5, 1.5)] * 5)
    with pytest.raises(ConfigError, match="unknown type"):
        add_indicators(df, [{"name": "x", "type": "magic", "period": 3}])
    with pytest.raises(ConfigError, match="period"):
        add_indicators(df, [{"name": "x", "type": "sma"}])
    with pytest.raises(ConfigError, match="already used"):
        add_indicators(df, [{"name": "close", "type": "sma", "period": 3}])
    with pytest.raises(ConfigError, match="unknown settings"):
        add_indicators(df, [{"name": "x", "type": "sma", "period": 3, "perod": 4}])


def test_rule_expression_detects_a_crossover_with_prev_columns():
    closes = [10, 10, 10, 12, 12, 9, 9]
    df = make_bars([(c, c + 0.1, c - 0.1, c) for c in closes])
    df = add_prev_columns(add_indicators(df, [{"name": "s2", "type": "sma", "period": 2}]))
    up = evaluate_rule(df, "close > s2 and close_prev <= s2_prev", "entry_long")
    assert up.tolist() == [False, False, False, True, False, False, False]


@pytest.mark.parametrize("expr", [
    "close.shift(1) > 1",              # attribute / method access
    "__import__('os')",                # code
    "abs(close) > 1",                  # function call
    "close > @x",                      # variable injection
])
def test_dangerous_or_unsupported_rules_are_rejected(expr):
    df = make_bars([(1, 2, 0.5, 1.5)] * 3)
    with pytest.raises(ConfigError):
        evaluate_rule(df, expr, "entry_long")


def test_unknown_column_and_non_boolean_rules_are_rejected():
    df = make_bars([(1, 2, 0.5, 1.5)] * 3)
    with pytest.raises(ConfigError, match="could not be evaluated"):
        evaluate_rule(df, "close > nonexistent", "entry_long")
    with pytest.raises(ConfigError, match="true/false"):
        evaluate_rule(df, "close + 1", "entry_long")


def test_rules_strategy_needs_at_least_one_rule_and_rejects_typos():
    with pytest.raises(ConfigError):
        RuleStrategy({})
    with pytest.raises(ConfigError, match="unknown params"):
        RuleStrategy({"entry_lng": "close > 1"})


def test_rules_strategy_signals_follow_position_state():
    closes = [10, 10, 10, 12, 12, 9, 9]
    df = make_bars([(c, c + 0.1, c - 0.1, c) for c in closes])
    st = RuleStrategy({
        "indicators": [{"name": "s2", "type": "sma", "period": 2}],
        "entry_long": "close > s2 and close_prev <= s2_prev",
        "exit_long": "close < s2",
    })
    prepared = st.prepare(df)
    assert st.on_bar(3, prepared, 0) == "BUY"
    assert st.on_bar(3, prepared, 1) is None      # already long: no second entry
    assert st.on_bar(5, prepared, 1) == "EXIT"
    assert st.on_bar(5, prepared, 0) is None


def test_sma_crossover_validation_and_signals():
    with pytest.raises(ConfigError):
        SmaCrossover({"fast": 30, "slow": 10})
    with pytest.raises(ConfigError, match="unknown params"):
        SmaCrossover({"fats": 5})
    st = SmaCrossover({"fast": 2, "slow": 3})
    closes = [10, 10, 10, 11, 12, 13, 12, 10, 8]
    df = st.prepare(make_bars([(c, c + 0.1, c - 0.1, c) for c in closes]))
    assert st.on_bar(1, df, 0) is None            # still warming up
    assert st.on_bar(5, df, 0) == "BUY"
    assert st.on_bar(8, df, 1) == "SELL"


def test_strategy_signals_do_not_change_when_future_bars_are_added():
    df = generate_sample_data(days=6, seed=9)
    cfg_params = {
        "indicators": [{"name": "f", "type": "ema", "period": 5}, {"name": "s", "type": "ema", "period": 12}],
        "entry_long": "f > s and f_prev <= s_prev",
        "exit_long": "f < s",
        "entry_short": "f < s and f_prev >= s_prev",
        "exit_short": "f > s",
    }
    full_st, part_st = RuleStrategy(cfg_params), RuleStrategy(cfg_params)
    full = full_st.prepare(df)
    k = 250
    part = part_st.prepare(df.iloc[:k])
    for pos in (0, 1, -1):
        for i in range(k):
            assert full_st.on_bar(i, full, pos) == part_st.on_bar(i, part, pos)


def test_build_strategy_unknown_name():
    cfg = make_cfg(strategy={"name": "does_not_exist"})
    with pytest.raises(ConfigError, match="Unknown strategy"):
        build_strategy(cfg)
