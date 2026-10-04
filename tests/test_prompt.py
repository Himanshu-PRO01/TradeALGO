from algobot.indicators import INDICATOR_TYPES
from algobot.prompt import AI_STRATEGY_PROMPT


def test_prompt_lists_every_indicator_type_the_engine_actually_supports():
    """Caught a real bug: the prompt's list had fallen behind indicators.py
    (missing opening_range_high/low and the pivot_* types), so an AI following
    the prompt would never suggest strategies using them even though the
    engine supports them. This pins the two together."""
    for kind in INDICATOR_TYPES:
        assert kind in AI_STRATEGY_PROMPT, f"{kind!r} is a real indicator type but missing from AI_STRATEGY_PROMPT"


def test_prompt_does_not_list_a_type_the_engine_does_not_support():
    """The reverse mistake would be worse: the AI could invent a plausible-sounding
    condition using a type that then fails validation with a confusing error."""
    claimed = {
        "sma", "ema", "wma", "hma", "rsi", "mfi", "atr", "highest", "lowest", "vwap",
        "prev_day_high", "prev_day_low", "prev_day_close",
        "prev_week_high", "prev_week_low", "swing_high", "swing_low",
        "opening_range_high", "opening_range_low",
        "pivot", "pivot_r1", "pivot_r2", "pivot_r3", "pivot_s1", "pivot_s2", "pivot_s3",
    }
    assert claimed == set(INDICATOR_TYPES)
