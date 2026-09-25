"""Pure helpers for the Auto Tester research page."""
from __future__ import annotations

import copy
import itertools
from typing import Iterable

from .config import validate_config


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
