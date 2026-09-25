"""Paper trading: run a saved strategy against real (delayed) market prices
and remember what it WOULD have done. No code path here places, modifies, or
cancels a broker order -- see execution_policy.py for the one real switch.

Why a persistent log instead of in-memory state: the free data feed only
looks back a limited window (5 days of 5-minute bars, for example), so this
never tries to replay "since inception". Instead, every check re-runs the
existing backtest engine on whatever window the feed currently has, and only
the trades that finished inside that window and are not already stored get
written down. That means:

  * Restarting the app, switching pages, or a slow/failed refresh never loses
    history -- whatever was already logged stays logged.
  * Re-checking an overlapping window twice is safe: the same finished trade
    is never written twice (enforced by a UNIQUE constraint, not by trusting
    the caller to track what "already happened").
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Optional

import pandas as pd

from .engine import BacktestResult
from .runner import run_from_dict

SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_key     TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    entry_time  TEXT NOT NULL,
    exit_time   TEXT NOT NULL,
    side        TEXT NOT NULL,
    qty         INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    exit_price  REAL NOT NULL,
    gross_pnl   REAL NOT NULL,
    costs       REAL NOT NULL,
    net_pnl     REAL NOT NULL,
    exit_reason TEXT NOT NULL,
    logged_at   TEXT NOT NULL,
    UNIQUE(run_key, entry_time, exit_time)
)
"""


def run_key_for(cfg: dict, symbol_label: str, interval_label: str) -> str:
    """A stable identifier so different strategies/symbols/timeframes don't mix logs."""
    return f"{cfg.get('name', 'unnamed')}::{symbol_label}::{interval_label}"


class PaperLog:
    """Where paper-trade history lives: a file locally, or in-session when hosted."""

    def __init__(self, path: str = ":memory:", check_same_thread: bool = True):
        self.db = sqlite3.connect(path, check_same_thread=check_same_thread)
        self.db.execute(SCHEMA)
        self.db.commit()

    def close_db(self) -> None:
        self.db.close()

    def add_trades(self, run_key: str, symbol: str, rows: list[dict]) -> int:
        """Insert closed trades, silently skipping any already logged. Returns how many were new."""
        before = self.db.total_changes
        for r in rows:
            self.db.execute(
                "INSERT OR IGNORE INTO paper_trades "
                "(run_key, symbol, entry_time, exit_time, side, qty, entry_price, exit_price, "
                " gross_pnl, costs, net_pnl, exit_reason, logged_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (run_key, symbol, str(r["entry_time"]), str(r["exit_time"]), r["side"], int(r["qty"]),
                 float(r["entry_price"]), float(r["exit_price"]), float(r["gross_pnl"]), float(r["costs"]),
                 float(r["net_pnl"]), r["exit_reason"], r["logged_at"]),
            )
        self.db.commit()
        return self.db.total_changes - before

    def all_trades(self, run_key: str) -> pd.DataFrame:
        cols = ["entry_time", "exit_time", "side", "qty", "entry_price", "exit_price",
                "gross_pnl", "costs", "net_pnl", "exit_reason", "logged_at"]
        cur = self.db.execute(
            f"SELECT {', '.join(cols)} FROM paper_trades WHERE run_key = ? ORDER BY exit_time", (run_key,)
        )
        return pd.DataFrame(cur.fetchall(), columns=cols)

    def summary(self, run_key: str) -> dict:
        df = self.all_trades(run_key)
        if df.empty:
            return {"trades": 0, "net": 0.0, "win_rate_pct": None, "best": None, "worst": None}
        wins = int((df["net_pnl"] > 0).sum())
        return {
            "trades": len(df),
            "net": float(df["net_pnl"].sum()),
            "win_rate_pct": wins / len(df) * 100.0,
            "best": float(df["net_pnl"].max()),
            "worst": float(df["net_pnl"].min()),
        }

    def reset(self, run_key: str) -> None:
        self.db.execute("DELETE FROM paper_trades WHERE run_key = ?", (run_key,))
        self.db.commit()


def evaluate(cfg: dict, df: pd.DataFrame) -> BacktestResult:
    """Run the existing (real-money-free) backtest engine on whatever price window is available."""
    return run_from_dict(cfg, df)


def split_open_and_closed(result: BacktestResult) -> tuple[Optional[dict], pd.DataFrame]:
    """The engine always force-closes a still-open position at the last available bar so it can
    report a result; that manufactured close (exit_reason 'end_of_data') is a snapshot of an open
    position, not a real exit, so it must never be logged as a finished trade."""
    trades = result.trades
    if trades.empty:
        return None, trades
    if trades.iloc[-1]["exit_reason"] == "end_of_data":
        return trades.iloc[-1].to_dict(), trades.iloc[:-1].copy()
    return None, trades


def log_new_trades(log: PaperLog, run_key: str, symbol: str, closed_trades: pd.DataFrame) -> int:
    if closed_trades.empty:
        return 0
    logged_at = dt.datetime.now(dt.timezone.utc).isoformat()
    rows = closed_trades.to_dict("records")
    for r in rows:
        r["entry_time"] = str(r["entry_time"])
        r["exit_time"] = str(r["exit_time"])
        r["logged_at"] = logged_at
    return log.add_trades(run_key, symbol, rows)