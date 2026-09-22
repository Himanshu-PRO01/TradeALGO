import pandas as pd
import pytest

from algobot.costs import CostModel
from helpers import flat_rows, make_bars, make_cfg, run


def test_decision_is_filled_at_next_bar_open_not_signal_close():
    rows = [
        (100, 100.5, 99.5, 100),     # 0: BUY decided at this close (100)
        (101, 102, 100.8, 101.5),    # 1: filled at THIS open (101)
        (101.5, 102, 101, 101.8),    # 2: SELL decided at this close
        (103, 103.5, 102.5, 103),    # 3: exit filled at THIS open (103)
    ] + flat_rows(4, 103)
    df = make_bars(rows)
    res = run(df, {0: "BUY", 2: "SELL"})
    t = res.trades.iloc[0]
    assert t.entry_price == 101 and t.exit_price == 103
    assert t.entry_time == df.index[1] and t.exit_time == df.index[3]
    assert t.net_pnl == pytest.approx(20.0)


def test_stop_loss_fills_at_stop_price():
    rows = [(100, 100.5, 99.5, 100), (100, 100.5, 98.5, 99.5)] + flat_rows(4, 99.5)
    res = run(make_bars(rows), {0: "BUY"}, strategy={"stop_loss_pct": 1.0})
    t = res.trades.iloc[0]
    assert t.exit_reason == "stop"
    assert t.exit_price == pytest.approx(99.0)
    assert t.net_pnl == pytest.approx(-10.0)


def test_gap_through_stop_fills_at_the_worse_open():
    rows = [
        (100, 100.5, 99.5, 100),
        (100, 100.4, 99.5, 100),
        (97, 98, 96.5, 97.5),        # opens below the 99 stop
    ] + flat_rows(3, 97.5)
    res = run(make_bars(rows), {0: "BUY"}, strategy={"stop_loss_pct": 1.0})
    t = res.trades.iloc[0]
    assert t.exit_reason == "stop"
    assert t.exit_price == pytest.approx(97.0)
    assert t.net_pnl == pytest.approx(-30.0)


def test_stop_wins_when_stop_and_target_are_both_inside_one_bar():
    rows = [(100, 100.5, 99.5, 100), (100, 101.5, 98.5, 100)] + flat_rows(3)
    res = run(make_bars(rows), {0: "BUY"}, strategy={"stop_loss_pct": 1.0, "target_pct": 1.0})
    assert res.trades.iloc[0].exit_reason == "stop"


def test_target_has_no_slippage_but_stop_does():
    rows = [(100, 100.5, 99.5, 100), (100, 102, 99.6, 101)] + flat_rows(3, 101)
    res = run(make_bars(rows), {0: "BUY"}, strategy={"target_pct": 1.0}, costs={"slippage_bps": 10})
    t = res.trades.iloc[0]
    entry = 100 * 1.001
    assert t.entry_price == pytest.approx(entry)
    assert t.exit_reason == "target"
    assert t.exit_price == pytest.approx(entry * 1.01)      # no slippage on the limit exit

    rows = [(100, 100.5, 99.5, 100), (100, 100.2, 98.0, 99)] + flat_rows(3, 99)
    res = run(make_bars(rows), {0: "BUY"}, strategy={"stop_loss_pct": 1.0}, costs={"slippage_bps": 10})
    t = res.trades.iloc[0]
    stop = entry * 0.99
    assert t.exit_reason == "stop"
    assert t.exit_price == pytest.approx(stop * 0.999)      # stop exit pays slippage


def test_short_trade_profit():
    rows = [(100, 100.5, 99.5, 100), (100, 100.4, 99.6, 100),
            (99, 99.5, 98.5, 99), (97, 97.5, 96.5, 97)] + flat_rows(3, 97)
    res = run(make_bars(rows), {0: "SELL", 2: "BUY"}, strategy={"allow_short": True})
    t = res.trades.iloc[0]
    assert t.side == "SHORT"
    assert t.net_pnl == pytest.approx(30.0)


def test_short_signal_ignored_when_shorting_not_allowed():
    res = run(make_bars(flat_rows(6)), {0: "SELL"})
    assert res.trades.empty


def test_costs_are_charged_on_both_sides():
    rows = [(100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100),
            (102, 102.5, 101.5, 102), (102, 102.5, 101.5, 102)] + flat_rows(3, 102)
    costs = dict(brokerage_pct=0.03, brokerage_cap=20, stt_sell_pct=0.025, exchange_txn_pct=0.003,
                 sebi_fee_pct=0.0001, stamp_buy_pct=0.003, gst_pct=18)
    res = run(make_bars(rows), {0: "BUY", 1: "SELL"}, costs=costs)
    t = res.trades.iloc[0]
    cm = CostModel(**{**dict(slippage_bps=0), **costs})
    expected = cm.order_charges("BUY", 100, 10) + cm.order_charges("SELL", 102, 10)
    assert t.gross_pnl == pytest.approx(20.0)
    assert t.costs == pytest.approx(expected)
    assert t.net_pnl == pytest.approx(20.0 - expected)


def test_square_off_closes_at_the_open_of_the_square_off_bar():
    rows = flat_rows(8)                      # 14:50 .. 15:25
    df = make_bars(rows, start="14:50")
    res = run(df, {0: "BUY"})
    t = res.trades.iloc[0]
    assert t.exit_reason == "square_off"
    assert t.exit_time.strftime("%H:%M") == "15:15"


def test_new_entry_after_last_entry_time_is_blocked():
    df = make_bars(flat_rows(8), start="14:50")   # 15:00 bar decides, 15:05 would fill
    res = run(df, {2: "BUY"})
    assert res.trades.empty
    assert res.rejections == {"after_last_entry_time": 1}


def test_max_trades_per_day():
    df = make_bars(flat_rows(10))
    res = run(df, {0: "BUY", 2: "SELL", 4: "BUY", 6: "SELL"}, risk={"max_trades_per_day": 1})
    assert len(res.trades) == 1
    assert res.rejections == {"max_trades_per_day": 1}


def test_position_size_limit():
    df = make_bars(flat_rows(6))
    res = run(df, {0: "BUY"}, risk={"max_position_value": 500})   # 10 x 100 = 1000 > 500
    assert res.trades.empty and res.rejections == {"position_too_large": 1}


def test_kill_switch_exits_and_blocks_the_day_then_resets_next_day():
    day1 = [
        (100, 100.5, 99.5, 100),      # 0: BUY decided
        (100, 100.2, 99.0, 99.5),     # 1: entered at 100
        (99.5, 99.5, 89.5, 90),       # 2: open loss -100 breaches the limit of 50
        (90, 91, 89, 90.5),           # 3: forced exit at 90 open
        (90.5, 91, 90, 90.8),         # 4: strategy must NOT be consulted (halted)
    ] + flat_rows(5, 90.8)
    day2 = [
        (91, 91.5, 90.5, 91),         # 10: BUY decided
        (91, 92, 90.9, 91.5),         # 11: entered at 91 (halt lifted on the new day)
    ] + flat_rows(4, 91.5)
    df = pd.concat([make_bars(day1, day="2025-01-06"), make_bars(day2, day="2025-01-07")])
    res = run(df, {0: "BUY", 4: "BUY", 10: "BUY"}, risk={"max_daily_loss": 50})
    assert len(res.trades) == 2
    first, second = res.trades.iloc[0], res.trades.iloc[1]
    assert first.exit_reason == "kill_switch" and first.net_pnl == pytest.approx(-100.0)
    assert second.entry_time.date().isoformat() == "2025-01-07"
    assert len(res.events) == 1 and "daily loss limit" in res.events[0]


def test_decision_on_last_bar_of_day_is_not_carried_overnight():
    day1 = flat_rows(3)
    day2 = flat_rows(3)
    df = pd.concat([make_bars(day1, day="2025-01-06"), make_bars(day2, day="2025-01-07")])
    res = run(df, {2: "BUY"})              # decided on the last bar of day 1
    assert res.trades.empty


def test_open_position_is_closed_if_a_days_data_ends_early():
    day1 = [(100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100),
            (100, 100.5, 99.5, 100), (100, 100.5, 99.5, 101)]   # ends 09:30, last close 101
    day2 = flat_rows(3)
    df = pd.concat([make_bars(day1, day="2025-01-06"), make_bars(day2, day="2025-01-07")])
    res = run(df, {0: "BUY"})
    t = res.trades.iloc[0]
    assert t.exit_reason == "day_ended_before_square_off"
    assert t.exit_price == pytest.approx(101.0)


def test_accounting_identity_end_equity_equals_capital_plus_trade_pnl():
    rows = [(100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100),
            (102, 102.5, 101.5, 102), (102, 102.5, 101.5, 101)] + flat_rows(6, 101)
    res = run(make_bars(rows), {0: "BUY", 2: "SELL", 4: "BUY"},
              costs={"brokerage_pct": 0.03, "brokerage_cap": 20, "slippage_bps": 5, "stt_sell_pct": 0.025})
    assert res.equity.iloc[-1] == pytest.approx(100000 + res.trades.net_pnl.sum())
    assert res.metrics["net_pnl"] == pytest.approx(res.trades.net_pnl.sum())
