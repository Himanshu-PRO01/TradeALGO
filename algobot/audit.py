"""Reality check: try to break a strategy before real money does.

Each check answers one reason backtested strategies fail live:

  1. Too few trades          -> luck cannot be told from skill
  2. Not significant         -> the average profit could be zero; also corrected
                                for how many variants were tried (cherry-picking)
  3. Costs                   -> the edge disappears when costs are a bit worse
  4. No better than random   -> the entry rule adds nothing over random entries
                                with the same stops, costs and holding time
  5. Falls apart over time   -> works in the first part of the data, not the rest
  6. Fragile settings        -> profitable only at one exact parameter value
  7. One lucky streak        -> profit comes from a few trades
  8. Risk of ruin            -> even a positive edge can wipe out a small account

Passing all checks does NOT prove a strategy will make money. Failing tells you
it very likely will not, or that you cannot know yet.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from .engine import Backtester, BacktestResult, run_backtest
from .experiments import required_t_stat
from .strategy import BUY, EXIT, SELL, Strategy, build_strategy

PASS, WARN, FAIL, SKIP = "PASS", "WARN", "FAIL", "SKIP"


@dataclass
class AuditCheck:
    name: str
    status: str
    detail: str


@dataclass
class AuditReport:
    name: str
    checks: list
    verdict: str
    result: BacktestResult
    trials: int = 1
    stats: dict = field(default_factory=dict)

    @property
    def failed(self) -> bool:
        return any(c.status == FAIL for c in self.checks)


# ------------------------------------------------------------------ helpers
COST_FIELDS = ("brokerage_pct", "brokerage_cap", "brokerage_flat", "stt_buy_pct", "stt_sell_pct",
               "exchange_txn_pct", "sebi_fee_pct", "stamp_buy_pct", "slippage_bps")


def scale_costs(cfg: dict, multiplier: float) -> dict:
    """Copy of the config with every charge and the slippage multiplied."""
    out = copy.deepcopy(cfg)
    for key in COST_FIELDS:
        if out["costs"].get(key) is not None:
            out["costs"][key] = out["costs"][key] * multiplier
    return out


class RandomEntry(Strategy):
    """Benchmark: enters at random, exits after a fixed number of bars (or at the stop/target)."""

    def __init__(self, prob: float, hold_bars: int, allow_short: bool, seed: int):
        super().__init__({})
        self.prob, self.hold, self.allow_short = prob, hold_bars, allow_short
        self.rng = np.random.default_rng(seed)
        self._held = 0

    def on_bar(self, i: int, df: pd.DataFrame, position: int) -> Optional[str]:
        if position == 0:
            self._held = 0
            if self.rng.random() < self.prob:
                return SELL if (self.allow_short and self.rng.random() < 0.5) else BUY
            return None
        self._held += 1
        return EXIT if self._held >= self.hold else None


def _hold_bars(df: pd.DataFrame, trades: pd.DataFrame) -> int:
    entry = df.index.get_indexer(pd.to_datetime(trades["entry_time"]))
    exit_ = df.index.get_indexer(pd.to_datetime(trades["exit_time"]))
    ok = (entry >= 0) & (exit_ >= 0)
    if not ok.any():
        return 1
    return int(max(1, round(float(np.median(exit_[ok] - entry[ok])))))


def parameter_variants(cfg: dict) -> list:
    """One-at-a-time changes of about +/-20% to every numeric setting we can safely perturb."""
    out = []
    s = cfg["strategy"]
    params = s["params"]

    def bump(base: int):
        return sorted({max(1, int(round(base * 0.8))), max(1, int(round(base * 1.2)))} - {base})

    if s["name"] == "sma_crossover":
        defaults = {"fast": 10, "slow": 30}
        for key in ("fast", "slow"):
            base = params.get(key, defaults[key])
            for v in bump(base):
                c = copy.deepcopy(cfg)
                c["strategy"]["params"] = {**defaults, **params, key: v}
                if c["strategy"]["params"]["fast"] < c["strategy"]["params"]["slow"]:
                    out.append((f"{key} {base} -> {v}", c))
    elif s["name"] == "rules":
        for i, spec in enumerate(params.get("indicators") or []):
            period = spec.get("period")
            if isinstance(period, int) and not isinstance(period, bool):
                for v in bump(period):
                    c = copy.deepcopy(cfg)
                    c["strategy"]["params"]["indicators"][i]["period"] = v
                    out.append((f"{spec.get('name')} period {period} -> {v}", c))
    for key in ("stop_loss_pct", "target_pct"):
        base = s[key]
        if base:
            for mult in (0.8, 1.2):
                c = copy.deepcopy(cfg)
                c["strategy"][key] = round(base * mult, 6)
                out.append((f"{key} {base:g} -> {c['strategy'][key]:g}", c))
    return out


def monte_carlo(nets: np.ndarray, capital: float, ruin_pct: float, n_paths: int, seed: int,
                path_len: Optional[int] = None) -> dict:
    """Resample the trades (with replacement) into many possible futures."""
    rng = np.random.default_rng(seed)
    length = path_len or int(min(max(len(nets), 30), 250))
    paths = np.cumsum(rng.choice(nets, size=(n_paths, length)), axis=1)
    with_start = np.concatenate([np.zeros((n_paths, 1)), paths], axis=1)
    drawdown = (with_start - np.maximum.accumulate(with_start, axis=1)).min(axis=1)
    ruin_level = -capital * ruin_pct / 100.0
    return {
        "length": length,
        "p_ruin": float((paths.min(axis=1) <= ruin_level).mean()),
        "p_loss": float((paths[:, -1] < 0).mean()),
        "final_p5": float(np.percentile(paths[:, -1], 5)),
        "final_median": float(np.percentile(paths[:, -1], 50)),
        "drawdown_p95": float(np.percentile(drawdown, 5)),
    }


def _rs(x: float) -> str:
    return f"Rs {x:,.2f}"


# ------------------------------------------------------------------- checks
def check_sample_size(trades: pd.DataFrame) -> AuditCheck:
    n = len(trades)
    name = "enough trades to tell skill from luck"
    if n >= 100:
        return AuditCheck(name, PASS, f"{n} trades.")
    if n >= 30:
        return AuditCheck(name, WARN, f"{n} trades is workable but thin. Aim for 100 or more.")
    return AuditCheck(name, FAIL, f"Only {n} trades. Results from fewer than 30 trades are mostly luck.")


def check_significance(trades: pd.DataFrame, trials: int, seed: int) -> AuditCheck:
    name = "average profit per trade is clearly above zero"
    n = len(trades)
    if n < 2:
        return AuditCheck(name, SKIP, "Not enough trades to test.")
    nets = trades["net_pnl"].to_numpy(dtype=float)
    mean, std = float(nets.mean()), float(nets.std(ddof=1))
    if std == 0:
        return AuditCheck(name, SKIP, "Every trade had the same result.")
    t = mean / (std / math.sqrt(n))
    hurdle = required_t_stat(trials)
    boot = np.random.default_rng(seed).choice(nets, size=(2000, n)).mean(axis=1)
    low = float(np.percentile(boot, 5))
    detail = (f"Average per trade {_rs(mean)}, t-statistic {t:.2f}. {trials} variant(s) were tried on this data, "
              f"so the bar is {hurdle:.2f}. With 95% confidence the true average is at least {_rs(low)}.")
    if mean <= 0 or t < 1.0:
        return AuditCheck(name, FAIL, detail)
    if t >= hurdle and low > 0:
        return AuditCheck(name, PASS, detail)
    return AuditCheck(name, WARN, detail)


def check_costs(df: pd.DataFrame, cfg: dict, base: BacktestResult) -> AuditCheck:
    name = "still profitable if costs turn out worse"
    net1 = base.metrics["net_pnl"]
    net15 = run_backtest(df, scale_costs(cfg, 1.5), build_strategy(cfg)).metrics["net_pnl"]
    net2 = run_backtest(df, scale_costs(cfg, 2.0), build_strategy(cfg)).metrics["net_pnl"]
    gross, costs = base.metrics["gross_pnl"], base.metrics["total_costs"]
    share = f" Costs took {costs / gross * 100:.0f}% of the profit before costs." if gross > 0 else ""
    detail = f"Net result at 1x costs {_rs(net1)}, at 1.5x {_rs(net15)}, at 2x {_rs(net2)}.{share}"
    if net1 <= 0:
        return AuditCheck(name, FAIL, "Loses money even at the costs you assumed. " + detail)
    if net2 > 0:
        return AuditCheck(name, PASS, detail)
    if net15 > 0:
        return AuditCheck(name, WARN, "The edge is thin: " + detail)
    return AuditCheck(name, FAIL, "The edge disappears when costs rise a little. " + detail)


def check_random_entries(df: pd.DataFrame, cfg: dict, base: BacktestResult, runs: int, seed: int,
                         trials: int = 1) -> AuditCheck:
    name = "beats random entries that use the same stops, costs and holding time"
    trades = base.trades
    if len(trades) == 0:
        return AuditCheck(name, SKIP, "No trades to compare.")
    hold = _hold_bars(df, trades)
    flat_bars = max(len(df) - len(trades) * hold, len(trades))
    prob = min(max(len(trades) / flat_bars, 0.001), 0.5)
    actual = float(trades["net_pnl"].mean())
    random_results = []
    for k in range(runs):
        strategy = RandomEntry(prob, hold, cfg["strategy"]["allow_short"], seed + 1000 + k)
        res = Backtester(cfg, strategy).run(df)
        exp = res.metrics["expectancy_per_trade"]
        if exp is not None:
            random_results.append(exp)
    if len(random_results) < max(5, runs // 4):
        return AuditCheck(name, SKIP, "The random benchmark produced too few trades to compare.")
    beaten = float(np.mean(np.array(random_results) < actual) * 100.0)
    # If many variants were tried, the winner beats most random runs by luck alone:
    # the bar rises the same way a multiple-testing correction raises it.
    needed = 100.0 * (1.0 - 0.05 / max(trials, 1))
    detail = (f"Your average per trade {_rs(actual)} beats {beaten:.0f}% of {len(random_results)} random-entry runs "
              f"(their median {_rs(float(np.median(random_results)))}). To be convincing it should beat at least "
              f"{min(needed, 99.9):.1f}%" + (f" (raised from 95% because {trials} variants were tried)." if trials > 1 else "."))
    if beaten >= 95 and beaten >= needed:
        return AuditCheck(name, PASS, detail)
    if beaten >= 80:
        return AuditCheck(name, WARN, detail)
    return AuditCheck(name, FAIL, detail)


def check_out_of_sample(df: pd.DataFrame, trades: pd.DataFrame, frac: float) -> AuditCheck:
    """Check later-period stability, not a substitute for a frozen true holdout.

    This project does not optimise parameters automatically, so it cannot prove
    that the later segment was never used to design the rule. A genuine
    out-of-sample test requires freezing the strategy on earlier data before
    looking at the later data.
    """
    name = "remains viable in the later period (stability check, not a true holdout)"
    if len(trades) == 0:
        return AuditCheck(name, SKIP, "No trades.")
    cut = df.index[int(len(df) * frac)]
    entered = pd.to_datetime(trades["entry_time"])
    first, later = trades[entered < cut], trades[entered >= cut]
    if len(first) < 10 or len(later) < 10:
        return AuditCheck(name, WARN, f"Too few trades to judge ({len(first)} early, {len(later)} late).")
    e1, e2 = float(first["net_pnl"].mean()), float(later["net_pnl"].mean())
    detail = f"Average per trade: {_rs(e1)} in the first {frac:.0%} of the data, {_rs(e2)} in the rest."
    if e2 <= 0:
        return AuditCheck(name, FAIL, detail)
    if e1 <= 0 or e2 < 0.5 * e1:
        return AuditCheck(name, WARN, detail)
    return AuditCheck(name, PASS, detail)


def check_parameters(df: pd.DataFrame, cfg: dict, base: BacktestResult) -> AuditCheck:
    name = "still profitable when settings change by about 20%"
    if base.metrics["net_pnl"] <= 0:
        return AuditCheck(name, SKIP, "Nothing to test: the base setup already loses money.")
    results = []
    for label, variant in parameter_variants(cfg):
        try:
            net = run_backtest(df, variant, build_strategy(variant)).metrics["net_pnl"]
        except Exception:
            continue
        results.append((label, net))
    if not results:
        return AuditCheck(name, SKIP, "This strategy has no numeric settings to vary.")
    good = sum(1 for _, net in results if net > 0)
    share = good / len(results)
    worst = min(results, key=lambda r: r[1])
    detail = (f"{good} of {len(results)} slightly changed versions are still profitable. "
              f"Worst: {worst[0]} gives {_rs(worst[1])}.")
    if share >= 0.7:
        return AuditCheck(name, PASS, detail)
    if share >= 0.5:
        return AuditCheck(name, WARN, detail)
    return AuditCheck(name, FAIL, "Profit depends on exact settings, a classic sign of curve-fitting. " + detail)


def check_concentration(trades: pd.DataFrame) -> AuditCheck:
    name = "profit does not come from a handful of lucky trades"
    n = len(trades)
    if n < 5:
        return AuditCheck(name, SKIP, "Too few trades.")
    nets = np.sort(trades["net_pnl"].to_numpy(dtype=float))[::-1]
    if nets.sum() <= 0:
        return AuditCheck(name, SKIP, "The strategy does not make a profit overall.")
    k = max(1, int(math.ceil(0.05 * n)))
    without = float(nets[k:].sum())
    share = float(nets[:k].sum() / nets[nets > 0].sum() * 100.0)
    detail = f"The best {k} trade(s) made {share:.0f}% of all winnings. Without them the result is {_rs(without)}."
    if without <= 0:
        return AuditCheck(name, FAIL, detail)
    if share >= 50:
        return AuditCheck(name, WARN, detail)
    return AuditCheck(name, PASS, detail)


def check_ruin(trades: pd.DataFrame, capital: float, ruin_pct: float, paths: int, seed: int) -> AuditCheck:
    name = f"small chance of losing {ruin_pct:g}% of the account"
    if len(trades) < 5:
        return AuditCheck(name, SKIP, "Too few trades to simulate.")
    mc = monte_carlo(trades["net_pnl"].to_numpy(dtype=float), capital, ruin_pct, paths, seed)
    detail = (f"Reshuffling the trades into {paths:,} possible futures of {mc['length']} trades each: "
              f"{mc['p_ruin']:.0%} lose {ruin_pct:g}% of the account at some point, {mc['p_loss']:.0%} end with a loss. "
              f"Typical worst drawdown {_rs(-mc['drawdown_p95'])} (1 in 20 is worse). Median outcome {_rs(mc['final_median'])}.")
    if mc["p_ruin"] > 0.20:
        return AuditCheck(name, FAIL, detail)
    if mc["p_ruin"] > 0.05 or mc["p_loss"] > 0.5:
        return AuditCheck(name, WARN, detail)
    return AuditCheck(name, PASS, detail)


# --------------------------------------------------------------------- audit
def run_audit(df: pd.DataFrame, cfg: dict, trials: int = 1, n_random: int = 100, n_mc: int = 1000,
              seed: int = 7, ruin_pct: float = 30.0, oos_frac: float = 0.6) -> AuditReport:
    base = run_backtest(df, cfg, build_strategy(cfg))
    trades = base.trades
    checks = [
        check_sample_size(trades),
        check_significance(trades, trials, seed),
        check_costs(df, cfg, base),
        check_random_entries(df, cfg, base, n_random, seed, trials),
        check_out_of_sample(df, trades, oos_frac),
        check_parameters(df, cfg, base),
        check_concentration(trades),
        check_ruin(trades, float(cfg["capital"]), ruin_pct, n_mc, seed),
    ]
    fails = [c for c in checks if c.status == FAIL]
    warns = [c for c in checks if c.status == WARN]
    if fails:
        verdict = f"NOT READY: {len(fails)} check(s) failed. Do not risk real money on this."
    elif warns:
        verdict = f"PROMISING BUT UNPROVEN: {len(warns)} warning(s). Keep testing and paper trade first."
    else:
        verdict = "PASSED THESE CHECKS: paper trade next. This is still not proof of future profit."
    return AuditReport(name=cfg["name"], checks=checks, verdict=verdict, result=base, trials=trials,
                       stats={"trades": len(trades)})


def format_audit(report: AuditReport) -> str:
    icons = {PASS: "PASS", WARN: "WARN", FAIL: "FAIL", SKIP: "SKIP"}
    lines = [f"REALITY CHECK: {report.name}", "=" * 64]
    for c in report.checks:
        lines.append(f"[{icons[c.status]}] {c.name}")
        lines.append(f"       {c.detail}")
    lines += ["=" * 64, "VERDICT: " + report.verdict,
              "Passing does not prove a strategy makes money. Failing means it very likely will not, "
              "or that you cannot know yet."]
    return "\n".join(lines)
