from pathlib import Path
from algobot.mirofish_qa import build_strategy_evidence, run_website_swarm, SAFE_PAGES
from algobot.config import load_config

def test_strategy_evidence_is_deterministic():
    cfg=load_config(Path(__file__).resolve().parents[1]/"configs"/"demo_rules.yaml")
    a=build_strategy_evidence(cfg,rounds=6,days=2,seed=11)
    b=build_strategy_evidence(cfg,rounds=6,days=2,seed=11)
    assert a==b
    assert len(a.evidence)==6 and a.graph_nodes>0 and a.graph_edges>0 and a.verdict

def test_website_swarm_allowlist_excludes_execution_pages():
    assert all("Live" not in p and "OpenAlgo" not in p for p in SAFE_PAGES)

def test_website_swarm_executes_safely():
    root = Path(__file__).resolve().parents[1]
    res = run_website_swarm(root, agents=1, max_pages=1, action_rounds=1, timeout=20.0)
    assert res.journeys_tested >= 1
    assert res.pass_rate == 100.0
    assert not res.safety_violations
