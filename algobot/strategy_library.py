"""A library of strategy templates for the Strategy Scanner / Auto Tester.

Every template is expressed as `rules`-strategy indicators + expressions
(see strategy.py) so no new Strategy subclasses are needed to add one: the
scanner just fills in a param_grid and lets the existing rule engine and
backtester do the work.

These are common, well-known intraday building blocks (crossover, mean
reversion, breakout). They are DEMOS of shape, not recommendations, and a
"winner" on one data set is not a promise for tomorrow -- see the caveats
printed on the Strategy Scanner page.
"""
from __future__ import annotations

import itertools
from typing import Callable, NamedTuple


class StrategyTemplate(NamedTuple):
    key: str
    label: str
    description: str
    param_grid: dict  # param name -> list of candidate values
    build: Callable[..., dict]  # (**params) -> strategy.params dict


def _combos(param_grid: dict) -> list[dict]:
    if not param_grid:
        return [{}]
    keys = list(param_grid)
    out = []
    for values in itertools.product(*(param_grid[k] for k in keys)):
        out.append(dict(zip(keys, values)))
    return out


# --------------------------------------------------------------------- builds

def _ema_crossover(fast: int, slow: int) -> dict:
    if fast >= slow:
        raise ValueError("fast must be < slow")
    return {
        "indicators": [
            {"name": "ema_fast", "type": "ema", "period": fast},
            {"name": "ema_slow", "type": "ema", "period": slow},
        ],
        "entry_long": "ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev",
        "exit_long": "ema_fast < ema_slow",
        "entry_short": "ema_fast < ema_slow and ema_fast_prev >= ema_slow_prev",
        "exit_short": "ema_fast > ema_slow",
    }


def _sma_crossover(fast: int, slow: int) -> dict:
    if fast >= slow:
        raise ValueError("fast must be < slow")
    return {
        "indicators": [
            {"name": "sma_fast", "type": "sma", "period": fast},
            {"name": "sma_slow", "type": "sma", "period": slow},
        ],
        "entry_long": "sma_fast > sma_slow and sma_fast_prev <= sma_slow_prev",
        "exit_long": "sma_fast < sma_slow",
        "entry_short": "sma_fast < sma_slow and sma_fast_prev >= sma_slow_prev",
        "exit_short": "sma_fast > sma_slow",
    }


def _rsi_reversion(period: int, oversold: int, overbought: int) -> dict:
    if oversold >= overbought:
        raise ValueError("oversold must be < overbought")
    return {
        "indicators": [{"name": "rsi_v", "type": "rsi", "period": period}],
        "entry_long": f"rsi_v < {oversold} and rsi_v_prev >= {oversold}",
        "exit_long": f"rsi_v > 50",
        "entry_short": f"rsi_v > {overbought} and rsi_v_prev <= {overbought}",
        "exit_short": f"rsi_v < 50",
    }


def _vwap_reversion(band_pct: float) -> dict:
    return {
        "indicators": [{"name": "vwap_v", "type": "vwap"}],
        "entry_long": f"close < vwap_v * (1 - {band_pct / 100.0})",
        "exit_long": "close > vwap_v",
        "entry_short": f"close > vwap_v * (1 + {band_pct / 100.0})",
        "exit_short": "close < vwap_v",
    }


def _donchian_breakout(period: int) -> dict:
    return {
        "indicators": [
            {"name": "hh", "type": "highest", "period": period},
            {"name": "ll", "type": "lowest", "period": period},
        ],
        "entry_long": "close > hh and close_prev <= hh_prev",
        "exit_long": "close < ll",
        "entry_short": "close < ll and close_prev >= ll_prev",
        "exit_short": "close > hh",
    }


def _orb_breakout(minutes: int) -> dict:
    return {
        "indicators": [
            {"name": "orh", "type": "opening_range_high", "period": minutes},
            {"name": "orl", "type": "opening_range_low", "period": minutes},
            {"name": "piv", "type": "pivot"},
        ],
        "entry_long": "close > orh and close_prev <= orh_prev and close > piv",
        "exit_long": "close < orh",
        "entry_short": "close < orl and close_prev >= orl_prev and close < piv",
        "exit_short": "close > orl",
    }


def _pivot_bounce() -> dict:
    return {
        "indicators": [
            {"name": "piv", "type": "pivot"},
            {"name": "r1", "type": "pivot_r1"},
            {"name": "s1", "type": "pivot_s1"},
        ],
        "entry_long": "close > s1 and close_prev <= s1_prev",
        "exit_long": "close > r1 or close < s1",
        "entry_short": "close < r1 and close_prev >= r1_prev",
        "exit_short": "close < s1 or close > r1",
    }


# --------------------------------------------------------------------- library

TEMPLATES: dict[str, StrategyTemplate] = {
    "ema_crossover": StrategyTemplate(
        "ema_crossover", "EMA crossover", "Trend-following: fast EMA crosses slow EMA.",
        {"fast": [5, 9, 12, 20], "slow": [20, 30, 50, 100]}, _ema_crossover,
    ),
    "sma_crossover": StrategyTemplate(
        "sma_crossover", "SMA crossover", "Trend-following: fast SMA crosses slow SMA.",
        {"fast": [5, 10, 20], "slow": [30, 50, 100]}, _sma_crossover,
    ),
    "rsi_reversion": StrategyTemplate(
        "rsi_reversion", "RSI mean-reversion", "Fade RSI extremes back toward 50.",
        {"period": [7, 14, 21], "oversold": [20, 25, 30], "overbought": [70, 75, 80]},
        _rsi_reversion,
    ),
    "vwap_reversion": StrategyTemplate(
        "vwap_reversion", "VWAP mean-reversion", "Fade price back toward the session VWAP.",
        {"band_pct": [0.3, 0.5, 0.75, 1.0]}, _vwap_reversion,
    ),
    "donchian_breakout": StrategyTemplate(
        "donchian_breakout", "Donchian channel breakout", "Buy/sell new N-bar highs/lows.",
        {"period": [10, 20, 30, 55]}, _donchian_breakout,
    ),
    "orb_breakout": StrategyTemplate(
        "orb_breakout", "Opening-range breakout", "Break of the first N minutes' range, filtered by pivot.",
        {"minutes": [5, 15, 30]}, _orb_breakout,
    ),
    "pivot_bounce": StrategyTemplate(
        "pivot_bounce", "Pivot S1/R1 bounce", "Buy a bounce off S1, sell a rejection at R1.",
        {}, _pivot_bounce,
    ),
}


def template_combos(key: str, max_combos: int | None = None) -> list[dict]:
    """All (or the first `max_combos`) parameter combinations for a template,
    silently skipping combinations the builder itself rejects (e.g. fast>=slow)."""
    tmpl = TEMPLATES[key]
    out = []
    for combo in _combos(tmpl.param_grid):
        try:
            tmpl.build(**combo)
        except ValueError:
            continue
        out.append(combo)
        if max_combos is not None and len(out) >= max_combos:
            break
    return out
