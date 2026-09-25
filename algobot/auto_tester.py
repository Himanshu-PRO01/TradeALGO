"""Pure helpers for the Auto Tester research page."""
from __future__ import annotations

import copy
import itertools
from typing import Iterable

from .config import validate_config
from .strategy_library import TEMPLATES, template_combos


def build_period_values(period_min: int, period_max: int, period_step: int) -> list[int]:
    if period_min > period_max:
        raise ValueError("Period minimum must be less than or equal to period maximum.")
    if period_step < 1:
        raise ValueError("Period step must be at least 1.")
    values = list(range(int(period_min), int(period_max) + 1, int(period_step)))
    if not values:
        raise ValueError("The period range produced no values.")
    return values


def build_candidate_grid(
    period_values: Iterable[int],
    selected_indicators: Iterable[str],
    stop_values: Iterable[float],
    target_values: Iterable[float],
    max_candidates: int,
    base_stop_loss: float | None,
    base_target: float | None,
) -> list[tuple[tuple[int, ...], float, float]]:
    if max_candidates < 1:
        raise ValueError("max_candidates must be at least 1.")
    periods = tuple(int(v) for v in period_values)
    indicators = tuple(selected_indicators)
    stops = tuple(float(v) for v in stop_values) or (float(base_stop_loss or 0.5),)
    targets = tuple(float(v) for v in target_values) or (float(base_target or 1.0),)
    combos = itertools.product(periods, repeat=len(indicators)) if indicators else [()]
    candidates = []
    for combo in combos:
        for stop_loss in stops:
            for target in targets:
                candidates.append((tuple(combo), stop_loss, target))
                if len(candidates) >= int(max_candidates):
                    return candidates
    return candidates


def estimate_candidate_count(period_values: Iterable[int], selected_indicator_count: int,
                             stop_count: int, target_count: int) -> int:
    if selected_indicator_count < 0:
        raise ValueError("selected_indicator_count cannot be negative.")
    period_count = len(tuple(period_values))
    combinations = period_count ** selected_indicator_count if selected_indicator_count else 1
    return max(1, combinations) * max(1, stop_count) * max(1, target_count)


def make_candidate(base_cfg: dict, selected_indicators: Iterable[str],
                   period_combo: Iterable[int], stop_loss: float, target: float,
                   candidate_number: int) -> dict:
    selected = tuple(selected_indicators)
    combo = tuple(int(v) for v in period_combo)
    if len(selected) != len(combo):
        raise ValueError("Each selected indicator must have exactly one period value.")
    cfg = copy.deepcopy(base_cfg)
    cfg["name"] = f"auto_{candidate_number}"
    cfg["strategy"]["stop_loss_pct"] = float(stop_loss)
    cfg["strategy"]["target_pct"] = float(target)
    lookup = dict(zip(selected, combo))
    for indicator in cfg["strategy"]["params"].get("indicators", []):
        if isinstance(indicator, dict) and indicator.get("name") in lookup:
            indicator["period"] = lookup[indicator["name"]]
    return validate_config(cfg)


# ------------------------------------------------------ multi-strategy scanner

def build_scanner_candidates(
    base_cfg: dict,
    template_keys: Iterable[str],
    max_per_template: int,
    stop_values: Iterable[float],
    target_values: Iterable[float],
) -> list[dict]:
    """Build candidate configs across MANY strategy templates and their
    parameters -- a wide, bounded search across strategy families, not a
    single strategy's parameter sweep. (No search is ever truly infinite;
    `max_per_template` caps each family so a run finishes in reasonable time.)

    Returns validated configs, each carrying '_template_key' and
    '_template_label' for grouping/labeling in the results table.
    """
    if int(max_per_template) < 1:
        raise ValueError("max_per_template must be at least 1.")
    stops = tuple(float(v) for v in stop_values) or (0.5,)
    targets = tuple(float(v) for v in target_values) or (1.0,)

    candidates = []
    counter = 0
    for key in template_keys:
        tmpl = TEMPLATES[key]
        combos = template_combos(key, max_combos=int(max_per_template))
        for combo in combos:
            params = tmpl.build(**combo)
            for stop_loss, target in itertools.product(stops, targets):
                counter += 1
                cfg = copy.deepcopy(base_cfg)
                cfg["name"] = f"{key}_{counter}"
                cfg["strategy"]["name"] = "rules"
                cfg["strategy"]["params"] = params
                cfg["strategy"]["stop_loss_pct"] = float(stop_loss)
                cfg["strategy"]["target_pct"] = float(target)
                cfg = validate_config(cfg)
                cfg["_template_key"] = key
                cfg["_template_label"] = tmpl.label
                cfg["_params"] = dict(combo, stop_loss_pct=stop_loss, target_pct=target)
                candidates.append(cfg)
    return candidates


def estimate_scanner_count(template_keys: Iterable[str], max_per_template: int,
                           stop_count: int, target_count: int) -> int:
    n_templates = len(list(template_keys))
    return n_templates * max(1, int(max_per_template)) * max(1, stop_count) * max(1, target_count)


def score_result(metrics: dict, min_trades: int = 5) -> float:
    """A single ranking score combining risk-adjusted return and consistency.

    This is a heuristic, not a law of markets: it exists to sort a leaderboard,
    not to certify a winner. Candidates with fewer than `min_trades` trades are
    scored -inf (a handful of trades is noise, not evidence of an edge).
    """
    if metrics.get("trades", 0) < min_trades:
        return float("-inf")
    sharpe = metrics.get("sharpe_daily") or 0.0
    profit_factor = metrics.get("profit_factor")
    profit_factor = 0.0 if profit_factor is None else min(profit_factor, 5.0)
    drawdown_pct = abs(metrics.get("max_drawdown_pct") or 0.0)
    expectancy = metrics.get("expectancy_per_trade") or 0.0
    return (sharpe * 10.0) + (profit_factor * 5.0) + expectancy - (drawdown_pct * 0.5)


def rank_scanner_rows(rows: list[dict]) -> list[dict]:
    """Sort scanner result rows best-first by `score`, descending."""
    return sorted(rows, key=lambda r: r.get("score", float("-inf")), reverse=True)
