import os

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "pages", "5_Backtest.py")


def fresh():
    at = AppTest.from_file(APP, default_timeout=90)
    at.run()
    return at


def texts(elements):
    return " ".join(str(getattr(e, "value", "")) for e in elements)


def test_dashboard_starts_without_errors_and_shows_the_plain_english_readback():
    at = fresh()
    assert not at.exception
    assert any("Buy (go long) when" in t.value for t in at.text)
    assert any("Short selling is NOT allowed" in t.value for t in at.text)
    # Buttons stay locked until the trader confirms the readback.
    assert at.button(key="btn_run").disabled
    assert at.button(key="btn_lookahead").disabled


def test_confirming_unlocks_the_buttons_and_a_backtest_shows_results():
    at = fresh()
    at.checkbox(key="confirm").check().run()
    assert not at.button(key="btn_run").disabled
    at.button(key="btn_run").click().run()
    assert not at.exception
    markdown = " ".join(str(getattr(m, "value", "")) for m in at.markdown)
    assert "Costs paid" in markdown and "Trades" in markdown
    assert any("random sample data" in w.value for w in at.warning)   # honesty banner


def test_lookahead_button_reports_green_checks_for_honest_rules():
    at = fresh()
    at.checkbox(key="confirm").check().run()
    at.button(key="btn_lookahead").click().run()
    assert not at.exception
    assert len(at.success) == 3 and len(at.error) == 0


def test_a_bad_rule_gives_a_friendly_error_not_a_crash():
    at = fresh()
    at.text_area(key="rules_text").set_value('entry_long: "close > nonexistent_column"').run()
    assert not at.exception
    assert any("could not be evaluated" in e.value for e in at.error)


def test_dangerous_rule_syntax_is_refused():
    at = fresh()
    at.text_area(key="rules_text").set_value('entry_long: "close.shift(-1) > close"').run()
    assert not at.exception
    assert any("not allowed" in e.value for e in at.error)


def test_bad_time_and_bad_yaml_are_reported():
    at = fresh()
    at.text_input(key="t_start").set_value("25:99").run()
    assert not at.exception
    assert any("must be a time" in e.value for e in at.error)

    at = fresh()
    at.text_area(key="rules_text").set_value("entry_long: [unclosed").run()
    assert not at.exception
    assert len(at.error) == 1


def test_sma_demo_mode_runs():
    at = fresh()
    at.radio(key="strategy_kind").set_value("SMA crossover (demo)").run()
    assert not at.exception
    at.checkbox(key="confirm").check().run()
    at.button(key="btn_run").click().run()
    assert not at.exception
    markdown = " ".join(str(getattr(m, "value", "")) for m in at.markdown)
    assert "Trades" in markdown
