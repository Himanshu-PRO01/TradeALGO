"""Turn a BacktestResult into a readable summary and saved files."""
from __future__ import annotations

import os


from .engine import BacktestResult


def _money(x) -> str:
    return "n/a" if x is None else f"{x:,.2f}"


def _num(x, suffix: str = "") -> str:
    if x is None:
        return "n/a"
    if x == float("inf"):
        return "infinite"
    return f"{x:,.2f}{suffix}"


def summary_text(result: BacktestResult) -> str:
    m = result.metrics
    eq = result.equity
    lines = [
        f"Backtest: {result.name}",
        f"Period:   {eq.index[0]:%Y-%m-%d} to {eq.index[-1]:%Y-%m-%d}  ({len(eq):,} bars)",
        "-" * 56,
        f"Trades:               {m['trades']}   (on {m['days_traded']} days)",
        f"Start capital:        {_money(m['start_capital'])}",
        f"End equity:           {_money(m['end_equity'])}",
        f"Net profit/loss:      {_money(m['net_pnl'])}  ({_num(m['return_pct'], '%')})",
        f"  before costs:       {_money(m['gross_pnl'])}",
        f"  costs paid:         {_money(m['total_costs'])}",
        f"Win rate:             {_num(m['win_rate_pct'], '%')}",
        f"Average win / loss:   {_money(m['avg_win'])} / {_money(m['avg_loss'])}",
        f"Profit factor:        {_num(m['profit_factor'])}",
        f"Expectancy per trade: {_money(m['expectancy_per_trade'])}",
        f"Max drawdown:         {_money(m['max_drawdown'])}  ({_num(m['max_drawdown_pct'], '%')})",
        f"Sharpe (daily, x sqrt 252): {_num(m['sharpe_daily'])}",
    ]
    if len(result.trades):
        reasons = result.trades["exit_reason"].value_counts()
        lines.append("Exits by reason:      " + ", ".join(f"{k}: {v}" for k, v in reasons.items()))
    if result.rejections:
        lines.append(
            "Entries blocked by risk rules: "
            + ", ".join(f"{k}: {v}" for k, v in result.rejections.items())
        )
    for e in result.events:
        lines.append("Risk event: " + e)
    lines.append("-" * 56)
    lines.append("Reminder: a backtest is not a promise. Results are optimistic (see engine.py).")
    return "\n".join(lines)


def save_outputs(result: BacktestResult, outdir: str, plot: bool = True) -> list[str]:
    os.makedirs(outdir, exist_ok=True)
    saved = []
    trades_path = os.path.join(outdir, "trades.csv")
    result.trades.to_csv(trades_path, index=False)
    saved.append(trades_path)
    equity_path = os.path.join(outdir, "equity.csv")
    result.equity.to_csv(equity_path, header=True)
    saved.append(equity_path)
    if plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(range(len(result.equity)), result.equity.to_numpy(), linewidth=1.1)
        ax.set_title(f"Equity curve: {result.name}")
        ax.set_xlabel("Bar number")
        ax.set_ylabel("Equity")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        plot_path = os.path.join(outdir, "equity.png")
        fig.savefig(plot_path, dpi=120)
        plt.close(fig)
        saved.append(plot_path)
    return saved
