import numpy as np
import pandas as pd
import pytest

from algobot.data import generate_sample_data
from algobot.indicators import add_indicators
from algobot.levels import prev_day, prev_week, swing_high, swing_low
from algobot.lookahead import check_future_scramble, check_indicator_columns, check_truncation
from algobot.strategy import RuleStrategy
from helpers import make_bars


def two_days():
    d1 = make_bars([(100, 105, 99, 101), (101, 108, 100, 107), (107, 107.5, 103, 104)], day="2025-01-06")
    d2 = make_bars([(104, 106, 102, 105), (105, 109, 104, 108)], day="2025-01-07")
    d3 = make_bars([(108, 110, 107, 109)], day="2025-01-08")
    return pd.concat([d1, d2, d3])


def test_previous_day_levels_use_only_the_finished_previous_day():
    df = two_days()
    pdh, pdl, pdc = prev_day(df, "high"), prev_day(df, "low"), prev_day(df, "close")
    assert pdh.iloc[:3].isna().all()                        # no earlier day exists
    assert pdh.iloc[3:5].tolist() == [108, 108]              # day 1 high
    assert pdl.iloc[3:5].tolist() == [99, 99]                # day 1 low
    assert pdc.iloc[3:5].tolist() == [104, 104]              # day 1 last close
    assert pdh.iloc[5] == 109 and pdl.iloc[5] == 102         # day 2 -> day 3


def test_previous_week_levels():
    wk1 = make_bars([(100, 110, 95, 105)] * 2, day="2025-01-06")      # Monday of week 1
    wk1b = make_bars([(105, 112, 100, 108)], day="2025-01-10")         # Friday of week 1
    wk2 = make_bars([(108, 109, 107, 108)] * 2, day="2025-01-13")      # Monday of week 2
    df = pd.concat([wk1, wk1b, wk2])
    pwh, pwl = prev_week(df, "high"), prev_week(df, "low")
    assert pwh.iloc[:3].isna().all()
    assert pwh.iloc[3:].tolist() == [112, 112] and pwl.iloc[3:].tolist() == [95, 95]


def test_swing_high_appears_only_after_it_is_confirmed_then_persists():
    highs = [1, 2, 5, 2, 1, 2, 3, 7, 3, 2, 1, 1]
    df = make_bars([(h, h, h - 0.5, h) for h in highs])
    level = swing_high(df, 2)
    assert level.iloc[:4].isna().all()                # the 5 at bar 2 needs bars 3 and 4 first
    assert level.iloc[4:9].tolist() == [5, 5, 5, 5, 5]
    assert level.iloc[9:].tolist() == [7, 7, 7]       # the 7 at bar 7 is confirmed at bar 9


def test_swing_low_mirror():
    lows = [9, 8, 4, 8, 9, 8, 7, 3, 7, 8, 9, 9]
    df = make_bars([(l + 0.5, l + 1, l, l + 0.5) for l in lows])
    level = swing_low(df, 2)
    assert level.iloc[:4].isna().all()
    assert level.iloc[4:9].tolist() == [4] * 5
    assert level.iloc[9:].tolist() == [3] * 3


@pytest.mark.parametrize("spec", [
    {"name": "x", "type": "prev_day_high"},
    {"name": "x", "type": "prev_day_low"},
    {"name": "x", "type": "prev_day_close"},
    {"name": "x", "type": "prev_week_high"},
    {"name": "x", "type": "prev_week_low"},
    {"name": "x", "type": "swing_high", "period": 3},
    {"name": "x", "type": "swing_low", "period": 3},
])
def test_level_indicators_pass_all_lookahead_checks(spec):
    df = generate_sample_data(days=14, seed=4)
    params = {
        "indicators": [spec],
        "entry_long": "close > x and close_prev <= x_prev",
        "exit_long": "close < x",
        "entry_short": "close < x and close_prev >= x_prev",
        "exit_short": "close > x",
    }
    factory = lambda: RuleStrategy(params)  # noqa: E731
    for check in (check_truncation(factory, df), check_future_scramble(factory, df),
                  check_indicator_columns(factory, df)):
        assert check.passed, f"{spec['type']}: {check.detail}"


def test_swing_needs_a_period_but_prev_levels_do_not():
    df = two_days()
    add_indicators(df, [{"name": "a", "type": "prev_day_high"}])           # fine without period
    with pytest.raises(Exception, match="period"):
        add_indicators(df, [{"name": "a", "type": "swing_high"}])


def test_a_breakout_of_the_previous_day_high_can_be_written_as_a_rule():
    df = two_days()
    st = RuleStrategy({
        "indicators": [{"name": "pdh", "type": "prev_day_high"}],
        "entry_long": "close > pdh and close_prev <= pdh_prev",
    })
    prepared = st.prepare(df)
    # Day 2, bar 2 (index 4) closes at 108 == previous day's high 108: not above it. No signal.
    assert st.on_bar(4, prepared, 0) is None
    # Day 3 opens above day 2's high (109): close 109 vs pdh 109 -> also not above. No signal.
    assert st.on_bar(5, prepared, 0) is None
