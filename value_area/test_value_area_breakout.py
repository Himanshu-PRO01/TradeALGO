import numpy as np
import pandas as pd
import pytest

from value_area_breakout import Params, run_backtest, summarize, value_area


def day_bars(date, rows, start="09:15"):
    idx = pd.date_range(f"{date} {start}", periods=len(rows), freq="15min")
    return pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close", "volume"])


def yesterday():
    # 25 bars; volume piles up between 100 and 102 -> value area roughly 100..102
    rows = []
    for i in range(25):
        mid = 101 + (0.3 if i % 2 else -0.3)
        rows.append((mid, mid + 0.4, mid - 0.4, mid, 1000))
    rows[0] = (101, 104, 98, 101, 200)      # thin wicks far from the value
    return day_bars("2025-03-03", rows)


def test_value_area_contains_70_percent_and_brackets_the_poc():
    val, poc, vah = value_area(yesterday(), 0.70, tick=0.1)
    assert val <= poc <= vah
    assert 100 <= val <= 101.2 and 101 <= vah <= 102.5
    assert (vah - val) < (104 - 98)           # narrower than the full range


def test_value_area_single_price():
    df = day_bars("2025-03-03", [(50, 50, 50, 50, 100)] * 4)
    val, poc, vah = value_area(df, 0.70, tick=0.05)
    assert val <= 50 <= vah


def build(signal_vol, make_after):
    y = yesterday()
    val, _, vah = value_area(y, 0.70, tick=0.1)
    inside = [(vah - 0.5, vah - 0.2, vah - 0.8, vah - 0.4, 1000)] * 3
    sig = [(vah - 0.4, vah + 0.6, vah - 0.6, vah + 0.4, signal_vol)]
    rows = inside + sig + make_after(vah)
    return pd.concat([y, day_bars("2025-03-04", rows)]), vah


P = Params(tick=0.1, low_volume_ratio=None, require_return_to_zone=True, vol_lookback_days=5,
           min_risk_pct=0.0, max_risk_pct=50, cost_bps_per_side=0, slippage_bps_per_side=0)


def test_target_hit_is_plus_two_r():
    # entry = next open (vah+0.4); stop = signal low (vah-0.6) -> risk 1.0, target = vah+2.4
    df, vah = build(500, lambda v: [(v + 0.4, v + 1.0, v + 0.2, v + 0.9, 800), (v + 1.0, v + 3.0, v + 0.9, v + 2.8, 800)])
    t = run_backtest(df, P)
    assert len(t) == 1 and t.loc[0, "reason"] == "target"
    assert t.loc[0, "entry"] == pytest.approx(vah + 0.4)
    assert t.loc[0, "stop"] == pytest.approx(vah - 0.6)
    assert t.loc[0, "r_multiple"] == pytest.approx(2.0)


def test_stop_checked_first_when_a_bar_touches_both():
    df, vah = build(500, lambda v: [(v + 0.4, v + 3.0, v - 0.7, v + 1.0, 800)])
    t = run_backtest(df, P)
    assert t.loc[0, "reason"] == "stop" and t.loc[0, "r_multiple"] == pytest.approx(-1.0)


def test_low_volume_filter_blocks_high_volume_breakouts():
    after = lambda v: [(v + 0.4, v + 1.0, v + 0.2, v + 0.9, 800), (v + 1.0, v + 3.0, v + 0.9, v + 2.8, 800)]
    strict = Params(**{**P.__dict__, "low_volume_ratio": 0.8})
    # needs a history of earlier sessions to build the same-time volume baseline, so seed 6 quiet days
    days = [yesterday().shift(freq=pd.Timedelta(days=-k)) for k in range(7, 1, -1)]
    df, _ = build(5000, after)                       # very high volume on the signal candle
    t = run_backtest(pd.concat(days + [df]).sort_index(), strict)
    assert t.empty
    quiet, _ = build(300, after)                     # control: same setup, quiet signal candle -> trades
    assert len(run_backtest(pd.concat(days + [quiet]).sort_index(), strict)) == 1


def test_no_trade_without_return_to_zone():
    y = yesterday(); _, _, vah = value_area(y, 0.70, tick=0.1)
    today = day_bars("2025-03-04", [(vah + 1, vah + 2, vah + 0.8, vah + 1.5, 500),
                                    (vah + 1.5, vah + 2.5, vah + 1.4, vah + 2, 500),
                                    (vah + 2, vah + 3, vah + 1.9, vah + 2.5, 500)])
    assert run_backtest(pd.concat([y, today]), P).empty            # gap-up day never revisits the zone
    loose = Params(**{**P.__dict__, "require_return_to_zone": False, "require_fresh_cross": False})
    assert len(run_backtest(pd.concat([y, today]), loose)) == 1


def test_levels_use_only_the_previous_day():
    df, vah = build(500, lambda v: [(v + 0.4, v + 1.0, v + 0.2, v + 0.9, 800), (v + 1.0, v + 3.0, v + 0.9, v + 2.8, 800)])
    t1 = run_backtest(df, P)
    df2 = df.copy()
    df2.loc[df2.index >= "2025-03-04 11:00", ["high", "low", "close"]] *= 1.5   # change the end of today
    t2 = run_backtest(df2, P)
    assert t1.loc[0, "vah"] == pytest.approx(t2.loc[0, "vah"])


def test_index_data_without_volume_is_refused():
    y = yesterday().assign(volume=0.0)
    with pytest.raises(ValueError):
        run_backtest(y, P)


def test_summarize_empty():
    assert summarize(pd.DataFrame()) == {"trades": 0}
