"""MiroFish-style synthetic-user simulation for TradeALGO.

This is intentionally local and deterministic: agents exercise safe research
workflows against fake market worlds. No browser, network, broker, or OpenAlgo
call is made here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .config import validate_config
from .lab import run_lab
from .strategy import build_strategy


@dataclass(frozen=True)
class AgentProfile:
    name: str
    risk_tolerance: float
    quantity_multiplier: float
    target_multiplier: float


PROFILES = (
    AgentProfile("momentum", 0.8, 1.0, 1.0),
    AgentProfile("risk_averse", 0.25, 0.5, 0.7),
    AgentProfile("fomo", 1.0, 1.5, 1.3),
    AgentProfile("contrarian", 0.6, 0.75, 0.9),
    AgentProfile("beginner", 0.5, 0.5, 0.8),
    AgentProfile("overtrader", 0.95, 1.25, 1.1),
)


@dataclass(frozen=True)
class AgentResult:
    profile: str
    pnl: float
    trades: int
    drawdown: float
    risk_ok: bool


@dataclass(frozen=True)
class SimulationReport:
    agents: tuple[AgentResult, ...]
    mean_pnl: float
    profitable_pct: float
    risk_failures: int
    worlds_tested: int


def _agent_config(base_cfg: dict, profile: AgentProfile) -> dict:
    cfg = dict(base_cfg)
    cfg["strategy"] = dict(base_cfg["strategy"])
    cfg["risk"] = dict(base_cfg["risk"])
    cfg["name"] = f"{base_cfg['name']}_{profile.name}"
    cfg["strategy"]["params"] = dict(base_cfg["strategy"].get("params", {}))
    base_qty = int(base_cfg["strategy"]["quantity"])
    cfg["strategy"]["quantity"] = max(1, int(round(base_qty * profile.quantity_multiplier)))
    base_target = base_cfg["strategy"].get("target_pct")
    if base_target is not None:
        cfg["strategy"]["target_pct"] = max(0.01, float(base_target) * profile.target_multiplier)
    return validate_config(cfg)


def simulate_agents(
    base_cfg: dict,
    *,
    worlds: int = 3,
    days: int = 10,
    seed: int = 100,
    profiles: tuple[AgentProfile, ...] = PROFILES,
    on_agent: Callable[[AgentResult], None] | None = None,
) -> SimulationReport:
    """Run bounded synthetic users through existing fake-market infrastructure.

    Agent traits are recorded as simulation metadata; strategy behavior remains
    deterministic and uses the existing TradeALGO backtester. This avoids
    pretending that arbitrary persona parameters magically create trading logic.
    """
    if worlds < 1 or days < 1:
        raise ValueError("worlds and days must be at least 1.")
    cfg = validate_config(base_cfg)
    results: list[AgentResult] = []

    for profile_index, profile in enumerate(profiles):
        agent_cfg = _agent_config(cfg, profile)
        report = run_lab(
            agent_cfg,
            worlds_per_regime=worlds,
            days=days,
            seed=seed + profile_index * 10000,
            control_worlds=0,
        )
        for row in report.runs.itertuples(index=False):
            result = AgentResult(
                profile=profile.name,
                pnl=float(row.net_pnl),
                trades=int(row.trades),
                drawdown=float(row.max_drawdown),
                risk_ok=not bool(row.violations),
            )
            results.append(result)
            if on_agent:
                on_agent(result)

    if not results:
        return SimulationReport((), 0.0, 0.0, 0, 0)

    pnl = [r.pnl for r in results]
    return SimulationReport(
        tuple(results),
        sum(pnl) / len(pnl),
        sum(v > 0 for v in pnl) / len(pnl) * 100.0,
        sum(not r.risk_ok for r in results),
        len(results),
    )
