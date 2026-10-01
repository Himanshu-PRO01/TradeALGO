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


def own_rules(at):
    """Switch the page to 'Write my own rules', where the rules box and the confirm gate live."""
    at.radio(key="strategy_kind").set_value("Write my own rules (advanced)").run()
    return at


def texts(elements):
    return " ".join(str(getattr(e, "value", "")) for e in elements)


def test_dashboard_starts_without_errors_and_shows_the_plain_english_readback():
    at = fresh()
    assert not at.exception
    assert any("Buy (go long) when" in t.value for t in at.text)
    assert any("Short selling is NOT allowed" in t.value for t in at.text)
    # Ready-made ideas need no confirmation, so the run button is ready straight away.
    assert not at.button(key="btn_run").disabled


def test_own_rules_stay_locked_until_the_trader_confirms_the_readback():
    at = own_rules(fresh())
    assert not at.exception
    assert at.button(key="btn_run").disabled
    assert at.button(key="btn_lookahead").disabled
    at.checkbox(key="confirm").check().run()
    assert not at.button(key="btn_run").disabled


def test_a_backtest_shows_results_without_any_extra_ticking():
    at = fresh()
    assert not at.button(key="btn_run").disabled
    at.button(key="btn_run").click().run()
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert "Costs paid (Rs)" in labels and "Trades" in labels
    assert any("random sample data" in w.value for w in at.warning)   # honesty banner


def test_lookahead_button_reports_green_checks_for_honest_rules():
    at = fresh()
    at.button(key="btn_lookahead").click().run()
    assert not at.exception
    assert len(at.success) == 3 and len(at.error) == 0


def test_a_bad_rule_gives_a_friendly_error_not_a_crash():
    at = own_rules(fresh())
    at.text_area(key="rules_text").set_value('entry_long: "close > nonexistent_column"').run()
    assert not at.exception
    assert any("could not be evaluated" in e.value for e in at.error)


def test_dangerous_rule_syntax_is_refused():
    at = own_rules(fresh())
    at.text_area(key="rules_text").set_value('entry_long: "close.shift(-1) > close"').run()
    assert not at.exception
    assert any("not allowed" in e.value for e in at.error)


def test_bad_time_and_bad_yaml_are_reported():
    at = fresh()
    at.text_input(key="t_start").set_value("25:99").run()
    assert not at.exception
    assert any("must be a time" in e.value for e in at.error)

    at = own_rules(fresh())
    at.text_area(key="rules_text").set_value("entry_long: [unclosed").run()
    assert not at.exception
    assert len(at.error) == 1


def test_sma_demo_mode_runs():
    at = fresh()
    at.radio(key="strategy_kind").set_value("Moving-average crossover (ready-made)").run()
    assert not at.exception
    at.button(key="btn_run").click().run()
    assert not at.exception
    assert any(m.label == "Trades" for m in at.metric)


def test_new_era_strategy_runs_instead_of_crashing():
    at = fresh()
    at.radio(key="strategy_kind").set_value("New Era Strategy 1.0").run()
    assert not at.exception
    at.button(key="btn_run").click().run()
    assert not at.exception
    assert any(m.label == "Trades" for m in at.metric)
def test_zero_trades_because_of_position_limit_explains_the_real_cause(monkeypatch):
    """High-priced data (like Nifty ~ 23,000) with the default 10 units / Rs 50,000 limit blocks every entry.
    The page must say so instead of claiming the rule never triggered."""
    import algobot.data as data
    real = data.generate_sample_data(days=30, seed=1)
    pricey = real.copy()
    pricey[["open", "high", "low", "close"]] = pricey[["open", "high", "low", "close"]] * 23.0
    monkeypatch.setattr(data, "generate_sample_data", lambda days=60, seed=42, **k: pricey.iloc[: int(days) * 75].copy())
    at = fresh()
    at.slider(key="sample_days").set_value(30).run()
    at.button(key="btn_run").click().run()
    assert not at.exception
    assert any("bigger than your limit" in w.value for w in at.warning)
    assert not any("never triggered" in i.value for i in at.info)

def test_market_desk_module_is_valid_python():
    """Catch accidental syntax regressions before Streamlit Cloud boots the app."""
    import ast

    with open(os.path.join(ROOT, "Trading_Desk.py"), encoding="utf-8") as fh:
        ast.parse(fh.read(), filename="Trading_Desk.py")
