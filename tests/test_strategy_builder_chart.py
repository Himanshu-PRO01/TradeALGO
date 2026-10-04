"""Strategy Builder's 'Look at a real chart' section: loads real OHLCV data,
shows plain computed facts (answers 'was the previous candle up or down'
directly, no AI needed), and optionally asks an AI provider to turn those same
facts into a suggested entry/exit rule that can be dropped straight into the
form below it.
"""
import os

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import algobot.live_data as live_data
from algobot.ai_strategy_agent import StrategyAgent

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "pages", "10_Strategy_Builder.py")


def _bars(n=30):
    idx = pd.date_range("2026-09-01 09:15", periods=n, freq="15min")
    closes = [24500.0 + i for i in range(n)]
    rows = [{"open": c - 1, "high": c + 2, "low": c - 2, "close": c, "volume": 1000} for c in closes]
    rows[-1] = {"open": closes[-1] + 5, "high": closes[-1] + 6, "low": closes[-1] - 1,
                "close": closes[-1], "volume": 1000}   # last candle: close < open -> bearish
    return pd.DataFrame(rows, index=idx)


@pytest.fixture
def fake_feed(monkeypatch):
    monkeypatch.setattr(live_data, "fetch_ohlc", lambda ticker, interval, period: _bars())


def test_loading_a_chart_shows_the_previous_candle_direction_with_no_ai_needed(fake_feed):
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    at.button(key="sb_chart_load").click().run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Previous candle" in text and "bearish" in text
    # No AI provider configured in this test environment -> suggestion button
    # should not even be offered, but the computed facts above must still show.
    assert not any(getattr(b, "key", None) == "sb_chart_ai_btn" for b in at.button)


def test_real_data_failure_falls_back_to_practice_data_instead_of_crashing(monkeypatch):
    import algobot.live_data as ld

    def boom(ticker, interval, period):
        raise ld.LiveDataError("no internet in this sandbox")
    monkeypatch.setattr(ld, "fetch_ohlc", boom)

    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    at.button(key="sb_chart_load").click().run()
    assert not at.exception
    assert any("practice data" in e.value.lower() for e in at.error)
    assert any("Previous candle" in m.value for m in at.markdown)  # still shows something


def test_ai_suggestion_can_be_dropped_straight_into_the_form(fake_feed, monkeypatch):
    class FakeAgent:
        available = True
        provider = type("P", (), {"name": "fake", "model": ""})()

        def suggest_from_chart(self, facts):
            from algobot.ai_strategy_agent import AgentResult
            return AgentResult(True, True, "ok", {
                "chart_read": "Price just pulled back on the last candle.",
                "suggested_entry": "close > sma20 and rsi14 > 55",
                "suggested_exit": "rsi14 < 45",
                "caveats": ["Based on a short lookback window."],
                "cited_metrics": {},
            })

    monkeypatch.setattr("algobot.ai_strategy_agent.StrategyAgent", FakeAgent)

    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    at.button(key="sb_chart_load").click().run()
    assert not at.exception
    at.button(key="sb_chart_ai_btn").click().run()
    assert not at.exception
    assert any("pulled back" in i.value for i in at.info)   # st.info(ai["chart_read"])

    at.button(key="sb_use_entry").click().run()
    assert not at.exception
    assert at.text_area(key="sb_level").value == "close > sma20 and rsi14 > 55"

    at.button(key="sb_use_confirmation").click().run()
    assert not at.exception
    assert at.text_area(key="sb_confirmation").value == "rsi14 < 45"
