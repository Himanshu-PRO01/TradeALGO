import pytest

from algobot.config import validate_config
from algobot.data import generate_sample_data
from algobot.explain import describe_indicator, explain_config, expression_to_english
from algobot.lookahead import (LeakyStrategy, check_future_scramble, check_indicator_columns,
                               check_truncation, run_lookahead_checks, selftest)
from algobot.strategy import RuleStrategy, SmaCrossover


def test_expression_readback_uses_plain_words():
    text = expression_to_english("ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev and rsi_14 < 30")
    assert text == ("ema_fast is above ema_slow AND previous ema_fast is at most previous ema_slow "
                    "AND rsi_14 is below 30")


def test_readback_keeps_the_direction_of_every_comparison():
    """The point of the readback: 'under 70' must never come back as 'over 70'."""
    assert "is below 70" in expression_to_english("rsi_14 < 70")
    assert "is above 70" in expression_to_english("rsi_14 > 70")
    assert "is at least 70" in expression_to_english("rsi_14 >= 70")
    assert "is at most 70" in expression_to_english("rsi_14 <= 70")
    assert "NOT" in expression_to_english("not close > vwap")
    assert " OR " in expression_to_english("close > vwap or rsi_14 < 20")


def test_indicator_descriptions():
    assert describe_indicator({"name": "f", "type": "ema", "period": 9}) == \
        "f = 9-bar exponential moving average of the close"
    assert "previous 20 bars" in describe_indicator({"name": "h", "type": "highest", "period": 20})


def _rules_cfg(**strategy):
    return validate_config({"strategy": {"name": "rules", "quantity": 5, **strategy}})


def test_explain_config_mentions_every_setting_the_trader_cares_about():
    cfg = validate_config({
        "capital": 250000,
        "strategy": {
            "name": "rules", "quantity": 25, "allow_short": False,
            "stop_loss_pct": 0.7, "target_pct": 1.4,
            "params": {
                "indicators": [{"name": "s20", "type": "sma", "period": 20}],
                "entry_long": "close > s20 and close_prev <= s20_prev",
                "exit_long": "close < s20",
            },
        },
        "risk": {"max_daily_loss": 1500, "max_trades_per_day": 4, "max_position_value": 40000,
                 "trading_start": "09:30", "no_new_entries_after": "14:30", "square_off_time": "15:10"},
    })
    text = explain_config(cfg)
    for expected in ["Rs 250,000", "25 share", "s20 = 20-bar simple moving average",
                     "Buy (go long) when: close is above s20 AND previous close is at most previous s20",
                     "NOT allowed", "0.7%", "1.4%", "Rs 1,500", "4 trade", "Rs 40,000",
                     "09:30", "14:30", "15:10", "example"]:
        assert expected in text, expected


def test_explain_says_so_when_protections_are_missing():
    text = explain_config(validate_config({"strategy": {"name": "sma_crossover"}}))
    assert "No stop-loss is set" in text
    assert "No daily loss limit is set" in text
    assert "No profit target is set" in text


def test_explain_sma_crossover():
    cfg = validate_config({"strategy": {"name": "sma_crossover", "params": {"fast": 5, "slow": 20}}})
    assert "5-bar average price is above the 20-bar average" in explain_config(cfg)


# ------------------------------------------------------------- look-ahead
DF = generate_sample_data(days=12, seed=21)

RULES = {
    "indicators": [
        {"name": "f", "type": "ema", "period": 5}, {"name": "s", "type": "ema", "period": 12},
        {"name": "r", "type": "rsi", "period": 9}, {"name": "h", "type": "highest", "period": 10},
        {"name": "v", "type": "vwap"}, {"name": "a", "type": "atr", "period": 7},
    ],
    "entry_long": "f > s and f_prev <= s_prev and r > 45 and close > v",
    "exit_long": "f < s",
    "entry_short": "close < h and close_prev >= h_prev and a > 0",
    "exit_short": "f > s",
}


@pytest.mark.parametrize("factory", [
    lambda: RuleStrategy(RULES),
    lambda: SmaCrossover({"fast": 5, "slow": 20}),
])
def test_honest_strategies_pass_every_check(factory):
    for check in (check_truncation(factory, DF), check_future_scramble(factory, DF),
                  check_indicator_columns(factory, DF)):
        assert check.passed, check.detail


def test_every_check_catches_a_strategy_that_peeks_one_bar_ahead():
    factory = lambda: LeakyStrategy({})
    assert not check_truncation(factory, DF).passed
    assert not check_future_scramble(factory, DF).passed
    assert not check_indicator_columns(factory, DF).passed


def test_selftest_helper_reports_all_failures():
    assert all(not c.passed for c in selftest(DF))


def test_run_lookahead_checks_on_a_validated_config():
    cfg = validate_config({"strategy": {"name": "rules", "params": RULES}})
    assert all(c.passed for c in run_lookahead_checks(cfg, DF))


def test_a_subtle_leak_is_caught_too():
    """A 'centered' moving average uses future bars; scramble and indicator checks must notice."""
    class CenteredAverage(SmaCrossover):
        def prepare(self, df):
            df = df.copy()
            df["sma_fast"] = df["close"].rolling(5, center=True).mean()   # peeks 2 bars ahead
            df["sma_slow"] = df["close"].rolling(15, center=True).mean()
            return df
    factory = lambda: CenteredAverage({"fast": 5, "slow": 15})
    assert not check_indicator_columns(factory, DF).passed
    assert not check_future_scramble(factory, DF).passed
