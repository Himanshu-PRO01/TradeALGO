"""A persistent, human-operable kill switch.

This is independent of the per-run daily-loss halt already inside RiskManager
(which only lives for the length of one backtest/paper-trading run). This one
survives app restarts and is meant to be the single global "stop everything"
control -- checked by execution_policy.live_trading_allowed() so that even
once LIVE_TRADING_ENABLED is eventually turned on, a tripped kill switch still
blocks real orders. Every halt and resume is kept forever, never overwritten,
so there is always a record of who stopped trading, when, and why.
"""
from __future__ import annotations

import datetime as dt
import sqlite3

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS kill_switch_events (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('halt', 'resume')),
    reason TEXT NOT NULL DEFAULT '',
    by     TEXT NOT NULL DEFAULT ''
)
"""


class KillSwitch:
    def __init__(self, path: str = ":memory:", check_same_thread: bool = True):
        self.db = sqlite3.connect(path, check_same_thread=check_same_thread)
        self.db.execute(SCHEMA)
        self.db.commit()

    def close_db(self) -> None:
        self.db.close()

    def halt(self, reason: str, by: str = "manual") -> None:
        self.db.execute(
            "INSERT INTO kill_switch_events (ts, action, reason, by) VALUES (?, 'halt', ?, ?)",
            (dt.datetime.now().isoformat(sep=" ", timespec="seconds"), reason.strip(), by.strip() or "manual"),
        )
        self.db.commit()

    def resume(self, by: str = "manual") -> None:
        self.db.execute(
            "INSERT INTO kill_switch_events (ts, action, reason, by) VALUES (?, 'resume', '', ?)",
            (dt.datetime.now().isoformat(sep=" ", timespec="seconds"), by.strip() or "manual"),
        )
        self.db.commit()

    def status(self) -> dict:
        """Current state, decided purely by whichever event happened last."""
        row = self.db.execute(
            "SELECT ts, action, reason, by FROM kill_switch_events ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return {"halted": False, "reason": "", "since": None, "by": None}
        ts, action, reason, by = row
        return {"halted": action == "halt", "reason": reason, "since": ts, "by": by}

    def history(self) -> pd.DataFrame:
        cur = self.db.execute("SELECT ts, action, reason, by FROM kill_switch_events ORDER BY id DESC")
        return pd.DataFrame(cur.fetchall(), columns=["ts", "action", "reason", "by"])
