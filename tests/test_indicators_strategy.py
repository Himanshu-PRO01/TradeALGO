import numpy as np
import pandas as pd
import pytest

from algobot.config import ConfigError
from algobot.data import generate_sample_data
from algobot.indicators import add_indicators, add_prev_columns, rsi, sma
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
