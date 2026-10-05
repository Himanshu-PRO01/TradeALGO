"""Adaptive, bounded MiroFish-style synthetic-user swarm for TradeALGO."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable
import numpy as np
import pandas as pd
from .engine import run_backtest
from .strategy import build_strategy
from .worlds import REGIMES, generate_mixed_world

@dataclass(frozen=True)
class Persona:
    name: str
    goal: str
    risk_tolerance: float
    patience: float
    exploration: float
    error_tolerance: float
    position_bias: float
    preferred_pages: tuple[str, ...]

PERSONAS = (
    Persona("beginner","learn safely",.35,.80,.75,.35,.20,("5_Backtest.py","6_Reality_check.py","16_Paper_Trading.py")),
    Persona("risk_manager","avoid loss and rule violations",.15,.95,.45,.20,-.10,("6_Reality_check.py","1_Position_size.py","7_Test_lab.py")),
    Persona("momentum_trader","find robust trend behavior",.80,.60,.55,.55,.55,("5_Backtest.py","7_Test_lab.py","15_Strategy_Scanner.py")),
    Persona("contrarian","find failure modes",.65,.70,.90,.80,-.45,("6_Reality_check.py","7_Test_lab.py","24_Options_Breakeven.py")),
    Persona("optimizer","compare many scenarios",.70,.85,.95,.65,.15,("7_Test_lab.py","15_Strategy_Scanner.py","13_Auto_Tester.py")),
    Persona("impatient","get a usable answer quickly",.90,.20,.60,.90,.70,("5_Backtest.py","16_Paper_Trading.py")),
    Persona("power_user","stress every safe workflow",.75,.90,1.00,.90,.10,("5_Backtest.py","6_Reality_check.py","7_Test_lab.py","15_Strategy_Scanner.py","16_Paper_Trading.py","17_Sandbox_Rehearsal.py")),
    Persona("adversarial_tester","break unsafe assumptions without trading",.50,.70,1.00,1.00,0.0,("5_Backtest.py","6_Reality_check.py","7_Test_lab.py")),
)

@dataclass
class Memory:
    observations: list[str] = field(default_factory=list)
    beliefs: dict[str,float] = field(default_factory=lambda: {"strategy_quality":.5,"risk_safety":.5,"trend_preference":.5})
    failures: list[str] = field(default_factory=list)
    def remember(self, observation: str) -> None:
        self.observations.append(observation)
        if len(self.observations)>20: del self.observations[:-20]
    def update(self, key: str, evidence: float, rate: float=.25) -> None:
        old=self.beliefs.get(key,.5)
        self.beliefs[key]=float(np.clip(old+rate*(evidence-old),0,1))

@dataclass(frozen=True)
class MarketEpisode:
    regime: str
    seed: int
    pnl: float
    trades: int
    drawdown: float
    risk_ok: bool

@dataclass(frozen=True)
class SwarmAgent:
    id: str
    persona: Persona
    memory: Memory
    episodes: tuple[MarketEpisode,...]
    score: float

@dataclass(frozen=True)
class SwarmReport:
    agents: tuple[SwarmAgent,...]
    episodes: int
    mean_pnl: float
    profitable_pct: float
    risk_failures: int
    consensus: dict[str,float]
    failure_modes: tuple[str,...]

def _risk_ok(result,cfg)->bool:
    trades=result.trades
    if not len(trades): return True
    risk=cfg["risk"]
    entry=pd.to_datetime(trades["entry_time"]); exit_=pd.to_datetime(trades["exit_time"])
    return not ((entry.dt.date!=exit_.dt.date).any() or (entry.dt.time>risk["no_new_entries_after"]).any())

def _score(persona,episodes,memory):
    if not episodes: return 0.0
    pnl=float(np.mean([e.pnl for e in episodes])); dd=float(np.mean([abs(e.drawdown) for e in episodes]))
    safety=float(np.mean([e.risk_ok for e in episodes]))
    stability=1-min(1,float(np.std([e.pnl for e in episodes]))/(abs(pnl)+1000))
    return pnl/1000+2*safety+persona.risk_tolerance*stability-dd/5000

def run_swarm(cfg: dict, *, agents:int=8, rounds:int=4, days_per_round:int=8, seed:int=700,
              personas:Iterable[Persona]=PERSONAS)->SwarmReport:
    """Run adaptive synthetic traders through changing fake worlds."""
    if agents<1 or rounds<1 or days_per_round<2:
        raise ValueError("agents >= 1, rounds >= 1, and days_per_round >= 2 are required.")
    persona_list=tuple(personas)
    if not persona_list: raise ValueError("At least one persona is required.")
    results=[]; all_episodes=[]
    for ai in range(agents):
        persona=persona_list[ai%len(persona_list)]; memory=Memory(); episodes=[]
        for ri in range(rounds):
            bias=float(np.clip(memory.beliefs["trend_preference"]+persona.position_bias*.25,0,1))
            pool=list(REGIMES)
            if bias>.65: pool=["trend","volatile","shocks","chop","noise"]
            elif bias<.35: pool=["mean_reversion","chop","volatile","shocks","noise"]
            episode_seed=seed+ai*100000+ri*1000
            world,segments=generate_mixed_world(days=days_per_round,seed=episode_seed,regimes=pool)
            result=run_backtest(world,cfg,build_strategy(cfg)); pnl=float(result.metrics["net_pnl"])
            dd=float(result.metrics["max_drawdown"]); ok=_risk_ok(result,cfg)
            names=[s[0] for s in segments]
            episode=MarketEpisode("+".join(dict.fromkeys(names)),episode_seed,pnl,int(result.metrics["trades"]),dd,ok)
            episodes.append(episode); all_episodes.append(episode)
            memory.update("strategy_quality",1.0 if pnl>0 else 0.0)
            memory.update("risk_safety",1.0 if ok else 0.0)
            memory.update("trend_preference",1.0 if "trend" in names else 0.0)
            memory.remember(f"round {ri+1}: pnl={pnl:.2f}, dd={dd:.2f}, risk={'ok' if ok else 'failed'}, regimes={episode.regime}")
            if not ok: memory.failures.append(f"round {ri+1}: risk rule violation")
        results.append(SwarmAgent(f"agent-{ai+1:03d}",persona,memory,tuple(episodes),_score(persona,episodes,memory)))
    pnls=[e.pnl for e in all_episodes]
    consensus={k:float(np.mean([a.memory.beliefs[k] for a in results])) for k in ("strategy_quality","risk_safety","trend_preference")}
    failures=[]
    if any(not e.risk_ok for e in all_episodes): failures.append("risk-rule violations appeared in at least one adaptive episode")
    if pnls and np.mean(pnls)<0: failures.append("swarm lost money on average across synthetic worlds")
    if pnls and np.std(pnls)>max(500,abs(np.mean(pnls))*2): failures.append("outcomes were highly unstable across agents/worlds")
    return SwarmReport(tuple(results),len(all_episodes),float(np.mean(pnls)) if pnls else 0.0,
                       float(np.mean(np.array(pnls)>0)*100) if pnls else 0.0,
                       sum(not e.risk_ok for e in all_episodes),consensus,tuple(failures))

SAFE_WEB_PAGES=("5_Backtest.py","6_Reality_check.py","7_Test_lab.py","15_Strategy_Scanner.py")

@dataclass(frozen=True)
class JourneyResult:
    persona:str
    page:str
    loaded:bool
    exception:str|None
    actions:int
    errors:int
    observations:tuple[str,...]

@dataclass(frozen=True)
class WebsiteSwarmReport:
    journeys:tuple[JourneyResult,...]
    pass_rate:float
    repeated_failures:tuple[str,...]

def plan_journey(persona:Persona,budget:int=5)->tuple[str,...]:
    pages=[p for p in persona.preferred_pages if p in SAFE_WEB_PAGES]
    return tuple((pages or ["5_Backtest.py"])[:max(1,budget)])

def summarize_website_journeys(journeys:Iterable[JourneyResult])->WebsiteSwarmReport:
    rows=tuple(journeys)
    if not rows: return WebsiteSwarmReport((),0.0,())
    passed=sum(j.loaded and j.exception is None for j in rows); counts={}
    for j in rows:
        if j.exception:
            key=f"{j.page}: {j.exception.splitlines()[-1][:160]}"; counts[key]=counts.get(key,0)+1
    repeated=tuple(k for k,v in sorted(counts.items(),key=lambda x:-x[1]) if v>1)
    return WebsiteSwarmReport(rows,passed/len(rows)*100,repeated)
