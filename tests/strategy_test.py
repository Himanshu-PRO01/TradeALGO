"""Fake-but-realistic end-to-end test of TradeALGO:
Opening-range breakout (15 min) + VWAP + EMA trend + RSI filter, Nifty-like data, real Indian costs."""
import sys, os
sys.path.insert(0, "/home/claude/TradeALGO")
import pandas as pd, yaml
from algobot.data import load_csv
from algobot.runner import run_from_dict
from algobot.lookahead import run_lookahead_checks
from algobot.config import validate_config

RULES = """
indicators:
  - {name: orh, type: opening_range_high, period: 15}
  - {name: orl, type: opening_range_low,  period: 15}
  - {name: vw,  type: vwap}
  - {name: e20, type: ema, period: 20}
  - {name: r14, type: rsi, period: 14}
entry_long:  "close > orh and close_prev <= orh_prev and close > vw and e20 > e20_prev and r14 > 55"
exit_long:   "close < vw"
entry_short: "close < orl and close_prev >= orl_prev and close < vw and e20 < e20_prev and r14 < 45"
exit_short:  "close > vw"
"""

raw = {
  "name": "orb_vwap_test", "capital": 500000,
  "strategy": {"name": "rules", "params": yaml.safe_load(RULES), "quantity": 75, "allow_short": True,
               "stop_loss_pct": 0.35, "target_pct": 0.7},
  "risk": {"max_daily_loss": 6000, "max_trades_per_day": 3, "max_position_value": 2500000,
           "trading_start": "09:30", "no_new_entries_after": "14:45", "square_off_time": "15:15"},
  "costs": {"brokerage_pct": 0.03, "brokerage_cap": 20, "stt_buy_pct": 0.0, "stt_sell_pct": 0.025,
            "exchange_txn_pct": 0.003, "sebi_fee_pct": 0.0001, "stamp_buy_pct": 0.003, "gst_pct": 18, "slippage_bps": 2},
}

df = load_csv("realistic_nifty_5min.csv")
res = run_from_dict(raw, df)
m, t = res.metrics, res.trades
cfg = validate_config(raw)

checks = []
def chk(name, ok, detail=""):
    checks.append((name, bool(ok), detail))

chk("CSV loaded", len(df) == 6750, f"{len(df)} bars, {df.index.min()} -> {df.index.max()}")
chk("Strategy produced trades", m["trades"] > 10, f"{m['trades']} trades")
et, xt = pd.to_datetime(t.entry_time), pd.to_datetime(t.exit_time)
chk("No entry before 09:30", (et.dt.strftime("%H:%M") >= "09:30").all(), f"earliest {et.dt.strftime('%H:%M').min()}")
chk("No entry after 14:45 (+1 bar fill)", (et.dt.strftime("%H:%M") <= "14:50").all(), f"latest {et.dt.strftime('%H:%M').max()}")
chk("Everything flat by 15:15-15:25", (xt.dt.strftime("%H:%M") <= "15:25").all(), f"latest exit {xt.dt.strftime('%H:%M').max()}")
chk("No trade held overnight", (et.dt.date == xt.dt.date).all())
per_day = t.groupby(et.dt.date).size()
chk("Max 3 trades per day respected", per_day.max() <= 3, f"busiest day {per_day.max()}")
chk("Net = gross - costs (per trade)", ((t.gross_pnl - t.costs - t.net_pnl).abs() < 0.02).all())
chk("Costs are positive on every trade", (t.costs > 0).all(), f"avg cost Rs {t.costs.mean():.1f}/trade")
chk("Final equity = capital + net P&L", abs(res.equity.iloc[-1] - (500000 + t.net_pnl.sum())) < 1.0,
    f"{res.equity.iloc[-1]:,.0f} vs {500000 + t.net_pnl.sum():,.0f}")
chk("Metrics net P&L matches trade sum", abs(m["net_pnl"] - t.net_pnl.sum()) < 1.0)
chk("Both long and short trades happened", set(t.side.str.upper().unique()) >= {"LONG", "SHORT"} or t.side.nunique() > 1,
    str(t.side.value_counts().to_dict()))
sl_hits = t.exit_reason.value_counts().to_dict()
chk("Exit reasons recorded", len(sl_hits) > 0, str(sl_hits))
chk("No loss far beyond the stop-loss", t.net_pnl.min() > -12000, f"worst trade Rs {t.net_pnl.min():,.0f}")
dl = t.groupby(xt.dt.date).net_pnl.sum()
chk("Daily loss brake roughly held", dl.min() > -6000*2.2, f"worst day Rs {dl.min():,.0f} (limit 6,000)")
la = run_lookahead_checks(cfg, df)
chk("Look-ahead checks all pass", all(c.passed for c in la), "; ".join(f"{c.name}:{'ok' if c.passed else 'FAIL'}" for c in la))

print("=== RESULT SUMMARY ===")
for k in ["trades","net_pnl","return_pct","win_rate_pct","profit_factor","max_drawdown","gross_pnl","total_costs","avg_win","avg_loss","max_win_streak","max_loss_streak","exposure_pct"]:
    print(f"{k:>16}: {m[k]}")
print("\n=== CHECKS ===")
bad = 0
for n, ok, d in checks:
    print(("PASS " if ok else "FAIL "), n, "-", d)
    bad += (not ok)
print(f"\n{len(checks)-bad}/{len(checks)} passed")
df.to_pickle("prices.pkl"); pd.to_pickle(raw, "raw.pkl")
sys.exit(1 if bad else 0)
