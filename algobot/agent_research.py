"""Autonomous synthetic research agents for TradeALGO.

Agents are researchers, not traders: they can generate and test strategy configurations
against synthetic Indian-market regimes, critique failures, mutate candidates and validate
survivors on untouched holdout worlds. No broker/live execution is reachable here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import copy
import math
import random
from typing import Iterable

import numpy as np

from .engine import run_backtest
from .strategy import build_strategy
from .worlds import generate_mixed_world


@dataclass(frozen=True)
class ResearchAgent:
    agent_id: str
    role: str
    risk_bias: float
    exploration: float


@dataclass(frozen=True)
class CandidateScore:
    candidate_id: str
    generation: int
    train_pnl: float
    holdout_pnl: float
    train_trades: int
    holdout_trades: int
    train_pf: float
    holdout_pf: float
    train_dd: float
    holdout_dd: float
    robustness: float
    accepted: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ResearchRun:
    agents: tuple[ResearchAgent, ...]
    generations: int
    candidates_tested: int
    scores: tuple[CandidateScore, ...]
    winner_id: str | None
    winner_cfg: dict | None
    verdict: str
    findings: tuple[str, ...]


AGENTS = (
    ResearchAgent("researcher-01", "explorer", .55, .95),
    ResearchAgent("researcher-02", "risk manager", .10, .35),
    ResearchAgent("researcher-03", "momentum specialist", .75, .80),
    ResearchAgent("researcher-04", "contrarian", .65, .90),
    ResearchAgent("researcher-05", "cost auditor", .20, .45),
    ResearchAgent("researcher-06", "adversarial validator", .15, 1.00),
    ResearchAgent("researcher-07", "stability analyst", .35, .55),
    ResearchAgent("researcher-08", "portfolio researcher", .50, .70),
)

REGIME_SETS = (
    ("trend", "chop", "mean_reversion"),
    ("volatile", "noise", "trend"),
    ("shocks", "chop", "mean_reversion"),
    ("trend", "volatile", "shocks"),
)


def _pf(result) -> float:
    value = result.metrics.get("profit_factor")
    if value is None:
        return 0.0
    return float(value)


def _evaluate(cfg: dict, days: int, seed: int, regimes: Iterable[str]):
    pnls, trades, pfs, dds = [], [], [], []
    for offset, regime in enumerate(regimes):
        world, _ = generate_mixed_world(
            days=days, seed=seed + offset * 997, regimes=[regime]
        )
        result = run_backtest(world, cfg, build_strategy(cfg))
        pnls.append(float(result.metrics.get("net_pnl", 0.0)))
        trades.append(int(result.metrics.get("trades", 0)))
        pfs.append(_pf(result))
        dds.append(float(result.metrics.get("max_drawdown", 0.0)))
    return (
        float(np.mean(pnls)) if pnls else 0.0,
        int(sum(trades)),
        float(np.mean(pfs)) if pfs else 0.0,
        float(np.mean(dds)) if dds else 0.0,
    )


def _mutate(base: dict, agent: ResearchAgent, rng: random.Random, generation: int) -> dict:
    cfg = copy.deepcopy(base)
    strategy = cfg["strategy"]
    # Bounded mutations keep the search interpretable and prevent parameter explosion.
    stop = float(strategy.get("stop_loss_pct") or 0.5)
    target = float(strategy.get("target_pct") or 1.0)
    stop *= rng.choice((0.80, 0.90, 1.0, 1.10, 1.25))
    target *= rng.choice((0.80, 0.90, 1.0, 1.10, 1.25))
    if agent.role == "risk manager":
        stop *= rng.choice((0.80, 0.90))
        target *= rng.choice((0.90, 1.0, 1.10))
    elif agent.role == "momentum specialist":
        target *= rng.choice((1.0, 1.10, 1.25))
    elif agent.role == "cost auditor":
        target *= rng.choice((1.10, 1.20))
        stop *= rng.choice((0.90, 1.0))
    elif agent.role == "adversarial validator":
        stop *= rng.choice((0.75, 1.25))
        target *= rng.choice((0.75, 1.25))
    strategy["stop_loss_pct"] = round(max(0.10, min(5.0, stop)), 4)
    strategy["target_pct"] = round(max(0.10, min(8.0, target)), 4)
    cfg["name"] = f"agent_g{generation}_{agent.agent_id}"
    return cfg


def _score(train, holdout, agent: ResearchAgent):
    train_pnl, train_trades, train_pf, train_dd = train
    test_pnl, test_trades, test_pf, test_dd = holdout
    # Holdout is weighted more heavily than training to discourage overfitting.
    dd_penalty = abs(test_dd) / 1000.0
    stability = max(0.0, min(1.0, 1.0 - abs(train_pnl - test_pnl) / (abs(train_pnl) + 1000.0)))
    robustness = (
        0.25 * max(-1.0, min(1.0, train_pnl / 1000.0))
        + 0.45 * max(-1.0, min(1.0, test_pnl / 1000.0))
        + 0.20 * max(0.0, min(1.0, test_pf / 2.0))
        + 0.10 * stability
        - dd_penalty * (0.5 + agent.risk_bias)
    )
    reasons = []
    if train_pnl <= 0:
        reasons.append("training P&L is non-positive")
    if test_pnl <= 0:
        reasons.append("holdout P&L is non-positive")
    if test_pf < 1.0:
        reasons.append("holdout profit factor is below 1")
    if test_trades < 5:
        reasons.append("holdout sample is too small")
    if abs(test_dd) > abs(train_dd) * 2 and abs(train_dd) > 0:
        reasons.append("holdout drawdown expanded materially")
    return robustness, tuple(reasons)


def run_agent_research(
    base_cfg: dict,
    *,
    generations: int = 5,
    candidates_per_agent: int = 2,
    days: int = 8,
    seed: int = 1701,
    agents: Iterable[ResearchAgent] = AGENTS,
) -> ResearchRun:
    """Let bounded synthetic agents perform an actual research loop.

    Every candidate is tested on multiple train regimes and then untouched holdout
    regimes. Only configurations that survive the holdout are eligible as winners.
    """
    if generations < 1 or candidates_per_agent < 1 or days < 2:
        raise ValueError("generations >= 1, candidates_per_agent >= 1 and days >= 2 required")
    cohort = tuple(agents)
    if not cohort:
        raise ValueError("At least one research agent is required")

    rng = random.Random(seed)
    population = [copy.deepcopy(base_cfg)]
    all_scores: list[CandidateScore] = []
    cfg_by_id: dict[str, dict] = {}
    counter = 0

    for generation in range(1, generations + 1):
        proposals = []
        for agent in cohort:
            for _ in range(candidates_per_agent):
                counter += 1
                cfg = _mutate(population[counter % len(population)], agent, rng, generation)
                cid = f"candidate-{counter:04d}"
                cfg_by_id[cid] = cfg
                proposals.append((cid, cfg, agent))

        ranked = []
        for cid, cfg, agent in proposals:
            train = _evaluate(cfg, days, seed + generation * 10000 + 11, REGIME_SETS[0])
            holdout = _evaluate(cfg, days, seed + generation * 10000 + 53, REGIME_SETS[1])
            robustness, reasons = _score(train, holdout, agent)
            accepted = (
                train[0] > 0
                and holdout[0] > 0
                and holdout[2] >= 1.0
                and holdout[1] >= 5
            )
            all_scores.append(
                CandidateScore(
                    cid, generation, train[0], holdout[0], train[1], holdout[1],
                    train[2], holdout[2], train[3], holdout[3],
                    float(robustness), accepted, reasons
                )
            )
            ranked.append((robustness, cid, cfg, accepted))

        ranked.sort(reverse=True, key=lambda row: row[0])
        # Agents actually choose what survives: retain the top accepted candidates,
        # plus a small exploration lane so one bad regime does not terminate research.
        survivors = [row for row in ranked if row[3]][: max(2, len(cohort) // 2)]
        explorers = ranked[: max(1, len(cohort) // 4)]
        selected = survivors + [row for row in explorers if row not in survivors]
        population = [row[2] for row in selected[: max(2, len(cohort))]]
        if not population:
            population = [copy.deepcopy(base_cfg)]

    final = sorted(
        all_scores,
        key=lambda s: (s.accepted, s.robustness, s.holdout_pnl, s.holdout_pf),
        reverse=True,
    )
    winner = next((s for s in final if s.accepted), None)
    findings = []
    if not winner:
        findings.append("No candidate survived the positive-P&L + holdout + profit-factor gate.")
        findings.append("Agents were unable to manufacture a robust edge from the tested parameter mutations.")
        verdict = "FAILED — KEEP RESEARCHING"
        winner_cfg = None
        winner_id = None
    else:
        winner_cfg = cfg_by_id[winner.candidate_id]
        winner_id = winner.candidate_id
        verdict = "RESEARCH CANDIDATE — REQUIRES REAL OOS DATA"
        findings.append(f"{winner.candidate_id} survived the autonomous holdout gate.")
        findings.append(f"Holdout P&L: ₹{winner.holdout_pnl:,.2f}; holdout PF: {winner.holdout_pf:.2f}.")
        if winner.reasons:
            findings.extend(winner.reasons)

    return ResearchRun(
        cohort, generations, len(all_scores), tuple(all_scores), winner_id,
        winner_cfg, verdict, tuple(findings)
    )
