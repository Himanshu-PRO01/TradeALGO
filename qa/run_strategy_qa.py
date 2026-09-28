"""Manual QA: run a realistic (fake) opening-range-breakout strategy through the engine and check the numbers.

Run from anywhere:   python qa/run_strategy_qa.py
This is NOT part of the pytest suite (the file name is deliberately not test_*.py or *_test.py)."""
import sys

import pandas as pd

from _common import RAW, load_prices
from algobot.config import validate_config
from algobot.lookahead import run_lookahead_checks
from algobot.runner import run_from_dict


def main() -> int:
    df = load_prices()
    res = run_from_dict(RAW, df)
    m, t = res.metrics, res.trades
    cfg = validate_config(RAW)
    checks = []

    def chk(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    chk("CSV loaded", len(df) == 6750, f"{len(df)} bars, {df.index.min()} -> {df.index.max()}")
    chk("Strategy produced trades", m["trades"] > 10, f"{m['trades']} trades")
    et, xt = pd.to_datetime(t.entry_time), pd.to_datetime(t.exit_time)
    chk("No entry before 09:30", (et.dt.strftime("%H:%M") >= "09:30").all())
    chk("No entry after 14:45 (+1 bar fill)", (et.dt.strftime("%H:%M") <= "14:50").all())
    chk("Everything flat by 15:15-15:25", (xt.dt.strftime("%H:%M") <= "15:25").all())
    chk("No trade held overnight", (et.dt.date == xt.dt.date).all())
    per_day = t.groupby(et.dt.date).size()
    chk("Max 3 trades per day respected", per_day.max() <= 3, f"busiest day {per_day.max()}")
    chk("Net = gross - costs (per trade)", ((t.gross_pnl - t.costs - t.net_pnl).abs() < 0.02).all())
    chk("Costs are positive on every trade", (t.costs > 0).all())
    chk("Final equity = capital + net P&L", abs(res.equity.iloc[-1] - (500000 + t.net_pnl.sum())) < 1.0)
    chk("Metrics net P&L matches trade sum", abs(m["net_pnl"] - t.net_pnl.sum()) < 1.0)
    chk("Both long and short trades happened", t.side.nunique() > 1, str(t.side.value_counts().to_dict()))
    chk("No loss far beyond the stop-loss", t.net_pnl.min() > -12000, f"worst trade Rs {t.net_pnl.min():,.0f}")
    la = run_lookahead_checks(cfg, df)
    chk("Look-ahead checks all pass", all(c.passed for c in la))

    print("=== RESULT SUMMARY ===")
    for k in ["trades", "net_pnl", "return_pct", "win_rate_pct", "profit_factor", "max_drawdown", "total_costs"]:
        print(f"{k:>16}: {m[k]}")
    print("\n=== CHECKS ===")
    bad = 0
    for n, ok, d in checks:
        print(("PASS " if ok else "FAIL "), n, "-", d)
        bad += not ok
    print(f"\n{len(checks) - bad}/{len(checks)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
