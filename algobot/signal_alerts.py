"""Sends a WhatsApp alert on the same strategy signal Paper Trading and Sandbox
Rehearsal evaluate. No order of any kind is placed from this module -- this is
the alerts-not-automation path the brother actually asked for: he wants to
know when a signal fires and decide for himself, not have the system trade
for him.

Uses the same "have we already acted on this position" state machine as
sandbox_rehearsal.py (see that module's docstring for why this matters): a
position that stays open across reruns sends exactly one entry alert and
exactly one exit alert, not one per refresh.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Optional

import pandas as pd

from .whatsapp_alerts import WhatsAppError, send_whatsapp

SCHEMA = """
CREATE TABLE IF NOT EXISTS alert_state (
    run_key    TEXT PRIMARY KEY,
    status     TEXT NOT NULL CHECK (status IN ('flat', 'open')),
    side       TEXT,
    entry_time TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alert_events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_key TEXT NOT NULL,
    ts      TEXT NOT NULL,
    action  TEXT NOT NULL CHECK (action IN ('entry', 'exit')),
    side    TEXT NOT NULL,
    message TEXT NOT NULL,
    ok      INTEGER NOT NULL,
    detail  TEXT NOT NULL DEFAULT ''
)
"""


class AlertLog:
    def __init__(self, path: str = ":memory:", check_same_thread: bool = True):
        self.db = sqlite3.connect(path, check_same_thread=check_same_thread)
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close_db(self) -> None:
        self.db.close()

    def get_state(self, run_key: str) -> dict:
        row = self.db.execute(
            "SELECT status, side, entry_time FROM alert_state WHERE run_key = ?", (run_key,)
        ).fetchone()
        if row is None:
            return {"status": "flat", "side": None, "entry_time": None}
        status, side, entry_time = row
        return {"status": status, "side": side, "entry_time": entry_time}

    def set_state(self, run_key: str, status: str, side: Optional[str] = None,
                  entry_time: Optional[str] = None) -> None:
        self.db.execute(
            "INSERT INTO alert_state (run_key, status, side, entry_time, updated_at) "
            "VALUES (?,?,?,?,?) "
            "ON CONFLICT(run_key) DO UPDATE SET status=excluded.status, side=excluded.side, "
            "entry_time=excluded.entry_time, updated_at=excluded.updated_at",
            (run_key, status, side, entry_time,
             dt.datetime.now().isoformat(sep=" ", timespec="seconds")),
        )
        self.db.commit()

    def record_event(self, run_key: str, action: str, side: str, message: str,
                      ok: bool, detail: str = "") -> None:
        self.db.execute(
            "INSERT INTO alert_events (run_key, ts, action, side, message, ok, detail) "
            "VALUES (?,?,?,?,?,?,?)",
            (run_key, dt.datetime.now().isoformat(sep=" ", timespec="seconds"),
             action, side, message, 1 if ok else 0, detail),
        )
        self.db.commit()

    def history(self, run_key: str) -> pd.DataFrame:
        cols = ["ts", "action", "side", "message", "ok", "detail"]
        cur = self.db.execute(
            f"SELECT {', '.join(cols)} FROM alert_events WHERE run_key = ? ORDER BY id DESC", (run_key,)
        )
        return pd.DataFrame(cur.fetchall(), columns=cols)

    def reset(self, run_key: str) -> None:
        """Forgets local tracking only -- does not un-send any alert already delivered."""
        self.db.execute("DELETE FROM alert_state WHERE run_key = ?", (run_key,))
        self.db.execute("DELETE FROM alert_events WHERE run_key = ?", (run_key,))
        self.db.commit()


def step(open_snapshot: Optional[dict], run_key: str, instrument_label: str,
         quantity: int, log: AlertLog) -> list:
    """Compare the strategy's current open/flat status against what we last
    alerted on, and send exactly the one WhatsApp alert needed (an entry, an
    exit, or nothing) to catch up."""
    state = log.get_state(run_key)
    messages: list = []

    if state["status"] == "flat":
        if open_snapshot is None:
            return messages  # still flat, nothing to do
        side = open_snapshot["side"]
        entry_time = str(open_snapshot["entry_time"])
        text = (f"\U0001F7E2 {instrument_label}: {side} signal fired at {entry_time}. "
                f"Suggested size: {quantity} unit(s). Not an order -- you place it "
                f"yourself if you want it.")
        try:
            results = send_whatsapp(text)
            log.set_state(run_key, "open", side=side, entry_time=entry_time)
            log.record_event(run_key, "entry", side, text, True, "; ".join(results))
            messages.append(f"Entry alert sent ({side}): " + "; ".join(results))
        except WhatsAppError as exc:
            log.record_event(run_key, "entry", side, text, False, str(exc))
            messages.append(f"Entry alert FAILED: {exc}")
        return messages

    # state["status"] == "open"
    still_same_position = open_snapshot is not None and str(open_snapshot["entry_time"]) == state["entry_time"]
    if still_same_position:
        return messages  # nothing changed, no duplicate alert
    text = f"\u26AA {instrument_label}: {state['side']} position closed. Flat now."
    try:
        results = send_whatsapp(text)
        log.record_event(run_key, "exit", state["side"], text, True, "; ".join(results))
        log.set_state(run_key, "flat")
        messages.append("Exit alert sent: " + "; ".join(results))
    except WhatsAppError as exc:
        log.record_event(run_key, "exit", state["side"], text, False, str(exc))
        messages.append(f"Exit alert FAILED: {exc}")
    return messages
