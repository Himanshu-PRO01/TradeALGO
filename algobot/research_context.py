from __future__ import annotations
import math
import pandas as pd

def _clean(v):
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        try: v = v.item()
        except Exception: pass
    return None if isinstance(v, float) and not math.isfinite(v) else v

def clean_metrics(metrics):
    return {k:_clean(v) for k,v in (metrics or {}).items()}

def backtest_facts(result):
    facts = clean_metrics(result.metrics)
    for k,v in (result.rejections or {}).items():
        facts[f"rejections.{k}"] = int(v)
    t = result.trades
    if t is None or t.empty:
        return facts
    n = t["net_pnl"].astype(float)
    facts.update({
        "backtest.largest_win":_clean(float(n.max())),
        "backtest.largest_loss":_clean(float(n.min())),
        "backtest.winning_trades":int((n>0).sum()),
        "backtest.losing_trades":int((n<=0).sum()),
    })
    for reason,g in t.groupby("exit_reason"):
        facts[f"exit_reason_count.{reason}"] = int(len(g))
        facts[f"exit_reason_net_pnl.{reason}"] = _clean(float(g["net_pnl"].sum()))
    return facts

def forward_test_facts(trades, starting_capital):
    facts={"forward.starting_capital":float(starting_capital),"forward.trades":0}
    if trades is None or trades.empty: return facts
    d=trades.copy()
    d["exit_time"]=pd.to_datetime(d["exit_time"])
    d=d.sort_values("exit_time")
    n=d["net_pnl"].astype(float)
    equity=float(starting_capital)+n.cumsum()
    dd=equity-equity.cummax()
    daily=d.groupby(d["exit_time"].dt.date)["net_pnl"].sum()
    facts.update({
        "forward.trades":int(len(d)),
        "forward.net_pnl":_clean(float(n.sum())),
        "forward.win_rate_pct":_clean(float((n>0).mean()*100)),
        "forward.expectancy_per_trade":_clean(float(n.mean())),
        "forward.max_drawdown":_clean(float(dd.min())),
        "forward.days_traded":int(len(daily)),
        "forward.profitable_days_pct":_clean(float((daily>0).mean()*100)),
        "forward.virtual_balance":_clean(float(equity.iloc[-1])),
    })
    return facts

def reality_check_facts(report):
    statuses=[c.status for c in report.checks]
    return {
        "reality.verdict":report.verdict,
        "reality.checks_passed":statuses.count("PASS"),
        "reality.checks_warned":statuses.count("WARN"),
        "reality.checks_failed":statuses.count("FAIL"),
        "reality.checks_skipped":statuses.count("SKIP"),
        "reality.trials":int(report.trials),
    }

def reality_check_details(report):
    return [{"name":c.name,"status":c.status,"detail":c.detail} for c in report.checks]
