import datetime as dt

import pytest

from algobot.journal import (Journal, JournalError, build_daily_report, format_daily_report_html,
                             format_daily_report_text, format_review, review_stats)

DAY = dt.date(2026, 9, 21)


def j_with_trades():
    j = Journal()
    a = j.add_trade("NIFTY 24500 CE", "BUY", 65, 100, opened_at="2026-09-21 10:00", stop_price=85,
                    setup="resistance breakout", notes="broke prev high")
    j.close_trade(a, 120, closed_at="2026-09-21 13:00", charges=60, lessons="waited for the close")
    b = j.add_trade("NIFTY 24400 PE", "BUY", 65, 90, opened_at="2026-09-21 14:00", stop_price=75,
                    setup="support breakdown")
    j.close_trade(b, 72, closed_at="2026-09-21 14:40", charges=55)
    return j


def test_buy_trade_pnl_charges_and_r_multiple():
    j = Journal()
    i = j.add_trade("NIFTY 24500 CE", "buy", 65, 100, opened_at="2026-09-21 10:00", stop_price=85)
    t = j.close_trade(i, 120, closed_at="2026-09-21 12:00", charges=60)
    assert t.gross_pnl == pytest.approx(1300)                 # 20 x 65
    assert t.net_pnl == pytest.approx(1240)
    assert t.risk_amount == pytest.approx(975)               # 15 x 65
    assert t.r_multiple == pytest.approx(1240 / 975)


def test_sell_trade_pnl_is_reversed():
    j = Journal()
    i = j.add_trade("NIFTY FUT", "SELL", 65, 24000, opened_at="2026-09-21 10:00", stop_price=24050)
    t = j.close_trade(i, 23900, closed_at="2026-09-21 11:00")
    assert t.gross_pnl == pytest.approx(6500)


def test_open_trade_has_no_pnl_yet():
    j = Journal()
    t = j.get(j.add_trade("NIFTY 24500 CE", "BUY", 65, 100))
    assert not t.is_closed and t.net_pnl is None and t.r_multiple is None


@pytest.mark.parametrize("kwargs", [
    dict(instrument="", side="BUY", qty=65, entry_price=100),
    dict(instrument="X", side="HOLD", qty=65, entry_price=100),
    dict(instrument="X", side="BUY", qty=0, entry_price=100),
    dict(instrument="X", side="BUY", qty=65, entry_price=0),
    dict(instrument="X", side="BUY", qty=65, entry_price=100, stop_price=110),   # stop above a buy
    dict(instrument="X", side="SELL", qty=65, entry_price=100, stop_price=90),   # stop below a sell
    dict(instrument="X", side="BUY", qty=65, entry_price=100, opened_at="yesterday-ish"),
])
def test_bad_trade_input_is_rejected(kwargs):
    with pytest.raises(JournalError):
        Journal().add_trade(**kwargs)


def test_cannot_close_twice_or_close_a_missing_trade_or_close_before_open():
    j = Journal()
    i = j.add_trade("X", "BUY", 1, 100, opened_at="2026-09-21 10:00")
    with pytest.raises(JournalError, match="before"):
        j.close_trade(i, 101, closed_at="2026-09-21 09:00")
    j.close_trade(i, 101, closed_at="2026-09-21 11:00")
    with pytest.raises(JournalError, match="already closed"):
        j.close_trade(i, 102)
    with pytest.raises(JournalError, match="no trade"):
        j.close_trade(999, 100)


def test_closed_between_uses_the_closing_date():
    j = Journal()
    i = j.add_trade("X", "BUY", 1, 100, opened_at="2026-09-18 10:00")
    j.close_trade(i, 105, closed_at="2026-09-21 10:00")
    assert len(j.closed_between(DAY, DAY)) == 1
    assert j.closed_between(dt.date(2026, 9, 18), dt.date(2026, 9, 20)) == []


def test_daily_report_totals():
    rep = build_daily_report(j_with_trades(), DAY, capital=10000)
    assert len(rep["trades"]) == 2 and rep["wins"] == 1 and rep["losses"] == 1
    assert rep["gross"] == pytest.approx(1300 - 1170)         # +1300 and -1170
    assert rep["charges"] == pytest.approx(115)
    assert rep["net"] == pytest.approx(130 - 115)
    text = format_daily_report_text(rep)
    assert "DAILY P&L REPORT" in text and "Net for the day: Rs 15.00" in text and "+0.15%" in text
    assert "waited for the close" in text


def test_report_flags_broken_rules():
    j = Journal()
    a = j.add_trade("X", "BUY", 65, 100, opened_at="2026-09-21 10:00")                       # no stop recorded
    j.close_trade(a, 80, closed_at="2026-09-21 11:00", charges=50)                             # -1,350
    b = j.add_trade("Y", "BUY", 65, 100, opened_at="2026-09-21 12:00", stop_price=90)
    j.close_trade(b, 95, closed_at="2026-09-21 13:00")
    c = j.add_trade("Z", "BUY", 65, 100, opened_at="2026-09-21 13:30", stop_price=90)
    j.close_trade(c, 99, closed_at="2026-09-21 14:00")
    j.add_trade("OPEN", "BUY", 65, 100, opened_at="2026-09-21 14:10")                          # open, no stop
    rep = build_daily_report(j, DAY, max_loss_per_trade=1000, max_daily_loss=1500, max_trades_per_day=2)
    text = " | ".join(rep["flags"])
    assert "Trade #1 lost Rs 1,350.00" in text
    assert "Trade #1 has no stop-loss recorded" in text
    assert "beyond the daily limit" in text
    assert "3 trades were closed today" in text
    assert "Open trade #4" in text and "no stop-loss" in text


def test_html_report_escapes_user_text():
    j = Journal()
    i = j.add_trade("<script>alert(1)</script>", "BUY", 1, 100, opened_at="2026-09-21 10:00",
                    notes="<b>bold</b>")
    j.close_trade(i, 101, closed_at="2026-09-21 11:00", lessons="<img src=x>")
    page = format_daily_report_html(build_daily_report(j, DAY))
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page
    assert "<img src=x>" not in page and "&lt;img src=x&gt;" in page


def test_report_for_a_day_with_no_trades():
    rep = build_daily_report(Journal(), DAY)
    assert "No trades were closed today." in format_daily_report_text(rep)
    assert "No trades were closed today." in format_daily_report_html(rep)


def test_review_statistics_on_known_trades():
    j = Journal()
    for entry, exit_, stop, setup in [(100, 110, 90, "breakout"), (100, 96, 90, "breakout"), (100, 95, 90, "reversal"),
                                      (100, 130, None, "breakout")]:
        i = j.add_trade("X", "BUY", 10, entry, opened_at="2026-09-21 10:00", stop_price=stop, setup=setup)
        j.close_trade(i, exit_, closed_at="2026-09-21 11:00")
    s = review_stats(j.all_trades())
    assert s["trades"] == 4 and s["net"] == pytest.approx(100 - 40 - 50 + 300)
    assert s["win_rate_pct"] == pytest.approx(50)
    assert s["profit_factor"] == pytest.approx(400 / 90)
    assert s["max_losing_streak"] == 2 and s["without_stop"] == 1
    assert s["r_trades"] == 3 and s["avg_r"] == pytest.approx((1.0 + -0.4 + -0.5) / 3)
    assert s["by_setup"]["breakout"] == (3, 100 - 40 + 300)
    text = format_review(s)
    assert "small sample" in text and "breakout: 3 trade(s)" in text


def test_review_with_no_trades():
    assert "No closed trades" in format_review(review_stats([]))


def test_journal_persists_in_a_file(tmp_path):
    path = str(tmp_path / "j.db")
    j = Journal(path)
    j.add_trade("X", "BUY", 1, 100, opened_at="2026-09-21 10:00")
    j.close_db()
    again = Journal(path)
    assert len(again.all_trades()) == 1


# ---------------------------------------------------------------- behaviour checks
from algobot.journal import behavior_flags  # noqa: E402


def test_behaviour_checks_catch_the_habits_that_drain_small_accounts():
    j = Journal()

    def trade(opened, closed, entry, exit_, stop=None, qty=65):
        i = j.add_trade("NIFTY X", "BUY", qty, entry, opened_at=opened, stop_price=stop)
        j.close_trade(i, exit_, closed_at=closed)
        return i

    a = trade("2026-09-21 10:00", "2026-09-21 10:30", 100, 70, stop=90)       # planned 650, lost 1,950 = 3x
    b = trade("2026-09-21 10:38", "2026-09-21 10:50", 100, 95, stop=90)       # opened 8 min after a loss
    c = trade("2026-09-21 11:30", "2026-09-21 11:40", 100, 99, stop=90)
    flags = " | ".join(behavior_flags(j.all_trades(), max_loss_per_trade=1000, max_trades_per_day=2,
                                       max_daily_loss=1500))
    assert f"Trade #{a} lost 3.0x" in flags and "stop was moved or ignored" in flags
    assert f"Trade #{a} lost Rs 1,950.00, beyond the per-trade limit" in flags
    assert f"Trade #{b} was opened 8 minutes after losing trade #{a}" in flags
    assert "3 trades were opened on 2026-09-21; the plan was at most 2." in flags
    assert f"Trade #{b} was opened after the daily loss limit" in flags and f"Trade #{c}" in flags


def test_behaviour_checks_flag_losers_held_longer_than_winners():
    j = Journal()
    for k in range(5):
        day = f"2026-09-{10 + k}"
        w = j.add_trade("X", "BUY", 1, 100, opened_at=f"{day} 10:00", stop_price=90)
        j.close_trade(w, 110, closed_at=f"{day} 10:20")                                 # winners: 20 minutes
        l = j.add_trade("X", "BUY", 1, 100, opened_at=f"{day} 12:00", stop_price=90)
        j.close_trade(l, 95, closed_at=f"{day} 14:00")                                  # losers: 120 minutes
    flags = " | ".join(behavior_flags(j.all_trades()))
    assert "held much longer than winning trades" in flags


def test_a_disciplined_journal_has_no_flags_and_review_says_so():
    j = Journal()
    i = j.add_trade("X", "BUY", 65, 100, opened_at="2026-09-21 10:00", stop_price=90)
    j.close_trade(i, 90, closed_at="2026-09-21 11:00")                                  # stop honoured exactly
    flags = behavior_flags(j.all_trades(), max_loss_per_trade=1000, max_trades_per_day=2, max_daily_loss=1500)
    assert flags == []
    text = format_review(review_stats(j.all_trades()), flags)
    assert "Behaviour checks:" in text and "No rule breaks found." in text
    assert "Behaviour checks" not in format_review(review_stats(j.all_trades()))        # only when asked


def test_a_journal_kept_across_dashboard_reruns_can_be_used_from_another_thread():
    import threading
    j = Journal(":memory:", check_same_thread=False)
    j.add_trade("X", "BUY", 1, 100, opened_at="2026-09-21 10:00")
    seen = []
    worker = threading.Thread(target=lambda: seen.append(len(j.all_trades())))
    worker.start()
    worker.join()
    assert seen == [1]
    strict = Journal(":memory:")
    errors = []

    def poke():
        try:
            strict.all_trades()
        except Exception as exc:                       # sqlite3.ProgrammingError
            errors.append(type(exc).__name__)
    other = threading.Thread(target=poke)
    other.start()
    other.join()
    assert errors == ["ProgrammingError"]              # the default stays strict
