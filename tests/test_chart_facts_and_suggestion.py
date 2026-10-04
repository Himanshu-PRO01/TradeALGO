import json

import pandas as pd

from algobot.ai_strategy_agent import StrategyAgent, UNAVAILABLE_MESSAGE
from algobot.chart_facts import chart_facts, describe_chart_facts
from algobot.ai_provider import AIProvider


def bars(ohlc):
    """ohlc: list of (open, high, low, close); volume defaults to 1000."""
    idx = pd.date_range("2026-09-01 09:15", periods=len(ohlc), freq="5min")
    rows = [{"open": o, "high": h, "low": l, "close": c, "volume": 1000} for o, h, l, c in ohlc]
    return pd.DataFrame(rows, index=idx)


# ------------------------------------------------------------ chart_facts()
def test_too_few_bars_returns_no_facts_instead_of_crashing():
    assert chart_facts(None) == {}
    assert chart_facts(bars([(1, 1, 1, 1)])) == {}


def test_previous_and_last_candle_direction_is_exactly_what_the_candle_shows():
    """The whole point of this feature: answer 'was the previous candle up or
    down' directly and correctly -- no guessing."""
    df = bars([(100, 105, 99, 103),     # bullish (close > open)
               (103, 104, 98, 99)])     # bearish (close < open) -- this is "previous" below
    df = pd.concat([df, bars([(99, 101, 97, 101)]).set_axis(
        pd.date_range("2026-09-01 09:25", periods=1, freq="5min"))])  # last candle: bullish
    facts = chart_facts(df, lookback=3)
    assert facts["candle.prev.direction"] == "bearish"
    assert facts["candle.last.direction"] == "bullish"
    assert facts["candle.prev.change_pct"] < 0
    assert facts["candle.last.change_pct"] > 0


def test_bullish_and_bearish_counts_over_the_lookback_window():
    df = bars([(10, 11, 9, 11),   # up
               (11, 12, 9, 9),    # down
               (9, 10, 8, 10),    # up
               (10, 11, 8, 8),    # down
               (8, 9, 7, 9)])     # up  -> 3 up, 2 down over last 5
    facts = chart_facts(df, lookback=5)
    assert facts["candle.last5.bullish_count"] == 3
    assert facts["candle.last5.bearish_count"] == 2
    assert facts["candle.last5.flat_count"] == 0


def test_trend_and_level_facts_appear_once_there_is_enough_history():
    df = bars([(100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(25)])
    facts = chart_facts(df)
    assert "trend.rsi14" in facts and 0 <= facts["trend.rsi14"] <= 100
    assert facts["trend.price_vs_sma20"] in ("above", "below")
    assert facts["levels.recent_swing_low"] < facts["levels.recent_swing_high"]


def test_describe_chart_facts_reads_naturally_and_skips_whats_missing():
    assert describe_chart_facts({}) == []
    lines = describe_chart_facts({"candle.prev.direction": "bearish", "candle.prev.change_pct": -0.42})
    assert any("Previous candle" in line and "bearish" in line for line in lines)
    assert not any("RSI" in line for line in lines)   # not supplied -> not claimed


# ------------------------------------------------------------ suggest_from_chart()
class FakeProvider(AIProvider):
    name = "fake"

    def __init__(self, reply):
        self.reply = reply

    def generate(self, system_prompt, user_prompt):
        return self.reply if isinstance(self.reply, str) else json.dumps(self.reply)


FACTS = {"candle.prev.direction": "bullish", "trend.rsi14": 58.3}


def test_suggest_from_chart_is_graceful_with_no_provider_configured():
    agent = StrategyAgent(provider=None)
    result = agent.suggest_from_chart(FACTS)
    assert result.available is False and result.ok is False
    assert result.message == UNAVAILABLE_MESSAGE


def test_suggest_from_chart_returns_the_suggestion_when_valid():
    reply = {"chart_read": "Uptrend, RSI healthy.", "suggested_entry": "rsi14 > 55",
             "suggested_exit": "rsi14 < 45", "caveats": ["Only checked on recent bars."],
             "cited_metrics": {"trend.rsi14": 58.3}}
    agent = StrategyAgent(provider=FakeProvider(reply))
    result = agent.suggest_from_chart(FACTS)
    assert result.ok is True
    assert result.data["suggested_entry"] == "rsi14 > 55"


def test_suggest_from_chart_rejects_a_fabricated_cited_number():
    """The citation check (shared with every other agent method) must apply here
    too: the AI cannot claim a chart fact that doesn't match what was supplied."""
    reply = {"chart_read": "x", "suggested_entry": "a", "suggested_exit": "b", "caveats": [],
             "cited_metrics": {"trend.rsi14": 99.9}}   # real value is 58.3
    agent = StrategyAgent(provider=FakeProvider(reply))
    result = agent.suggest_from_chart(FACTS)
    assert result.ok is False
    assert "58.3" in result.message or "rejected" in result.message.lower() or "cited" in result.message.lower()


def test_suggest_from_chart_rejects_overconfident_language():
    reply = {"chart_read": "x", "suggested_entry": "This is guaranteed to work.",
             "suggested_exit": "b", "caveats": [], "cited_metrics": {}}
    agent = StrategyAgent(provider=FakeProvider(reply))
    result = agent.suggest_from_chart(FACTS)
    assert result.ok is False
