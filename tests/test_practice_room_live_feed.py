"""Practice Room's Live mode can stream real ticks from the shared Upstox market-data
hub (algobot.live_market) instead of polling Yahoo Finance every 60s. These tests drive
that path with a fake hub -- no network, no real token -- and pin down two behaviours
that are easy to silently break:

  1. When a token is configured, Upstox is offered and used, and the price shown on
     the page is exactly what the hub reports (not a stale Yahoo bar).
  2. The auto-refresh loop is SELF-LIMITING. It must not spin in a tight loop calling
     st.rerun() forever within a single render -- that would hang this test suite (and
     waste a real server's CPU) instead of pacing itself, one rerun per interval.
"""
import os

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import algobot.live_market as live_market

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "pages", "3_Practice_room.py")


class FakeHub:
    """Stands in for algobot.live_market.LiveMarketHub: an in-memory feed with no
    background thread and no network, so tests are fast and deterministic."""

    def __init__(self, bars: pd.DataFrame, latest: dict | None, connected: bool = True):
        self.bars = bars
        self.latest_tick = latest
        self.connected = connected
        self.started_with = None
        self.snapshot_calls = 0

    def start(self, instrument_keys):
        self.started_with = instrument_keys

    def snapshot(self, instrument_key, max_bars=300):
        self.snapshot_calls += 1
        return self.bars.tail(max_bars).copy()

    def latest(self, instrument_key):
        return self.latest_tick

    def status(self):
        return {"connected": self.connected, "last_error": None, "ticks": self.snapshot_calls * 100}


def _bars(prices, start="2026-09-29 09:15"):
    idx = pd.date_range(start, periods=len(prices), freq="1min")
    return pd.DataFrame({"open": prices, "high": [p + 1 for p in prices], "low": [p - 1 for p in prices],
                          "close": prices, "volume": [1000] * len(prices)}, index=idx)


@pytest.fixture
def fake_hub(monkeypatch):
    hub = FakeHub(_bars([24500.0, 24510.0, 24525.0]),
                   {"price": 24525.0, "datetime": pd.Timestamp("2026-09-29 09:17:42")})
    monkeypatch.setattr(live_market, "get_market_hub", lambda token: hub)
    monkeypatch.setattr(live_market, "market_data_token", lambda: "fake-token-not-a-real-secret")
    return hub


def _start_live(at, feed_label=None):
    at.run()
    at.radio(key="pr_source").set_value("⚡ Live (real-time + AI)").run()
    if feed_label:
        at.radio(key="pr_live_feed").set_value(feed_label)
    at.button(key="pr_start").click().run()
    return at


def test_upstox_is_offered_and_selected_by_default_when_a_token_is_configured(fake_hub):
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    at.radio(key="pr_source").set_value("⚡ Live (real-time + AI)").run()
    feed = at.radio(key="pr_live_feed")
    assert feed.value.startswith("🟢"), "Upstox should be the recommended default when a token exists"
    assert any("Yahoo" in o for o in feed.options), "Yahoo should still be offered as a fallback"


def test_starting_a_live_session_streams_the_hubs_price_not_a_stale_one(fake_hub):
    at = _start_live(AppTest.from_file(PAGE, default_timeout=60))
    assert not at.exception, at.exception
    assert st_session_source(at) == "upstox"
    assert fake_hub.started_with == ["NSE_INDEX|Nifty 50"]
    ticker_html = "".join(m.value for m in at.markdown if "ab-strip" in m.value)
    assert "24,525.0" in ticker_html          # the hub's price, not a fetched-elsewhere one
    assert "Last tick" in ticker_html and "09:17:42" in ticker_html


def test_the_autorefresh_loop_does_not_hang_the_test_suite(fake_hub):
    """The single most important regression check here: an earlier version of this
    feature called st.rerun() unconditionally at the end of every render for the
    Upstox path, with no condition that ever became false. That hangs forever (in
    this test suite, and burns a thread pointlessly on a real server). AppTest's
    default_timeout is the backstop -- if this test times out, the loop is back."""
    at = _start_live(AppTest.from_file(PAGE, default_timeout=15))
    assert not at.exception, at.exception


def test_no_ticks_yet_shows_a_connecting_message_and_still_resolves(monkeypatch):
    calls = {"n": 0}
    bars_when_ready = _bars([100.0])

    class SlowHub(FakeHub):
        def snapshot(self, instrument_key, max_bars=300):
            calls["n"] += 1
            return pd.DataFrame() if calls["n"] == 1 else bars_when_ready.copy()

        def latest(self, instrument_key):
            return None if calls["n"] < 2 else {"price": 100.0, "datetime": pd.Timestamp("2026-09-29 09:15:03")}

        def status(self):
            return {"connected": calls["n"] >= 2, "last_error": None, "ticks": 0 if calls["n"] < 2 else 1}

    hub = SlowHub(bars_when_ready, None)
    monkeypatch.setattr(live_market, "get_market_hub", lambda token: hub)
    monkeypatch.setattr(live_market, "market_data_token", lambda: "fake-token-not-a-real-secret")

    at = _start_live(AppTest.from_file(PAGE, default_timeout=30))
    assert not at.exception, at.exception
    assert calls["n"] >= 2, "should keep polling until the first bar arrives, not give up or crash"


def test_no_token_falls_back_to_yahoo_and_offers_no_upstox_choice(monkeypatch):
    monkeypatch.setattr(live_market, "market_data_token", lambda: "")
    at = AppTest.from_file(PAGE, default_timeout=60)
    at.run()
    at.radio(key="pr_source").set_value("⚡ Live (real-time + AI)").run()
    assert not at.exception
    # No token -> the feed radio isn't shown at all; Yahoo is used silently, as before.
    assert "pr_live_feed" not in {getattr(r, "key", None) for r in at.radio}
    assert any("UPSTOX_ANALYTICS_TOKEN" in c.value for c in at.caption)


def st_session_source(at):
    return at.session_state.get("live_data_source")
