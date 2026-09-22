import pytest

from algobot.cli import main


@pytest.fixture()
def db(tmp_path):
    return str(tmp_path / "j.db")


def run(argv, capsys):
    code = main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err


def test_size_command(capsys):
    code, out, _ = run(["size", "--max-loss", "1000", "--entry", "100", "--stop", "85", "--capital", "10000"], capsys)
    assert code == 0 and "Lots allowed:        1" in out and "10% of capital" in out


def test_size_command_reports_bad_input_as_a_friendly_problem(capsys):
    code, _, err = run(["size", "--max-loss", "1000", "--entry", "100", "--stop", "120"], capsys)
    assert code == 2 and "Problem:" in err and "BELOW" in err


def test_journal_report_and_review_flow(db, capsys):
    assert run(["journal", "add", "--db", db, "--instrument", "NIFTY 24500 CE", "--side", "BUY", "--qty", "65",
                "--entry", "100", "--stop", "85", "--setup", "breakout", "--opened-at", "2026-09-21 10:00"], capsys)[0] == 0
    code, out, _ = run(["journal", "close", "1", "--db", db, "--exit", "90", "--charges", "50",
                        "--closed-at", "2026-09-21 12:00", "--lessons", "entered too early"], capsys)
    assert code == 0 and "Net Rs -700.00" in out
    code, out, _ = run(["report", "--db", db, "--date", "2026-09-21", "--max-loss-per-trade", "500"], capsys)
    assert code == 0 and "Net for the day: Rs -700.00" in out and "more than the per-trade limit" in out
    code, out, _ = run(["review", "--db", db], capsys)
    assert code == 0 and "1 closed trade" in out and "Win rate:           0%" in out
    code, out, _ = run(["journal", "list", "--db", db], capsys)
    assert "NIFTY 24500 CE" in out


def test_html_report_file_is_written(db, tmp_path, capsys):
    run(["journal", "add", "--db", db, "--instrument", "X", "--side", "BUY", "--qty", "1", "--entry", "10",
         "--opened-at", "2026-09-21 10:00"], capsys)
    run(["journal", "close", "1", "--db", db, "--exit", "12", "--closed-at", "2026-09-21 11:00"], capsys)
    target = tmp_path / "r.html"
    code, _, _ = run(["report", "--db", db, "--date", "2026-09-21", "--html", str(target)], capsys)
    assert code == 0 and "<h1>Daily P&amp;L report" in target.read_text()


def test_bad_inputs_are_friendly(db, capsys):
    code, _, err = run(["journal", "close", "42", "--db", db, "--exit", "10"], capsys)
    assert code == 2 and "no trade with id 42" in err
    code, _, err = run(["report", "--db", db, "--date", "not-a-date"], capsys)
    assert code == 2 and "--date must look like" in err
    code, _, err = run(["journal", "add", "--db", db, "--instrument", "X", "--side", "BUY", "--qty", "1",
                        "--entry", "10", "--stop", "12"], capsys)
    assert code == 2 and "BELOW" in err


def test_missing_stop_is_called_out(db, capsys):
    _, out, _ = run(["journal", "add", "--db", db, "--instrument", "X", "--side", "BUY", "--qty", "1",
                     "--entry", "10"], capsys)
    assert "no stop-loss was recorded" in out
