"""Tests for the win/loss-streak and exposure additions to compute_metrics()."""
import pandas as pd

from algobot.metrics import compute_metrics


def _trades(net_pnls, minutes_held=30):
    """Build a minimal trades frame: one row per net_pnl, each `minutes_held`
    long, back-to-back starting 2025-01-06 09:15, so exposure is exact and
    checkable by hand."""
    rows = []
    start = pd.Timestamp("2025-01-06 09:15")
    for i, pnl in enumerate(net_pnls):
        entry = start + pd.Timedelta(minutes=i * minutes_held)
        exit_ = entry + pd.Timedelta(minutes=minutes_held)
        rows.append({
            "entry_time": entry, "exit_time": exit_, "side": "LONG", "qty": 1,
            "entry_price": 100.0, "exit_price": 100.0, "gross_pnl": pnl,
            "costs": 0.0, "net_pnl": pnl, "exit_reason": "signal",
        })
    return pd.DataFrame(rows)


def _flat_equity(span_minutes, capital=100000.0):
    idx = pd.date_range("2025-01-06 09:15", periods=2, freq=f"{span_minutes}min")
    return pd.Series([capital, capital], index=idx)


def test_win_streak_and_loss_streak_are_longest_consecutive_runs():
    # +,+,-,+,+,+,-,- -> longest win run 3, longest loss run 2
    trades = _trades([10, 5, -3, 8, 2, 9, -1, -4])
    m = compute_metrics(trades, _flat_equity(8 * 30), 100000.0)
    assert m["max_win_streak"] == 3
    assert m["max_loss_streak"] == 2


def test_zero_pnl_trade_counts_as_a_loss_for_streaks():
    # matches win_rate_pct's own win/loss split (net > 0 is the only way to "win")
    trades = _trades([5, 0, 5])
    m = compute_metrics(trades, _flat_equity(3 * 30), 100000.0)
    assert m["max_win_streak"] == 1
    assert m["max_loss_streak"] == 1


def test_no_trades_gives_zero_streaks_and_zero_exposure():
    empty = pd.DataFrame(columns=[
        "entry_time", "exit_time", "side", "qty", "entry_price", "exit_price",
        "gross_pnl", "costs", "net_pnl", "exit_reason",
    ])
    m = compute_metrics(empty, pd.Series(dtype=float), 100000.0)
    assert m["max_win_streak"] == 0
    assert m["max_loss_streak"] == 0
    assert m["exposure_pct"] == 0.0


def test_exposure_pct_is_held_time_over_total_span():
    # Two 30-minute trades back to back = 60 minutes held out of a 120-minute span = 50%.
    trades = _trades([10, 10], minutes_held=30)
    equity = _flat_equity(120)  # index spans 0..120 minutes
    m = compute_metrics(trades, equity, 100000.0)
    assert abs(m["exposure_pct"] - 50.0) < 1e-6


def test_exposure_pct_is_capped_at_100():
    # A single trade "held" for longer than the equity curve's own span (can
    # happen at the edges of a resampled/live window) must not report >100%.
    trades = _trades([10], minutes_held=500)
    equity = _flat_equity(120)
    m = compute_metrics(trades, equity, 100000.0)
    assert m["exposure_pct"] == 100.0
