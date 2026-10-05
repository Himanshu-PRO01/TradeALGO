from algobot.agent_research import run_agent_research
from algobot.config import load_config
from pathlib import Path


def test_agents_actually_test_and_select_candidates():
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(root / "configs" / "demo_rules.yaml")
    report = run_agent_research(
        cfg, generations=1, candidates_per_agent=1, days=2, seed=1701
    )
    assert report.candidates_tested == 8
    assert len(report.scores) == 8
    assert all(s.train_trades >= 0 and s.holdout_trades >= 0 for s in report.scores)
    assert report.verdict
