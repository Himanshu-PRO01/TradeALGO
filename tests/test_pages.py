import datetime as dt
import os

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def page(name, monkeypatch=None, db=None):
    if monkeypatch is not None and db is not None:
        monkeypatch.setenv("ALGOBOT_JOURNAL", db)
    at = AppTest.from_file(os.path.join(ROOT, "pages", name), default_timeout=60)
    at.run()
    return at


def test_position_size_page_defaults_match_the_brothers_numbers():
    at = page("1_Position_size.py")
    assert not at.exception
    assert [m.value for m in at.metric][0] == "1"                       # 1 lot fits
    assert any("10% of capital" in w.value for w in at.warning)          # Rs 1,000 on Rs 10,000


def test_position_size_page_explains_a_trade_that_does_not_fit():
    at = page("1_Position_size.py")
    at.number_input(key="ps_stop").set_value(60.0).run()                 # stop 40 points away
    assert not at.exception
    assert [m.value for m in at.metric][0] == "0"
    assert any("premium points" in w.value for w in at.warning)


def test_position_size_page_rejects_a_stop_above_the_entry():
    at = page("1_Position_size.py")
    at.number_input(key="ps_stop").set_value(120.0).run()
    assert not at.exception and any("BELOW" in e.value for e in at.error)


def test_journal_page_full_flow(tmp_path, monkeypatch):
    at = page("2_Journal_and_report.py", monkeypatch, str(tmp_path / "j.db"))
    assert not at.exception
    assert any("No trades were closed today." in t.value for t in at.text)

    at.text_input(key="j_instrument").set_value("NIFTY 24500 CE")
    at.number_input(key="j_entry").set_value(100.0)
    at.number_input(key="j_stop").set_value(85.0)
    at.text_input(key="j_setup").set_value("resistance breakout")
    at.text_input(key="j_opened").set_value("2026-09-21 10:00")
    at.button(key="j_add").click().run()
    assert not at.exception and any("Trade #1 recorded" in s.value for s in at.success)

    at.number_input(key="j_exit").set_value(112.0)
    at.number_input(key="j_charges").set_value(60.0)
    at.text_area(key="j_lessons").set_value("waited for the close")
    at.text_input(key="j_closed").set_value("2026-09-21 13:00")
    at.button(key="j_close").click().run()
    assert not at.exception and any("Net Rs 720.00" in s.value for s in at.success)

    at.date_input(key="r_day").set_value(dt.date(2026, 9, 21)).run()
    assert any("Net for the day: Rs 720.00" in t.value for t in at.text)
    assert any("1 closed trade" in t.value for t in at.text)


def test_journal_page_shows_friendly_errors(tmp_path, monkeypatch):
    at = page("2_Journal_and_report.py", monkeypatch, str(tmp_path / "j.db"))
    at.text_input(key="j_instrument").set_value("X")
    at.number_input(key="j_entry").set_value(100.0)
    at.number_input(key="j_stop").set_value(120.0)                       # stop above a BUY entry
    at.button(key="j_add").click().run()
    assert not at.exception and any("BELOW" in e.value for e in at.error)


def test_position_size_page_shows_the_gate_from_the_journal(tmp_path, monkeypatch):
    from algobot.journal import Journal
    today = dt.date.today()
    db = str(tmp_path / "j.db")
    at = page("1_Position_size.py", monkeypatch, db)
    assert not at.exception
    assert any("OK by your own rules" in s.value for s in at.success)             # empty journal: open

    j = Journal(db)
    for hour in (9, 10):                                                           # two trades already today
        i = j.add_trade("X", "BUY", 65, 100, opened_at=f"{today} {hour:02d}:00", stop_price=90)
        j.close_trade(i, 101, closed_at=f"{today} {hour:02d}:30")
    j.close_db()
    at = page("1_Position_size.py", monkeypatch, db)
    assert any("BLOCKED" in e.value and "already opened today" in e.value for e in at.error)


def test_strategy_scanner_page_runs_end_to_end_on_sample_data():
    at = page("15_Strategy_Scanner.py")
    assert not at.exception
    at.radio(key=None if not at.radio else at.radio[0].key).set_value("Generate sample data").run() \
        if at.radio else None
    # Keep the run small so the smoke test is fast.
    if at.slider:
        for s in at.slider:
            if s.label and "combo" in s.label.lower():
                s.set_value(2)
    if at.button:
        at.button[0].click().run()
    assert not at.exception
