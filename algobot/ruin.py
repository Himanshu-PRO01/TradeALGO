"""Risk of ruin: how likely is a small account to be wrecked by a normal losing streak?

Even a strategy with a genuine edge loses several times in a row. Whether the
account survives depends on how much is risked per trade, not only on how
good the strategy is. This simulates many possible sequences of trades.

Model: each trade wins with probability `win_rate` and gains `reward_r` times
the amount risked, otherwise it loses exactly the amount risked (1R). `cost_r`
is the cost of the trade measured in R (charges of Rs 100 on Rs 1,000 risked
is 0.1R). The amount risked is a fixed share of the STARTING capital
(fixed_rupee=True, like "never lose more than Rs 1,000 a trade") or a share
of the current account (fixed_rupee=False).
"""
from __future__ import annotations

import numpy as np


def expected_value_r(win_rate: float, reward_r: float, cost_r: float = 0.0) -> float:
    """Average result per trade in R (positive = an edge, after costs)."""
    return win_rate * reward_r - (1.0 - win_rate) - cost_r


def breakeven_win_rate(reward_r: float, cost_r: float = 0.0) -> float:
    """The win rate below which the strategy loses money, for a given reward:risk."""
    return (1.0 + cost_r) / (1.0 + reward_r)


def simulate_ruin(
    win_rate: float, reward_r: float, risk_pct: float, n_trades: int = 100, ruin_loss_pct: float = 50.0,
    cost_r: float = 0.0, n_paths: int = 5000, seed: int = 1, fixed_rupee: bool = True,
) -> dict:
    if not 0.0 < win_rate < 1.0:
        raise ValueError("win_rate must be between 0 and 1 (for example 0.45)")
    if reward_r <= 0:
        raise ValueError("reward_r must be above 0 (average win as a multiple of the amount risked)")
    if not 0.0 < risk_pct < 100.0:
        raise ValueError("risk_pct must be between 0 and 100 (percent of capital risked per trade)")
    if n_trades < 1 or n_paths < 1:
        raise ValueError("n_trades and n_paths must be 1 or more")
    if not 0.0 < ruin_loss_pct < 100.0:
        raise ValueError("ruin_loss_pct must be between 0 and 100")
    if cost_r < 0:
        raise ValueError("cost_r cannot be negative")

    rng = np.random.default_rng(seed)
    wins = rng.random((n_paths, n_trades)) < win_rate
    pnl_r = np.where(wins, reward_r, -1.0) - cost_r
    step = pnl_r * (risk_pct / 100.0)
    equity = 1.0 + np.cumsum(step, axis=1) if fixed_rupee else np.cumprod(1.0 + step, axis=1)
    # An account cannot go below zero: once it is empty it stays empty.
    equity = np.where(np.maximum.accumulate(equity <= 0.0, axis=1), 0.0, equity)
    floor = 1.0 - ruin_loss_pct / 100.0
    final = equity[:, -1]
    return {
        "expected_value_r": expected_value_r(win_rate, reward_r, cost_r),
        "breakeven_win_rate": breakeven_win_rate(reward_r, cost_r),
        "p_ruin": float((equity.min(axis=1) <= floor).mean()),
        "p_loss": float((final < 1.0).mean()),
        "final_median_pct": float((np.median(final) - 1.0) * 100.0),
        "final_p5_pct": float((np.percentile(final, 5) - 1.0) * 100.0),
        "final_p95_pct": float((np.percentile(final, 95) - 1.0) * 100.0),
        "worst_streak_median": float(np.median(_longest_loss_run(~wins))),
    }


def _longest_loss_run(losses: np.ndarray) -> np.ndarray:
    """Longest run of consecutive losses in each simulated path."""
    best = np.zeros(losses.shape[0], dtype=int)
    current = np.zeros(losses.shape[0], dtype=int)
    for k in range(losses.shape[1]):
        current = np.where(losses[:, k], current + 1, 0)
        best = np.maximum(best, current)
    return best


def format_ruin(res: dict, win_rate: float, reward_r: float, risk_pct: float, n_trades: int, ruin_loss_pct: float) -> str:
    edge = res["expected_value_r"]
    lines = [
        f"Assumptions: win rate {win_rate:.0%}, average win {reward_r:g}R, risk {risk_pct:g}% of capital per trade, "
        f"{n_trades} trades.",
        f"Average result per trade: {edge:+.2f}R  ({'an edge' if edge > 0 else 'NO edge: this loses money on average'}). "
        f"Break-even win rate at this reward: {res['breakeven_win_rate']:.0%}.",
        f"Chance of losing {ruin_loss_pct:g}% of the account at some point: {res['p_ruin']:.0%}",
        f"Chance of finishing with a loss: {res['p_loss']:.0%}",
        f"Final result: median {res['final_median_pct']:+.0f}% of capital, "
        f"worst 1 in 20 {res['final_p5_pct']:+.0f}%, best 1 in 20 {res['final_p95_pct']:+.0f}%.",
        f"Typical longest losing streak: {res['worst_streak_median']:.0f} trades in a row.",
    ]
    return "\n".join(lines)
