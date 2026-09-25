import pandas as pd
import pytest

from algobot.auto_tester import (
    build_scanner_candidates,
    estimate_scanner_count,
    rank_scanner_rows,
    score_result,
)
from algobot.config import validate_config
from algobot.data import generate_sample_data
from algobot.engine import run_backtest
from algobot.strategy import build_strategy
from algobot.strategy_library import TEMPLATES, template_combos

BASE_CFG = validate_config({
    "name": "base",
    "capital": 100000,
    "strategy": {"name": "rules", "params": {}, "quantity": 10, "allow_short": True},
})


def test_every_template_builds_a_usable_ruleset():
    for key, tmpl in TEMPLATES.items():
        combos = template_combos(key, max_combos=2)
        assert combos, f"{key} produced no valid parameter combinations"
        for combo in combos:
            params = tmpl.build(**combo)
            assert "entry_long" in params or "entry_short" in params


def test_build_scanner_candidates_spans_templates_and_is_bounded():
    keys = ["ema_crossover", "rsi_reversion", "pivot_bounce"]
    candidates = build_scanner_candidates(BASE_CFG, keys, max_per_template=3,
                                          stop_values=[0.5], target_values=[1.0])
    seen_keys = {c["_template_key"] for c in candidates}
    assert seen_keys == set(keys)
    for key in keys:
        assert sum(1 for c in candidates if c["_template_key"] == key) <= 3


def test_estimate_scanner_count_matches_actual_build():
    keys = ["ema_crossover", "donchian_breakout"]
    est = estimate_scanner_count(keys, max_per_template=2, stop_count=2, target_count=1)
    candidates = build_scanner_candidates(
        BASE_CFG, keys, max_per_template=2, stop_values=[0.5, 1.0], target_values=[1.0],
    )
    assert len(candidates) == est


def test_score_result_penalizes_too_few_trades():
    assert score_result({"trades": 2, "sharpe_daily": 5.0}, min_trades=5) == float("-inf")
    assert score_result({"trades": 10, "sharpe_daily": 1.0, "profit_factor": 1.5,
                         "max_drawdown_pct": -5.0, "expectancy_per_trade": 20.0}) > 0


def test_rank_scanner_rows_sorts_best_first():
    rows = [{"score": 1.0}, {"score": 5.0}, {"score": -1.0}]
    ranked = rank_scanner_rows(rows)
    assert [r["score"] for r in ranked] == [5.0, 1.0, -1.0]


def test_a_template_runs_end_to_end_on_sample_data():
    df = generate_sample_data(days=20, seed=7)
    cfg = build_scanner_candidates(
        BASE_CFG, ["ema_crossover"], max_per_template=1, stop_values=[0.5], target_values=[1.0],
    )[0]
    strategy = build_strategy(cfg)
    result = run_backtest(df, cfg, strategy)
    assert isinstance(result.metrics, dict)
    assert "trades" in result.metrics
