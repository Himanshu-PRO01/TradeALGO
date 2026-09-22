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
    return m
