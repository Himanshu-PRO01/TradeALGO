import datetime as dt
import os

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from algobot import ui  # noqa: E402
from algobot.charts import candlestick, equity_drawdown, payoff_chart, pnl_bars, premium_line  # noqa: E402
from algobot.feedback import FeedbackError, FeedbackStore  # noqa: E402
from algobot.journal import Journal, JournalError, journal_rows_from_csv, journal_to_csv  # noqa: E402
from algobot.options import breakeven_analysis, payoff_curve  # noqa: E402
from algobot.practice import PracticeSession, PracticeSettings  # noqa: E402
from algobot.worlds import generate_world  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app(name, **state):
    path = os.path.join(ROOT, name)
    at = AppTest.from_file(path, default_timeout=60)
    for key, value in state.items():
        at.session_state[key] = value
    return at


# ------------------------------------------------------------------ charts
def test_candlestick_handles_normal_empty_and_tiny_inputs():
    df = generate_world("trend", 3, 2, 24500.0)
    assert candlestick(df) is not None
    assert candlestick(df.iloc[:0]) is None
    assert candlestick(df.iloc[:1]) is not None
    assert candlestick(df, volume=False) is not None


def test_candlestick_draws_trade_markers_only_for_bars_on_screen():
    df = generate_world("noise", 3, 2, 1000.0)
    trades = pd.DataFrame([
        {"entry_time": df.index[10], "exit_time": df.index[20], "side": "LONG", "entry_price": 1000.0, "exit_price": 1005.0, "net_pnl": 40.0},
        {"entry_time": df.index[50], "exit_time": pd.NaT, "side": "SHORT", "entry_price": 1001.0, "exit_price": np.nan, "net_pnl": 0.0},
    ])
    chart = candlestick(df, trades=trades, hlines={"day open": 1000.0, "junk": float("nan")}, max_bars=400)
    text = str(chart.to_dict())
    assert "triangle-up" in text and "triangle-down" in text and "day open" in text and "junk" not in text
    # Trades outside the visible window are quietly left out instead of crashing.
    hidden = candlestick(df, trades=trades, max_bars=5)
    assert hidden is not None and "triangle" not in str(hidden.to_dict())


def test_other_charts_build_and_refuse_to_draw_nothing():
    series = pd.Series(np.linspace(100, 110, 30), index=pd.date_range("2025-01-06 09:15", periods=30, freq="5min"))
    assert equity_drawdown(series) is not None and equity_drawdown(series.iloc[:1]) is None
    assert pnl_bars(pd.Series([50.0, -20.0], index=["a", "b"])) is not None and pnl_bars(pd.Series(dtype=float)) is None
    assert premium_line(series, entry=101, stop=99) is not None and premium_line(series.iloc[:1]) is None
    curve = payoff_curve(24500, 24500, 3, 14, "CE", 1, 65)
    assert payoff_chart(curve, 45.0) is not None and payoff_chart(curve.iloc[:1]) is None


def test_payoff_curve_crosses_zero_at_the_breakeven_move():
    kw = dict(spot=24500, strike=24500, days_to_expiry=3, iv_pct=14, kind="CE", holding_days=1, lot_size=65)
    for extra in (dict(), dict(entry_premium=140.0, spread_per_unit=1.0, charges_round_trip=100.0),
                  dict(spread_per_unit=0.6, charges_round_trip=100.0, iv_change_pct=-2)):
        curve = payoff_curve(**kw, **extra)
        be = breakeven_analysis(**kw, **extra)["breakeven_points"]
        assert abs(float(np.interp(be, curve["move"], curve["pnl_per_lot"]))) < 5.0      # rupees per lot, interpolation error
        assert curve["pnl_per_lot"].is_monotonic_increasing                                 # a call: up is better
    puts = payoff_curve(**{**kw, "kind": "PE"})
    assert puts["pnl_per_lot"].is_monotonic_decreasing                                      # a put: down is better
    with pytest.raises(ValueError):
        payoff_curve(**kw, points=2)


# ------------------------------------------------------------------ ui helpers
def test_number_helpers():
    assert ui.inr(1234.4) == "₹1,234" and ui.inr(-500) == "-₹500" and ui.inr(720, sign=True) == "+₹720"
    assert ui.tone(5) == "up" and ui.tone(-5) == "down" and ui.tone(0) == ""


def test_html_helpers_escape_what_they_are_given():
    assert "<script>" not in ui.pill("<script>alert(1)</script>")
    assert "&lt;script&gt;" in ui.card("<b>x</b>", "<script>alert(1)</script>")


# ------------------------------------------------------------------ practice markers need the spot levels
def test_practice_records_carry_the_index_level_at_entry_and_exit():
    bars = generate_world("trend", 3, 4, 24500.0)
    s = PracticeSession(bars, PracticeSettings(capital=100000.0), start_index=20)
    entry_spot = s.spot
    s.buy("CE", s.atm_strike(), 1)
    s.advance(10)
    exit_spot = s.spot
    rec = s.close()
    assert rec["entry_spot"] == pytest.approx(entry_spot) and rec["exit_spot"] == pytest.approx(exit_spot)


# ------------------------------------------------------------------ journal backup
def test_journal_csv_round_trip_keeps_everything_including_awkward_text():
    j = Journal()
    a = j.add_trade("NIFTY 24500 CE", "BUY", 65, 100, opened_at="2026-09-21 10:00", stop_price=85, target_price=130,
                    setup="breakout", notes='says "hi", then\nnew line')
    j.close_trade(a, 112, closed_at="2026-09-21 12:00", charges=60, lessons="waited for the close")
    j.add_trade("NIFTY 24400 PE", "BUY", 65, 90, opened_at="2026-09-21 14:00")             # still open
    k = Journal()
    assert k.import_rows(journal_rows_from_csv(journal_to_csv(j))) == 2
    first, second = k.all_trades()
    assert first.net_pnl == pytest.approx(720) and first.stop_price == 85 and first.target_price == 130
    assert first.notes == 'says "hi", then\nnew line' and first.lessons == "waited for the close"
    assert second.exit_price is None and second.stop_price is None


def test_bad_journal_files_are_refused_with_a_reason():
    with pytest.raises(JournalError, match="missing columns"):
        journal_rows_from_csv("a,b\n1,2\n")
    with pytest.raises(JournalError):
        Journal().import_rows([{"instrument": "X", "side": "HOLD", "qty": 1, "entry_price": 1, "opened_at": "2026-09-21 10:00"}])


# ------------------------------------------------------------------ feedback
def test_feedback_is_saved_shared_and_defused_for_spreadsheets(tmp_path):
    path = str(tmp_path / "f.csv")
    store = FeedbackStore(path)
    store.add("Bhai", "Practice room", "A feature is missing", "Must have", "Show open interest", "=HYPERLINK(\"x\")")
    store.add("", "Test lab", "Other", "Nice to have", "Nicer colours")
    text = store.to_text()
    assert text.index("Must have") < text.index("Nice to have") and "Show open interest" in text
    assert "'=HYPERLINK" in store.to_csv() and "'=HYPERLINK" in open(path, encoding="utf-8").read()   # no live formula
    assert len(FeedbackStore(path).items) == 2                                                          # survives a restart
    with pytest.raises(FeedbackError):
        store.add("x", "Test lab", "Other", "Nice to have", "   ")
    with pytest.raises(FeedbackError):
        store.add("x", "Test lab", "Other", "Nice to have", "y" * 3001)


def test_feedback_page_saves_and_offers_the_text_to_send(tmp_path, monkeypatch):
    monkeypatch.setenv("ALGOBOT_FEEDBACK", str(tmp_path / "fb.csv"))
    at = app("pages/8_Feedback.py")
    at.run()
    assert not at.exception
    at.text_area(key="fb_message").set_value("The option chain needs open interest.")
    at.button(key="fb_submit").click().run()
    assert not at.exception and any("Saved" in s.value for s in at.success)
    assert "open interest" in at.text_area(key="fb_share").value
    assert (tmp_path / "fb.csv").exists()
    at.text_area(key="fb_message").set_value("   ")
    at.button(key="fb_submit").click().run()
    assert any("Please write" in e.value for e in at.error)


# ------------------------------------------------------------------ front page
def test_front_page_loads_with_links_and_the_safety_strip():
    at = app("Trading_Desk.py")
    at.run()
    assert not at.exception
    strip = " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in getattr(at, "caption", []))
    assert "LIVE DISABLED" in strip or "RESEARCH" in strip
    assert "EXECUTION" in strip


def test_the_old_entry_point_still_starts_the_same_page():
    at = app("dashboard.py")
    at.run()
    assert not at.exception and any("Trading Desk" in m.value for m in at.markdown)


def test_every_page_in_the_menu_loads_with_no_exception():
    pages = sorted(os.listdir(os.path.join(ROOT, "pages")))
    assert len(pages) >= 8
    for name in pages:
        at = app(os.path.join("pages", name))
        at.run()
        assert not at.exception, name


# ------------------------------------------------------------------ password screen and hosted mode
def test_password_screen_blocks_every_page_until_the_right_password(monkeypatch):
    monkeypatch.setenv("ALGOBOT_PASSWORD", "open-sesame")
    at = app("pages/1_Position_size.py")
    at.run()
    assert not at.exception
    assert not any("how many lots fit" in m.value for m in at.markdown)             # the page content is not shown
    assert any("Private trading desk" in m.value for m in at.markdown)
    at.text_input(key="ab_pw").set_value("wrong")
    at.button(key="ab_login_btn").click().run()
    assert any("not right" in e.value for e in at.error)
    assert not any("how many lots fit" in m.value for m in at.markdown)
    at.text_input(key="ab_pw").set_value("open-sesame")
    at.button(key="ab_login_btn").click().run()
    assert not at.exception and any("Lots allowed" in m.value for m in at.markdown)


def test_too_many_wrong_passwords_lock_the_session(monkeypatch):
    monkeypatch.setenv("ALGOBOT_PASSWORD", "open-sesame")
    monkeypatch.setattr("time.sleep", lambda s: None)
    at = app("pages/1_Position_size.py")
    at.run()
    for _ in range(5):
        at.text_input(key="ab_pw").set_value("nope")
        at.button(key="ab_login_btn").click().run()
    at.run()
    assert any("Too many wrong tries" in e.value for e in at.error)
    assert not [w for w in at.text_input if w.key == "ab_pw"]                       # the box is gone


def test_hosted_mode_keeps_each_visitors_journal_in_memory_only(tmp_path, monkeypatch):
    monkeypatch.setenv("ALGOBOT_HOSTED", "1")
    monkeypatch.setenv("ALGOBOT_JOURNAL", str(tmp_path / "journal.db"))
    at = app("pages/2_Journal_and_report.py")
    at.run()
    assert not at.exception
    at.text_input(key="j_instrument").set_value("NIFTY 24500 CE")
    at.number_input(key="j_entry").set_value(100.0)
    at.number_input(key="j_stop").set_value(85.0)
    at.text_input(key="j_opened").set_value("2026-09-21 10:00")
    at.button(key="j_add").click().run()
    assert not at.exception and any("Trade #1 recorded" in s.value for s in at.success)
    at.button(key="j_add").click().run()                                            # rerun in the same session
    assert not at.exception and at.session_state["_ab_journal"].all_trades()[0].instrument == "NIFTY 24500 CE"
    assert not (tmp_path / "journal.db").exists()                                   # nothing written to a shared file
    assert any("Kept only while this browser tab is open" in m.value for m in at.markdown)
    # a different visitor (a new session) does not see it
    other = app("pages/2_Journal_and_report.py")
    other.run()
    assert other.session_state["_ab_journal"].all_trades() == []


def test_local_mode_still_saves_to_the_journal_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ALGOBOT_JOURNAL", str(tmp_path / "journal.db"))
    at = app("pages/2_Journal_and_report.py")
    at.run()
    at.text_input(key="j_instrument").set_value("NIFTY 24500 CE")
    at.number_input(key="j_entry").set_value(100.0)
    at.text_input(key="j_opened").set_value("2026-09-21 10:00")
    at.button(key="j_add").click().run()
    assert (tmp_path / "journal.db").exists() and len(Journal(str(tmp_path / "journal.db")).all_trades()) == 1
    assert any("Saved on this computer" in m.value for m in at.markdown)


def test_launchers_and_the_start_here_guide_ship_with_the_project():
    for name in ("run_windows.bat", "run_mac.command", "START_HERE.txt", ".streamlit/config.toml", "HOSTING.md"):
        assert os.path.exists(os.path.join(ROOT, name)), name
    bat = open(os.path.join(ROOT, "run_windows.bat"), encoding="utf-8").read()
    assert "Trading_Desk.py" in bat and "requirements.txt" in bat
