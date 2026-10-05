"""Full MiroFish-style, safety-bounded QA and strategy orchestration for TradeALGO.

Independent implementation inspired by the architecture of reality seed -> personas ->
memory/graph -> interaction -> report -> deep inspection. No broker, credential,
OpenAlgo, or live-order surface is ever exercised.
"""
from __future__ import annotations
from dataclasses import dataclass
import time
from pathlib import Path

SAFE_PAGES = (
    "5_Backtest.py", "6_Reality_check.py", "7_Test_lab.py",
    "15_Strategy_Scanner.py", "27_Agent_Simulation_Lab.py", "28_Swarm_Simulation_Lab.py",
)
SAFE_ACTION_WORDS = ("run","test","scan","backtest","reality","simulate","research","refresh","validate","check","calculate")
BLOCKED_ACTION_WORDS = ("live","order","broker","openalgo","execute","buy","sell","place order","credentials","token","api key")

@dataclass(frozen=True)
class WebsiteAgent:
    agent_id: str
    persona: str
    patience: int
    aggression: float
    exploration: float
    page_budget: int

WEBSITE_AGENTS = (
    WebsiteAgent("web-001","beginner",3,.20,.75,4),
    WebsiteAgent("web-002","risk_manager",5,.05,.55,5),
    WebsiteAgent("web-003","momentum_trader",3,.75,.65,4),
    WebsiteAgent("web-004","contrarian",5,.45,.90,5),
    WebsiteAgent("web-005","optimizer",6,.55,1.00,6),
    WebsiteAgent("web-006","impatient",2,.90,.55,3),
    WebsiteAgent("web-007","power_user",8,.65,1.00,6),
    WebsiteAgent("web-008","adversarial_tester",8,.50,1.00,6),
)

@dataclass(frozen=True)
class WebsiteJourney:
    agent_id: str
    persona: str
    page: str
    loaded: bool
    exception: str | None
    visible_errors: tuple[str,...]
    actions_attempted: int
    actions_completed: int
    blocked_actions: tuple[str,...]
    duration_ms: float

@dataclass(frozen=True)
class WebsiteSwarmResult:
    journeys: tuple[WebsiteJourney,...]
    pages_tested: int
    journeys_tested: int
    pass_rate: float
    action_success_rate: float
    repeated_failures: tuple[str,...]
    safety_violations: tuple[str,...]
    findings: tuple[str,...]

def _page_path(root: Path, page: str) -> Path:
    path = root / "pages" / page
    if not path.exists(): raise FileNotFoundError(str(path))
    return path

def _safe_buttons(app) -> list:
    out=[]
    for button in list(app.button):
        label=str(getattr(button,"label","") or "").strip()
        low=label.lower()
        if any(w in low for w in BLOCKED_ACTION_WORDS): continue
        if any(w in low for w in SAFE_ACTION_WORDS): out.append(button)
    return out

def _visible_errors(app) -> tuple[str,...]:
    out=[]
    for collection in (getattr(app,"error",[]), getattr(app,"exception",[])):
        for item in list(collection):
            value=str(getattr(item,"value",item))
            if value: out.append(value[:300])
    return tuple(out)

def run_website_swarm(root: str|Path, *, agents:int=8, max_pages:int=6,
                      action_rounds:int=2, timeout:float=20.0) -> WebsiteSwarmResult:
    """Execute synthetic-user journeys through Streamlit AppTest on research pages only."""
    try:
        from streamlit.testing.v1 import AppTest
    except Exception as exc:
        raise RuntimeError("Streamlit AppTest is unavailable") from exc
    root=Path(root).resolve()
    cohort=WEBSITE_AGENTS[:max(1,min(agents,len(WEBSITE_AGENTS)))]
    journeys=[]
    for agent in cohort:
        pages=SAFE_PAGES[:min(max_pages,agent.page_budget)]
        for page in pages:
            started=time.perf_counter(); loaded=False; exception=None
            blocked=[]; attempted=completed=0; errors=()
            try:
                app=AppTest.from_file(str(_page_path(root,page)))
                app.run(timeout=timeout)
                loaded=len(getattr(app,"exception",[]))==0
                errors=_visible_errors(app)
                for _ in range(max(0,action_rounds)):
                    candidates=_safe_buttons(app)
                    if not candidates: break
                    take=max(1,min(len(candidates),1+int(agent.exploration*2)))
                    for button in candidates[:take]:
                        label=str(getattr(button,"label","") or "").strip()
                        if any(w in label.lower() for w in BLOCKED_ACTION_WORDS):
                            blocked.append(label); continue
                        attempted+=1
                        button.click(); app.run(timeout=timeout); completed+=1
                        errors=_visible_errors(app)
                        if errors: break
                    if errors: break
            except Exception as exc:
                exception=f"{type(exc).__name__}: {exc}"[:500]; loaded=False
            journeys.append(WebsiteJourney(
                agent.agent_id,agent.persona,page,loaded,exception,errors,
                attempted,completed,tuple(blocked),(time.perf_counter()-started)*1000))
    passed=sum(j.loaded and j.exception is None and not j.visible_errors for j in journeys)
    attempted=sum(j.actions_attempted for j in journeys); completed=sum(j.actions_completed for j in journeys)
    counts={}
    for j in journeys:
        if j.exception:
            key=f"{j.page}: {j.exception.splitlines()[-1][:180]}"; counts[key]=counts.get(key,0)+1
        for error in j.visible_errors:
            key=f"{j.page}: visible error: {error[:180]}"; counts[key]=counts.get(key,0)+1
    repeated=tuple(k for k,v in sorted(counts.items(),key=lambda x:-x[1]) if v>=2)
    safety=tuple(f"{j.agent_id}/{j.page}: attempted blocked action {label}" for j in journeys for label in j.blocked_actions)
    findings=[
        f"Executed {len(journeys)} synthetic-user journeys across {len(set(j.page for j in journeys))} research pages.",
        f"Page journey pass rate: {passed/len(journeys)*100:.1f}%." if journeys else "No journeys executed.",
        f"Safe research action completion: {completed/attempted*100:.1f}%." if attempted else "No clickable research actions were available.",
        f"Average journey time: {sum(j.duration_ms for j in journeys)/len(journeys):.0f} ms." if journeys else "",
    ]
    if repeated: findings.append(f"{len(repeated)} failure pattern(s) repeated across agents.")
    if safety: findings.append("A safety filter encountered blocked controls; no blocked control was clicked.")
    return WebsiteSwarmResult(tuple(journeys),len(set(j.page for j in journeys)),len(journeys),
        passed/len(journeys)*100 if journeys else 0.0,completed/attempted*100 if attempted else 100.0,
        repeated,safety,tuple(x for x in findings if x))

@dataclass(frozen=True)
class StrategyEvidence:
    source: str
    regime: str
    pnl: float
    trades: int
    profit_factor: float
    drawdown: float
    passed: bool

@dataclass(frozen=True)
class MiroFishStrategyReport:
    evidence: tuple[StrategyEvidence,...]
    mean_pnl: float
    profitable_rate: float
    mean_profit_factor: float
    worst_drawdown: float
    consensus: float
    consensus_strength: float
    graph_nodes: int
    graph_edges: int
    failure_modes: tuple[str,...]
    verdict: str

def build_strategy_evidence(cfg: dict, *, rounds:int=12, days:int=8, seed:int=9001) -> MiroFishStrategyReport:
    """Create an adversarial MiroFish-style evidence world from independent regimes."""
    from .engine import run_backtest
    from .strategy import build_strategy
    from .worlds import generate_mixed_world
    regimes=("trend","chop","mean_reversion","volatile","shocks","noise")
    evidence=[]
    for i in range(rounds):
        regime=regimes[i%len(regimes)]
        world,_=generate_mixed_world(days=days,seed=seed+i*101,regimes=[regime])
        result=run_backtest(world,cfg,build_strategy(cfg)); m=result.metrics
        pf=float(m.get("profit_factor") or 0.0); pnl=float(m.get("net_pnl",0.0))
        dd=float(m.get("max_drawdown",0.0)); trades=int(m.get("trades",0))
        evidence.append(StrategyEvidence("synthetic-market",regime,pnl,trades,pf,dd,pnl>0 and pf>=1.0))
    pnls=[e.pnl for e in evidence]; pfs=[e.profit_factor for e in evidence]
    stances=[1.0 if e.passed else -1.0 for e in evidence]
    consensus=sum(stances)/len(stances)
    strength=1.0-min(1.0,(max(stances)-min(stances))/2.0) if stances else 0.0
    failures=[]
    if sum(pnls)<=0: failures.append("aggregate synthetic P&L is negative")
    if sum(e.passed for e in evidence)/len(evidence)<.5: failures.append("fewer than half of independent regimes passed")
    if max(abs(e.drawdown) for e in evidence)>max(1.0,abs(sum(pnls))*.75): failures.append("drawdown stress is large relative to aggregate return")
    if any(e.regime=="shocks" and not e.passed for e in evidence): failures.append("shock regime failed")
    if any(e.regime=="noise" and e.passed for e in evidence): failures.append("noise regime passed; investigate possible overfitting")
    if failures: verdict="FAILED — ADVERSARIAL SWARM FOUND WEAKNESS"
    elif consensus>.25 and sum(pfs)/len(pfs)>=1.2: verdict="PROMISING — REQUIRES REAL OOS AND COST ROBUSTNESS"
    else: verdict="UNSTABLE — KEEP RESEARCHING"
    return MiroFishStrategyReport(tuple(evidence),sum(pnls)/len(pnls),sum(e.passed for e in evidence)/len(evidence)*100,
        sum(pfs)/len(pfs),max(abs(e.drawdown) for e in evidence),consensus,strength,
        len(evidence)+len(regimes)+8,len(evidence)*3,tuple(failures),verdict)
