import numpy as np
import pandas as pd
import pytest

from algobot.options import bs_price
from algobot.practice import (PracticeBlocked, PracticeError, PracticeSession, PracticeSettings,
                              format_practice_report)
from algobot.worlds import generate_world


def flat_market(days=2, price=24500.0, bars=75):
    idx = np.concatenate([pd.date_range(f"2025-01-{6 + d:02d} 09:15", periods=bars, freq="5min") for d in range(days)])
    return pd.DataFrame({"open": price, "high": price, "low": price, "close": price, "volume": 1000.0},
                        index=pd.DatetimeIndex(idx, name="datetime"))


def session(bars=None, **kw):
    settings = PracticeSettings(**{**dict(capital=100000.0, days_to_expiry=5.0, spread_points=0.6,
                                          charges_per_order=40.0), **kw})
    return PracticeSession(bars if bars is not None else flat_market(), settings, start_index=10)


def test_quotes_have_a_spread_and_the_atm_strike_is_rounded():
    s = session()
    bid, ask = s.quote("CE", 24500)
    assert ask - bid == pytest.approx(0.6) and bid > 0
    assert s.atm_strike() == 24500 and 24500 in s.strikes() and len(s.strikes()) == 11
    assert session(flat_market(price=24537.0)).atm_strike() == 24550


def test_time_decay_is_real_even_when_the_market_does_not_move():
    s = session()
    before = s.mid("CE", 24500)
    s.advance(60)                                              # five hours of a dead-flat market
    assert s.mid("CE", 24500) < before
    s.advance_to_day_end()
    s.next_bar()                                               # next morning
    assert s.mid("CE", 24500) < before - 5                     # a night and a day of decay


def test_a_flat_market_still_loses_money_to_spread_time_and_charges():
    s = session()
    info = s.buy("CE", 24500, 1)
    assert info["price"] == pytest.approx(s.quote("CE", 24500)[1]) and info["qty"] == 65
    s.advance(30)
    rec = s.close()
    assert rec["move"] == pytest.approx(0.0, abs=1e-6)          # price did not move at all
    assert rec["time"] < 0 and rec["spread"] < 0 and rec["charges"] == pytest.approx(-80.0)
    assert rec["net"] < 0
    assert rec["move"] + rec["time"] + rec["spread"] + rec["charges"] == pytest.approx(rec["net"])
    assert s.cash == pytest.approx(100000 + rec["net"])


def test_a_rally_pays_a_call_and_the_split_shows_the_market_move():
    bars = flat_market()
    bars.iloc[30:, bars.columns.get_indexer(["open", "high", "low", "close"])] = 24700.0       # +200 points
    s = session(bars)
    s.buy("CE", 24500, 1)
    s.advance(25)
    rec = s.close()
    assert rec["net"] > 0 and rec["move"] > 5000
    assert rec["move"] + rec["time"] + rec["spread"] + rec["charges"] == pytest.approx(rec["net"])


def test_stop_inside_a_bar_fills_at_the_stop_and_a_gap_fills_worse():
    bars = flat_market()
    ask = session(bars).quote("CE", 24500)[1]
    stop = round(ask - 20, 2)
    # a dip inside one bar: low falls, open and close do not
    dip = bars.copy()
    dip.iloc[12, dip.columns.get_loc("low")] = 24380.0
    s = session(dip)
    s.buy("CE", 24500, 1, stop_premium=stop)
    s.advance(3)
    assert s.position is None and s.closed[0]["reason"] == "stop" and s.closed[0]["exit_price"] == pytest.approx(stop)
    assert s.closed[0]["move"] + s.closed[0]["time"] + s.closed[0]["spread"] + s.closed[0]["charges"] == \
        pytest.approx(s.closed[0]["net"], abs=1e-6)
    # a gap: the market opens far below the stop
    gap = bars.copy()
    gap.iloc[12:, gap.columns.get_indexer(["open", "high", "low", "close"])] = 24300.0
    g = session(gap)
    g.buy("CE", 24500, 1, stop_premium=stop)
    g.advance(3)
    assert g.closed[0]["reason"] == "stop (gapped)" and g.closed[0]["exit_price"] < stop - 1


def test_expiry_settles_at_intrinsic_value_and_blocks_new_buys():
    bars = flat_market(days=2)
    bars.iloc[75:, bars.columns.get_indexer(["open", "high", "low", "close"])] = 24560.0         # day 2 opens higher
    s = session(bars, days_to_expiry=1.2)                                                        # expires mid day 2
    s.buy("CE", 24500, 1)
    s.advance(130)                                                                               # past 14:03 on day 2
    assert s.position is None and s.closed[0]["reason"] == "expired"
    assert s.closed[0]["exit_price"] == pytest.approx(60.0)                                      # 24560 - 24500
    assert s.expired
    with pytest.raises(PracticeError, match="expired"):
        s.buy("CE", 24500, 1)


def test_your_own_rules_block_you_unless_you_override_and_the_review_calls_it_out():
    s = session(max_trades_per_day=1)
    s.buy("CE", 24500, 1, stop_premium=50.0)
    s.close()
    with pytest.raises(PracticeBlocked, match="already opened today"):
        s.buy("PE", 24500, 1, stop_premium=50.0)
    assert s.blocked == 1
    info = s.buy("PE", 24500, 1, stop_premium=50.0, override=True)
    assert any("broke your own rules" in w for w in info["warnings"]) and s.overrides == 1
    rep = s.finish()
    assert any("2 trades were opened" in f and "at most 1" in f for f in rep["flags"])
    assert rep["blocked"] == 1 and rep["overrides"] == 1


def test_a_stopless_or_oversized_trade_is_warned_about():
    s = session()
    assert "No stop-loss was set." in s.buy("CE", 24500, 1)["warnings"]
    s.close()
    ask = s.quote("CE", 24500)[1]
    info = s.buy("CE", 24500, 1, stop_premium=round(ask - 30, 2))                               # 30 x 65 = 1,950 > 1,000
    assert any("more than your limit" in w for w in info["warnings"])


@pytest.mark.parametrize("call, message", [
    (lambda s: s.buy("XX", 24500, 1), "CE"),
    (lambda s: s.buy("CE", 24500, 0), "whole number"),
    (lambda s: s.buy("CE", 24500, 1, stop_premium=9999), "stop must be"),
    (lambda s: s.buy("CE", 24500, 50), "Not enough money"),
    (lambda s: s.close(), "no open position"),
])
def test_mistakes_are_explained(call, message):
    with pytest.raises(PracticeError, match=message):
        call(session())


def test_only_one_position_at_a_time():
    s = session()
    s.buy("CE", 24500, 1)
    with pytest.raises(PracticeError, match="Close the open position first"):
        s.buy("PE", 24500, 1)


def test_you_never_see_the_future():
    s = session()
    assert len(s.revealed()) == 11 and s.revealed().index[-1] == s.now
    s.advance(5)
    assert len(s.revealed()) == 16
    assert len(s.premium_history("CE", 24500)) == 16


def test_the_clock_reports_the_end_and_day_boundaries():
    s = session(flat_market(days=2))
    s.advance_to_day_end()
    assert s.now.strftime("%H:%M") == "15:25" and s.now.day == 6
    assert s.next_bar() and s.now.day == 7
    assert s.advance(1000) > 0 and s.at_end and s.next_bar() is False


def test_finish_closes_the_position_and_the_review_adds_up():
    bars = generate_world("trend", 3, 4, 24500.0)
    s = PracticeSession(bars, PracticeSettings(), start_index=20)
    ask = s.quote("CE", s.atm_strike())[1]
    s.buy("CE", s.atm_strike(), 1, stop_premium=round(ask * 0.9, 2))
    s.advance(40)
    rep = s.finish()
    t = rep["totals"]
    assert s.position is None and len(rep["trades"]) == 1
    assert t["move"] + t["time"] + t["spread"] + t["charges"] == pytest.approx(t["net"], abs=1e-6)
    assert rep["net_pnl"] == pytest.approx(t["net"])
    text = format_practice_report(rep, "The market was: trend.")
    assert "PRACTICE ROOM REVIEW" in text and "Spread and charges alone cost" in text and "The market was: trend." in text
    assert "not real premiums" in text


def test_the_review_explains_being_right_and_still_losing():
    # A small favourable move that time decay, spread and charges more than eat.
    bars = flat_market()
    bars.iloc[40:, bars.columns.get_indexer(["open", "high", "low", "close"])] = 24508.0
    s = session(bars, days_to_expiry=2.0)
    s.buy("CE", 24500, 1)
    s.advance(50)
    rep = s.finish()
    assert rep["totals"]["move"] > 0 and rep["net_pnl"] < 0
    assert "right about direction" in format_practice_report(rep)


def test_bad_sessions_are_refused():
    with pytest.raises(PracticeError, match="too short"):
        PracticeSession(flat_market(days=1).iloc[:5], PracticeSettings())
    with pytest.raises(PracticeError, match="above 0"):
        PracticeSession(flat_market(), PracticeSettings(iv_pct=0))


def test_model_prices_match_the_pricing_module():
    s = session()
    assert s.mid("CE", 24500) == pytest.approx(bs_price(24500, 24500, s.dte(), 0.14, "call", s.s.rate))
