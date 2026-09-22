"""Stress lab: meet many kinds of market, instantly.

For each market personality (trend, chop, crash, shocks...) this generates many
fresh fake worlds, runs the strategy through each with its real costs and risk
rules, and reports:

  * where the strategy makes money and where it loses (its "habitat"),
  * whether the risk rules held (nothing overnight, trade limits, daily loss),
  * a NULL TEST: on pure noise with all costs removed, a strategy must earn
    about zero. If it "profits" from random prices, it is almost certainly
    cheating (peeking at the future, or a bug), and no result from it can be
    trusted.

Reading the results: these are made-up markets. They show how a strategy and
its safety rules BEHAVE. They cannot show what will make money, and tuning the
strategy to win here would only teach it to fit noise.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .engine import run_backtest
from .strategy import build_strategy
from .worlds import REGIMES, generate_world

ZERO_COSTS = {"brokerage_pct": 0.0, "brokerage_cap": None, "brokerage_flat": None, "stt_buy_pct": 0.0,
              "stt_sell_pct": 0.0, "exchange_txn_pct": 0.0, "sebi_fee_pct": 0.0, "stamp_buy_pct": 0.0,
              "gst_pct": 0.0, "slippage_bps": 0.0}


@dataclass
class LabReport:
    name: str
    runs: pd.DataFrame
    by_regime: pd.DataFrame
    integrity: list = field(default_factory=list)
    control: dict = field(default_factory=dict)
    insights: list = field(default_factory=list)


def _summarise_world(result, cfg) -> dict:
    trades, equity = result.trades, result.equity
    capital = float(cfg["capital"])
    daily = equity.groupby(equity.index.date).last()
    day_pnl = daily.diff()
    day_pnl.iloc[0] = daily.iloc[0] - capital
    violations = []
    risk = cfg["risk"]
    if len(trades):
        entry, exit_ = pd.to_datetime(trades["entry_time"]), pd.to_datetime(trades["exit_time"])
        if (entry.dt.date != exit_.dt.date).any():
            violations.append("a position was held overnight")
        if (entry.dt.time > risk["no_new_entries_after"]).any():
            violations.append("a trade was opened after the last allowed entry time")
        if risk["max_trades_per_day"] is not None and (entry.dt.date.value_counts() > risk["max_trades_per_day"]).any():
            violations.append("more trades in a day than the limit")
    if risk["max_daily_loss"] is not None and day_pnl.min() < -2.0 * risk["max_daily_loss"]:
        violations.append(f"a day lost {-day_pnl.min():,.0f}, more than double the daily limit of {risk['max_daily_loss']:,.0f}")
    m = result.metrics
    return {
        "net_pnl": m["net_pnl"], "gross_pnl": m["gross_pnl"], "costs": m["total_costs"], "trades": m["trades"],
        "win_rate": m["win_rate_pct"], "max_drawdown": m["max_drawdown"], "worst_day": float(day_pnl.min()),
        "violations": "; ".join(violations),
    }


def null_test(cfg: dict, worlds: int = 30, days: int = 15, seed: int = 5000) -> dict:
    """Pure noise, zero costs: the average result must be about zero. Anything else smells like cheating."""
    free = copy.deepcopy(cfg)
    free["costs"] = dict(ZERO_COSTS)
    nets = []
    for k in range(worlds):
        df = generate_world("noise", days, seed + k)
        nets.append(run_backtest(df, free, build_strategy(free)).metrics["net_pnl"])
    nets = np.array(nets, dtype=float)
    std = float(nets.std(ddof=1)) if len(nets) > 1 else 0.0
    t = float(nets.mean() / (std / math.sqrt(len(nets)))) if std > 0 else 0.0
    suspicious = t >= 3.0
    return {
        "worlds": worlds, "mean": float(nets.mean()), "std": std, "t": t, "suspicious": suspicious,
        "text": (f"On {worlds} pure-noise worlds with no costs, the average result was Rs {nets.mean():,.2f} "
                 f"(t-statistic {t:+.2f}). "
                 + ("SUSPICIOUS: it profits from random prices, which no honest strategy can. Look for peeking at "
                    "future prices or a bug before trusting anything else." if suspicious
                    else "That is what an honest strategy should do: nothing, on average.")),
    }


def run_lab(cfg: dict, regimes: list | None = None, worlds_per_regime: int = 8, days: int = 15, seed: int = 100,
            control_worlds: int = 30) -> LabReport:
    names = list(regimes or REGIMES)
    rows = []
    for r_index, name in enumerate(names):
        for k in range(worlds_per_regime):
            world_seed = seed + 1000 * r_index + k
            df = generate_world(name, days, world_seed)
            result = run_backtest(df, cfg, build_strategy(cfg))
            rows.append({"regime": name, "seed": world_seed, **_summarise_world(result, cfg)})
    runs = pd.DataFrame(rows)
    grouped = runs.groupby("regime", sort=False)
    by_regime = pd.DataFrame({
        "worlds": grouped.size(),
        "profitable_pct": grouped["net_pnl"].apply(lambda s: float((s > 0).mean() * 100.0)),
        "mean_net": grouped["net_pnl"].mean(),
        "worst_net": grouped["net_pnl"].min(),
        "mean_trades": grouped["trades"].mean(),
        "worst_day": grouped["worst_day"].min(),
        "worst_drawdown": grouped["max_drawdown"].min(),
    }).reindex(names)

    integrity = sorted({v for cell in runs["violations"] if cell for v in cell.split("; ")})
    insights = []
    best, worst = by_regime["mean_net"].idxmax(), by_regime["mean_net"].idxmin()
    if by_regime["mean_net"].max() > 0:
        insights.append(f"Best habitat: '{best}' (average Rs {by_regime.loc[best, 'mean_net']:,.0f} per {days}-day world). "
                        f"Worst: '{worst}' (average Rs {by_regime.loc[worst, 'mean_net']:,.0f}).")
    else:
        insights.append(f"Least bad: '{best}' (average Rs {by_regime.loc[best, 'mean_net']:,.0f} per {days}-day world). "
                        f"Worst: '{worst}' (average Rs {by_regime.loc[worst, 'mean_net']:,.0f}).")
    if "noise" in by_regime.index:
        noise_win = by_regime.loc["noise", "profitable_pct"]
        insights.append(f"On pure noise it was profitable in {noise_win:.0f}% of worlds. With costs included, "
                        "an honest strategy should be profitable well under half the time there.")
    profitable_regimes = [n for n in names if by_regime.loc[n, "mean_net"] > 0]
    if not profitable_regimes:
        insights.append("It lost money on average in every kind of market tested.")
    elif len(profitable_regimes) < len(names):
        insights.append("It only earns in: " + ", ".join(profitable_regimes) + ". It needs a way to know which "
                        "market it is in, or it will give the profit back in the others.")
    report = LabReport(name=cfg["name"], runs=runs, by_regime=by_regime, integrity=integrity, insights=insights)
    if control_worlds:
        report.control = null_test(cfg, control_worlds, days)
    return report


def format_lab(report: LabReport) -> str:
    lines = [f"STRESS LAB: {report.name}", "=" * 78,
             f"{'market':<15}{'worlds':>7}{'profitable':>12}{'avg net':>11}{'worst net':>11}{'avg trades':>12}{'worst day':>11}"]
    for name, row in report.by_regime.iterrows():
        lines.append(f"{name:<15}{int(row['worlds']):>7}{row['profitable_pct']:>11.0f}%{row['mean_net']:>11,.0f}"
                     f"{row['worst_net']:>11,.0f}{row['mean_trades']:>12.0f}{row['worst_day']:>11,.0f}")
    lines.append("-" * 78)
    lines += report.insights
    if report.integrity:
        lines.append("RISK RULES BROKEN: " + "; ".join(report.integrity))
    else:
        lines.append("Risk rules held in every world (nothing overnight, trade limits, daily loss within twice the limit).")
    if report.control:
        lines.append("NULL TEST: " + report.control["text"])
    lines.append("These are made-up markets: they show how the strategy behaves, not what will make money.")
    return "\n".join(lines)
