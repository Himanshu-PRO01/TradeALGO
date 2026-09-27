"""Performance metrics computed from the trade list and equity curve."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def compute_metrics(trades: pd.DataFrame, equity: pd.Series, capital: float) -> dict:
    n = len(trades)
    end_equity = float(equity.iloc[-1]) if len(equity) else float(capital)
    m: dict = {
        "trades": n,
        "start_capital": float(capital),
        "end_equity": end_equity,
        "net_pnl": end_equity - float(capital),
        "return_pct": (end_equity / float(capital) - 1.0) * 100.0,
        "gross_pnl": 0.0,
        "total_costs": 0.0,
        "win_rate_pct": None,
        "avg_win": None,
        "avg_loss": None,
        "profit_factor": None,
        "expectancy_per_trade": None,
        "max_drawdown": 0.0,
        "max_drawdown_pct": 0.0,
        "sharpe_daily": None,
        "days_traded": 0,
        "max_win_streak": 0,
        "max_loss_streak": 0,
        "exposure_pct": 0.0,
    }

    if len(equity):
        running_max = equity.cummax()
        drawdown = equity - running_max
        m["max_drawdown"] = float(drawdown.min())
        m["max_drawdown_pct"] = float((drawdown / running_max).min() * 100.0)
        daily = equity.groupby(equity.index.date).last()
        rets = daily.pct_change().dropna()
        if len(rets) >= 2 and rets.std() > 0:
            m["sharpe_daily"] = float(rets.mean() / rets.std() * math.sqrt(252))

    if n:
        net = trades["net_pnl"]
        wins, losses = net[net > 0], net[net <= 0]
        m["gross_pnl"] = float(trades["gross_pnl"].sum())
        m["total_costs"] = float(trades["costs"].sum())
        m["win_rate_pct"] = float(len(wins) / n * 100.0)
        m["avg_win"] = float(wins.mean()) if len(wins) else 0.0
        m["avg_loss"] = float(losses.mean()) if len(losses) else 0.0
        loss_sum = abs(float(losses.sum()))
        m["profit_factor"] = float(wins.sum() / loss_sum) if loss_sum > 0 else (
            float("inf") if len(wins) else None
        )
        m["expectancy_per_trade"] = float(net.mean())
        m["days_traded"] = int(pd.to_datetime(trades["entry_time"]).dt.date.nunique())
        m["max_win_streak"], m["max_loss_streak"] = _streaks(net)
        m["exposure_pct"] = _exposure_pct(trades, equity)
    return m


def _streaks(net_pnl: pd.Series) -> tuple[int, int]:
    """Longest run of consecutive winning trades, and of consecutive non-winning
    trades, in the order the trades happened (a trade with net_pnl == 0 counts
    as a loss for this purpose, matching win_rate_pct's win/loss split above)."""
    best_win = cur_win = 0
    best_loss = cur_loss = 0
    for pnl in net_pnl:
        if pnl > 0:
            cur_win += 1
            cur_loss = 0
        else:
            cur_loss += 1
            cur_win = 0
        best_win = max(best_win, cur_win)
        best_loss = max(best_loss, cur_loss)
    return best_win, best_loss


def _exposure_pct(trades: pd.DataFrame, equity: pd.Series) -> float:
    """Percentage of the tested time span spent holding a position (either side).
    Approximate by design: it sums each trade's own entry-to-exit duration, which
    slightly overlaps square-off/day-boundary artifacts by at most one bar per
    trade -- fine for a "how much of the time was capital at risk" read, not a
    precision timing metric. Needs both entry_time and exit_time on the trades
    frame; callers that only pass a minimal frame (just net_pnl, say) get 0.0
    back instead of a KeyError, same as the other stats above degrade quietly."""
    if trades.empty or len(equity) < 2:
        return 0.0
    if "entry_time" not in trades.columns or "exit_time" not in trades.columns:
        return 0.0
    total_span = (equity.index[-1] - equity.index[0]).total_seconds()
    if total_span <= 0:
        return 0.0
    entry = pd.to_datetime(trades["entry_time"])
    exit_ = pd.to_datetime(trades["exit_time"])
    held_seconds = (exit_ - entry).dt.total_seconds().clip(lower=0).sum()
    return float(min(held_seconds / total_span * 100.0, 100.0))
