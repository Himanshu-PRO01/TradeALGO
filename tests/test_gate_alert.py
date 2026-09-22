import datetime as dt
import os

import pandas as pd
import pytest

from algobot import cli
from algobot.cli import main
from algobot.gate import build_alert, check_gate
from algobot.journal import Journal

DAY = dt.date(2026, 9, 21)


def journal_with_a_losing_morning():
    j = Journal()
    i = j.add_trade("NIFTY 24500 CE", "BUY", 65, 100, opened_at="2026-09-21 09:30", stop_price=85)
    j.close_trade(i, 85, closed_at="2026-09-21 10:15", charges=25)              # -1,000
    return j


def test_gate_is_open_on_a_fresh_day_and_reports_the_day_so_far():
    gate = check_gate(Journal(), DAY, max_trades_per_day=2, max_daily_loss=1500)
    assert gate.allowed and gate.trades_opened_today == 0 and gate.net_pnl_today == 0


def test_gate_blocks_after_the_trade_limit_or_the_loss_limit():
    j = journal_with_a_losing_morning()
    assert check_gate(j, DAY, max_trades_per_day=2, max_daily_loss=1500).allowed        # 1 trade, -1,000
    limit = check_gate(j, DAY, max_trades_per_day=1)
    assert not limit.allowed and "already opened today" in limit.reasons[0]
    loss = check_gate(j, DAY, max_daily_loss=1000)
    assert not loss.allowed and "daily loss limit of Rs 1,000 has been reached" in loss.reasons[0]
    assert check_gate(j, dt.date(2026, 9, 22), max_trades_per_day=1, max_daily_loss=1000).allowed   # a new day resets


def test_alert_text_carries_the_size_the_risk_and_the_verdict():
    gate = check_gate(Journal(), DAY, 2, 1500)
    text, takeable, size = build_alert("NIFTY 24500 CE", 100, 85, 65, 10000, 1000, gate, max_trades_per_day=2,
                                       max_daily_loss=1500)
    assert takeable and size.lots == 1
    assert "NIFTY 24500 CE: level alert" in text
    assert "Size: 1 lot(s) = 65 units" in text and "about Rs 975 (9.8% of capital)" in text
    assert "Check: OK by your own rules" in text and "Limits: max 2 trades, max loss Rs 1,500" in text


def test_alert_is_blocked_when_the_day_is_over_or_the_trade_does_not_fit():
    j = journal_with_a_losing_morning()
    gate = check_gate(j, DAY, max_daily_loss=1000)
    text, takeable, _ = build_alert("NIFTY 24500 CE", 100, 85, 65, 10000, 1000, gate, max_daily_loss=1000)
    assert not takeable and "Check: BLOCKED" in text and "No more trades today" in text
    wide = check_gate(Journal(), DAY)
    text, takeable, size = build_alert("NIFTY 24500 CE", 100, 60, 65, 10000, 1000, wide)
    assert not takeable and size.lots == 0 and "does not fit your rules" in text and "BLOCKED" in text


# ------------------------------------------------------------------ CLI wiring
class FakeClient:
    def __init__(self):
        self.sent = []

    def lot_size(self, symbol, exchange):
        return 65

    def telegram_notify(self, username, message, wait_for_delivery=False):
        self.sent.append((username, message))

    def history(self, symbol, exchange, interval, start, end, source="api"):
        idx = pd.date_range(f"{start} 09:15", periods=75, freq="5min", name="datetime")
        return pd.DataFrame({"open": 100.0, "high": 100.5, "low": 99.5, "close": 100.2, "volume": 10.0}, index=idx)


@pytest.fixture()
def fake_client(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(cli, "_make_client", lambda: fake)
    return fake


def run(argv, capsys):
    code = main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err


def test_alert_command_sends_to_telegram_and_exits_zero_when_allowed(fake_client, tmp_path, capsys):
    db = str(tmp_path / "j.db")
    code, out, _ = run(["alert", "--db", db, "--instrument", "NIFTY 24500 CE", "--entry", "100", "--stop", "85",
                        "--capital", "10000", "--max-loss", "1000", "--symbol", "NIFTY25SEP2624500CE",
                        "--date", "2026-09-21", "--telegram-user", "brother"], capsys)
    assert code == 0 and "Lot size from OpenAlgo for NIFTY25SEP2624500CE: 65" in out
    assert fake_client.sent and fake_client.sent[0][0] == "brother" and "level alert" in fake_client.sent[0][1]
    assert "queued, not confirmed delivered" in out


def test_alert_command_exits_one_and_still_tells_him_when_blocked(fake_client, tmp_path, capsys):
    db = str(tmp_path / "j.db")
    j = Journal(db)
    i = j.add_trade("X", "BUY", 65, 100, opened_at="2026-09-21 09:30", stop_price=85)
    j.close_trade(i, 85, closed_at="2026-09-21 10:00")
    j.close_db()
    code, out, _ = run(["alert", "--db", db, "--instrument", "NIFTY 24500 CE", "--entry", "100", "--stop", "85",
                        "--capital", "10000", "--max-loss", "1000", "--max-daily-loss", "900", "--date", "2026-09-21",
                        "--telegram-user", "brother"], capsys)
    assert code == 1 and "BLOCKED" in out and "BLOCKED" in fake_client.sent[0][1]


def test_size_command_can_read_the_lot_size_from_openalgo(fake_client, capsys):
    code, out, _ = run(["size", "--max-loss", "1000", "--entry", "100", "--stop", "85", "--symbol", "NIFTY25SEP2624500CE"], capsys)
    assert code == 0 and "Lot size from OpenAlgo" in out and "(65 units, lot size 65)" in out


def test_fetch_history_command_writes_a_csv_our_tools_can_read(fake_client, tmp_path, capsys):
    out_file = tmp_path / "data" / "nifty.csv"
    code, out, _ = run(["fetch-history", "--symbol", "NIFTY", "--exchange", "NSE_INDEX", "--interval", "5m",
                        "--from", "2026-09-01", "--to", "2026-09-03", "--out", str(out_file)], capsys)
    assert code == 0 and out_file.exists() and "Saved" in out and "Data check" in out and "30 to 90 days" in out
    from algobot.data import load_csv
    assert len(load_csv(str(out_file))) == 75


def test_openalgo_problems_are_reported_as_friendly_errors(monkeypatch, capsys):
    monkeypatch.delenv("OPENALGO_API_KEY", raising=False)
    monkeypatch.setenv("ALGOBOT_NO_ENV", "1")
    code, _, err = run(["fetch-history", "--symbol", "NIFTY", "--exchange", "NSE_INDEX", "--interval", "5m",
                        "--from", "2026-09-01", "--to", "2026-09-03", "--out", "/tmp/never.csv"], capsys)
    assert code == 2 and "No OpenAlgo API key" in err
