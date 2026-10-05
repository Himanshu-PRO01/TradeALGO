"""India-first robustness scoring for strategy research; no live execution."""
from __future__ import annotations
from dataclasses import dataclass
import math
import statistics


@dataclass(frozen=True)
class RobustnessResult:
    net_pnl: float
    avg_trade: float
    win_rate: float
    max_drawdown: float
    profit_factor: float
    cost_stress_pnl: float
    walk_forward_pass: bool
    monte_carlo_p05: float
    monte_carlo_p50: float
    monte_carlo_p95: float
    verdict: str


def max_drawdown(equity: list[float]) -> float:
    peak = equity[0] if equity else 0.0
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        worst = min(worst, value - peak)
    return worst


def monte_carlo_trade_paths(trades: list[float], paths: int = 500, seed: int = 7) -> tuple[float, float, float]:
    import random
    if not trades:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed)
    totals = []
    for _ in range(max(10, paths)):
        totals.append(sum(rng.choice(trades) for _ in trades))
    totals.sort()
    def pct(p):
        return totals[min(len(totals)-1, max(0, int((len(totals)-1)*p)))]
    return pct(.05), pct(.50), pct(.95)


def evaluate_trades(
    trades: list[float],
    *,
    cost_multiplier: float = 1.5,
    validation_fraction: float = .30,
) -> RobustnessResult:
    if not trades:
        return RobustnessResult(0,0,0,0,0,0,False,0,0,0,"FAILED")
    net = float(sum(trades))
    wins = [x for x in trades if x > 0]
    losses = [x for x in trades if x < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_win / gross_loss if gross_loss else math.inf
    equity = []
    running = 0.0
    for t in trades:
        running += t
        equity.append(running)
    cut = max(1, int(len(trades) * (1-validation_fraction)))
    train = trades[:cut]
    validation = trades[cut:]
    wf = bool(validation) and statistics.mean(validation) > 0 and statistics.mean(train) > 0
    mc05, mc50, mc95 = monte_carlo_trade_paths(trades)
    stressed = net - abs(net) * max(0.0, cost_multiplier - 1.0) if net < 0 else net * (2.0-cost_multiplier)
    if net <= 0 or mc05 <= 0 or not wf:
        verdict = "FAILED"
    elif pf < 1.2 or mc05 <= 0:
        verdict = "UNSTABLE"
    elif pf >= 1.5 and mc05 > 0:
        verdict = "ROBUST RESEARCH CANDIDATE"
    else:
        verdict = "PROMISING"
    return RobustnessResult(
        net, net/len(trades), len(wins)/len(trades), max_drawdown(equity),
        pf, stressed, wf, mc05, mc50, mc95, verdict
    )
