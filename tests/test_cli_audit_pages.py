import os

import pytest

from algobot.cli import main

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from algobot.data import generate_sample_data  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(argv, capsys):
    code = main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.fixture()
def small_data(tmp_path):
    path = tmp_path / "small.csv"
    generate_sample_data(days=15, seed=5).to_csv(path)
    return str(path)


def test_backtest_logs_variants_and_audit_uses_the_count(small_data, capsys):
    cfg = os.path.join(ROOT, "configs", "demo_rules.yaml")
    code, out, _ = run(["backtest", cfg, "--data", small_data, "--no-save"], capsys)
    assert code == 0 and "Variants tried on this data so far: 1" in out
    run(["backtest", os.path.join(ROOT, "configs", "demo_sma.yaml"), "--data", small_data, "--no-save"], capsys)
    code, out, _ = run(["experiments"], capsys)
    assert "2 run(s)" in out
    code, out, _ = run(["audit", cfg, "--data", small_data, "--random-runs", "10", "--mc-paths", "100"], capsys)
    assert "2 variant(s) tried on this data" in out and "REALITY CHECK" in out
    assert code == 1 and "NOT READY" in out                              # random data has no edge


def test_no_log_flag_and_manual_trials_override(small_data, capsys):
    cfg = os.path.join(ROOT, "configs", "demo_rules.yaml")
    _, out, _ = run(["backtest", cfg, "--data", small_data, "--no-save", "--no-log"], capsys)
    assert "Variants tried" not in out
    _, out, _ = run(["audit", cfg, "--data", small_data, "--trials", "50", "--random-runs", "10", "--mc-paths", "100"], capsys)
    assert "50 variant(s) tried" in out


def test_check_data_command(small_data, tmp_path, capsys):
    code, out, _ = run(["check-data", small_data], capsys)
    assert code == 0 and "No problems found" in out
    df = generate_sample_data(days=3, seed=1).drop(index=generate_sample_data(days=3, seed=1).index[[40, 41, 42]])
    bad = tmp_path / "bad.csv"
    df.to_csv(bad)
    code, out, _ = run(["check-data", str(bad)], capsys)
    assert code == 1 and "missing inside trading days" in out


def test_breakeven_and_ruin_commands(capsys):
    code, out, _ = run(["breakeven", "--spot", "24500", "--strike", "24500", "--type", "CE", "--days", "3",
                        "--iv", "14", "--hold", "1"], capsys)
    assert code == 0 and "must move up by" in out and "Theta per day" in out
    code, _, err = run(["breakeven", "--spot", "24500", "--strike", "24500", "--type", "CE", "--days", "0",
                        "--iv", "14", "--hold", "1"], capsys)
    assert code == 2 and "days_to_expiry" in err
    code, out, _ = run(["ruin", "--win-rate", "45", "--reward-r", "1.5", "--risk-pct", "10"], capsys)
    assert code == 0 and "Chance of losing 50%" in out
    code, _, err = run(["ruin", "--win-rate", "150", "--reward-r", "1.5", "--risk-pct", "10"], capsys)
    assert code == 2 and "win_rate" in err


def test_review_with_behaviour_options(tmp_path, capsys):
    db = str(tmp_path / "j.db")
    run(["journal", "add", "--db", db, "--instrument", "X", "--side", "BUY", "--qty", "65", "--entry", "100",
         "--stop", "90", "--opened-at", "2026-09-21 10:00"], capsys)
    run(["journal", "close", "1", "--db", db, "--exit", "70", "--closed-at", "2026-09-21 10:30"], capsys)
    _, out, _ = run(["review", "--db", db, "--max-loss-per-trade", "1000"], capsys)
    assert "Behaviour checks:" in out and "stop was moved or ignored" in out


# ------------------------------------------------------------------- pages
def page(name):
    at = AppTest.from_file(os.path.join(ROOT, "pages", name), default_timeout=90)
    return at


def test_reality_check_page_needs_a_backtest_first():
    at = page("6_Reality_check.py")
    at.run()
    assert not at.exception and any("Run a backtest on the Backtest page first" in i.value for i in at.info)


def test_reality_check_page_runs_the_audit_on_the_last_backtest():
    raw = {"name": "dashboard_run", "capital": 100000,
           "strategy": {"name": "sma_crossover", "params": {"fast": 10, "slow": 30}, "quantity": 10,
                        "allow_short": False, "stop_loss_pct": 0.5, "target_pct": 1.0}}
    at = page("6_Reality_check.py")
    at.session_state["last_raw"] = raw
    at.session_state["last_prices"] = generate_sample_data(days=12, seed=3)
    at.run()
    assert not at.exception
    at.slider(key="au_random").set_value(20).run()
    at.button(key="au_run").click().run()
    assert not at.exception
    assert len(at.error) >= 1                                            # the verdict banner
    assert any("NOT READY" in e.value for e in at.error)


def test_option_breakeven_and_ruin_page():
    at = page("4_Option_breakeven_and_ruin.py")
    at.run()
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert "Entry premium used" in labels and "Average result per trade (R)" in labels
    at.number_input(key="ru_risk").set_value(1.0).run()
    assert not at.exception
    at.number_input(key="be_days").set_value(0.1)
    at.number_input(key="be_hold").set_value(5.0)
    at.run()                                             # holding far longer than the option lives: must not crash
    assert not at.exception


def test_main_dashboard_now_logs_variants_and_hands_over_to_the_reality_check():
    at = AppTest.from_file(os.path.join(ROOT, "pages", "5_Backtest.py"), default_timeout=90)
    at.run()
    at.checkbox(key="confirm").check().run()
    at.button(key="btn_run").click().run()
    assert not at.exception
    assert at.session_state["variants_tried"] == 1 and "last_raw" in at.session_state
    assert any("Variants tried on this data so far: 1" in c.value for c in at.caption)


# ------------------------------------------------------------- test lab and practice room pages
def test_test_lab_page_runs_and_reports():
    at = page("7_Test_lab.py")
    at.run()
    assert not at.exception and any("demo strategy" in i.value for i in at.info)
    at.slider(key="lab_worlds").set_value(3)
    at.slider(key="lab_days").set_value(5)
    at.slider(key="lab_control").set_value(6)
    at.multiselect(key="lab_regimes").set_value(["trend", "chop"])
    at.button(key="lab_run").click().run()
    assert not at.exception
    assert len(at.dataframe) == 1
    assert any("Risk rules held" in s.value for s in at.success)
    assert any("Cheating test" in m.value for m in list(at.success) + list(at.error))


def test_test_lab_page_uses_the_strategy_from_the_last_backtest():
    raw = {"name": "dashboard_run", "capital": 100000,
           "strategy": {"name": "sma_crossover", "params": {"fast": 5, "slow": 20}, "quantity": 10,
                        "allow_short": False, "stop_loss_pct": 0.5, "target_pct": 1.0}}
    at = page("7_Test_lab.py")
    at.session_state["last_raw"] = raw
    at.run()
    assert not at.exception and any("last backtest" in i.value for i in at.info)


def start_practice(capital=100000, **inputs):
    at = page("3_Practice_room.py")
    at.run()
    at.number_input(key="pr_capital").set_value(capital)
    for key, value in inputs.items():
        at.number_input(key=key).set_value(value)
    at.button(key="pr_start").click().run()
    return at


def test_practice_room_full_session_and_the_market_stays_hidden_until_the_end():
    at = start_practice()
    assert not at.exception
    assert any("NIFTY (fake)" in md.value for md in at.markdown)                 # the ticker strip
    assert not any("The market was" in t.value for t in at.text)                 # hidden while you play
    at.button(key="pr_next").click().run()
    at.button(key="pr_buy").click().run()
    assert not at.exception and any("Bought" in s.value for s in at.success)
    at.button(key="pr_next12").click().run()
    if any(b.key == "pr_close" for b in at.button):                               # not already stopped out
        at.button(key="pr_close").click().run()
    at.button(key="pr_finish").click().run()
    assert not at.exception
    review = " ".join(t.value for t in at.text)
    assert "PRACTICE ROOM REVIEW" in review and "The market was" in review and "Spread and charges alone" in review


def test_practice_room_enforces_your_rules_unless_you_choose_to_break_them():
    at = start_practice(pr_maxtrades=1)
    at.button(key="pr_buy").click().run()
    at.button(key="pr_close").click().run()
    at.button(key="pr_buy").click().run()
    assert any("Blocked by your own rules" in e.value for e in at.error)
    at.checkbox(key="pr_override").check().run()
    at.button(key="pr_buy").click().run()
    assert not at.exception and any("broke your own rules" in w.value for w in at.warning)
    at.button(key="pr_finish").click().run()
    review = " ".join(t.value for t in at.text)
    assert "Times you broke your own rules on purpose: 1" in review and "at most 1" in review


def test_practice_room_explains_when_you_cannot_afford_the_trade():
    at = start_practice(capital=1000)
    at.button(key="pr_buy").click().run()
    assert not at.exception and any("Not enough money" in e.value for e in at.error)
