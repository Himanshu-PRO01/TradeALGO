"""Connects a strategy's own signal (the same one Paper Trading evaluates) to real
Upstox Sandbox orders -- still sandbox only, still no real money, but now rehearsing
the actual order lifecycle instead of just logging what would have happened.

The hard part is not placing an order; it is placing it EXACTLY ONCE per position.
Every refresh re-evaluates the whole strategy from scratch (see paper_trading.py),
so without remembering "did we already act on this position", a signal that stays
open across several refreshes would fire a new entry order every single time. The
state tracked here is what prevents that: one row per run_key recording whether we
are currently flat or already hold a sandbox position, updated only when that
actually changes.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Optional

import pandas as pd

from .upstox_sandbox import UpstoxSandboxClient, UpstoxSandboxError, extract_order_id

SCHEMA = """
CREATE TABLE IF NOT EXISTS rehearsal_state (
    run_key    TEXT PRIMARY KEY,
    status     TEXT NOT NULL CHECK (status IN ('flat', 'open')),
    side       TEXT,
    entry_time TEXT,
    order_id   TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rehearsal_events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    run_key           TEXT NOT NULL,
    ts                TEXT NOT NULL,
    action            TEXT NOT NULL CHECK (action IN ('entry', 'exit')),
    side              TEXT NOT NULL,
    transaction_type  TEXT NOT NULL,
    instrument_token  TEXT NOT NULL,
    quantity          INTEGER NOT NULL,
    ok                INTEGER NOT NULL,
    detail            TEXT NOT NULL DEFAULT ''
)
"""


class RehearsalLog:
    def __init__(self, path: str = ":memory:", check_same_thread: bool = True):
        self.db = sqlite3.connect(path, check_same_thread=check_same_thread)
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close_db(self) -> None:
        self.db.close()

    def get_state(self, run_key: str) -> dict:
        row = self.db.execute(
            "SELECT status, side, entry_time, order_id FROM rehearsal_state WHERE run_key = ?", (run_key,)
        ).fetchone()
        if row is None:
            return {"status": "flat", "side": None, "entry_time": None, "order_id": None}
        status, side, entry_time, order_id = row
        return {"status": status, "side": side, "entry_time": entry_time, "order_id": order_id}

    def set_state(self, run_key: str, status: str, side: Optional[str] = None,
                  entry_time: Optional[str] = None, order_id: Optional[str] = None) -> None:
        self.db.execute(
            "INSERT INTO rehearsal_state (run_key, status, side, entry_time, order_id, updated_at) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(run_key) DO UPDATE SET status=excluded.status, side=excluded.side, "
            "entry_time=excluded.entry_time, order_id=excluded.order_id, updated_at=excluded.updated_at",
            (run_key, status, side, entry_time, order_id, dt.datetime.now().isoformat(sep=" ", timespec="seconds")),
        )
        self.db.commit()

    def record_event(self, run_key: str, action: str, side: str, transaction_type: str,
                      instrument_token: str, quantity: int, ok: bool, detail: str = "") -> None:
        self.db.execute(
            "INSERT INTO rehearsal_events (run_key, ts, action, side, transaction_type, instrument_token, "
            "quantity, ok, detail) VALUES (?,?,?,?,?,?,?,?,?)",
            (run_key, dt.datetime.now().isoformat(sep=" ", timespec="seconds"), action, side, transaction_type,
             instrument_token, int(quantity), 1 if ok else 0, detail),
        )
        self.db.commit()

    def history(self, run_key: str) -> pd.DataFrame:
        cols = ["ts", "action", "side", "transaction_type", "instrument_token", "quantity", "ok", "detail"]
        cur = self.db.execute(
            f"SELECT {', '.join(cols)} FROM rehearsal_events WHERE run_key = ? ORDER BY id DESC", (run_key,)
        )
        return pd.DataFrame(cur.fetchall(), columns=cols)

    def reset(self, run_key: str) -> None:
        """Forgets local tracking only. It does NOT cancel any order already sent to Upstox Sandbox --
        do that from the Upstox Sandbox page (or the Upstox app) if one is still open there."""
        self.db.execute("DELETE FROM rehearsal_state WHERE run_key = ?", (run_key,))
        self.db.execute("DELETE FROM rehearsal_events WHERE run_key = ?", (run_key,))
        self.db.commit()


def step(open_snapshot: Optional[dict], run_key: str, client: UpstoxSandboxClient,
         instrument_token: str, quantity: int, log: RehearsalLog) -> list[str]:
    """Compare the strategy's current open/flat status against what we last acted on, and place
    exactly the one sandbox order needed (an entry, an exit, or nothing) to catch up."""
    state = log.get_state(run_key)
    messages: list[str] = []

    if state["status"] == "flat":
        if open_snapshot is None:
            return messages  # still flat, nothing to do
        side = open_snapshot["side"]
        transaction_type = "BUY" if side == "LONG" else "SELL"
        entry_time = str(open_snapshot["entry_time"])
        try:
            response = client.place_order(instrument_token, int(quantity), transaction_type, order_type="MARKET")
            order_id = extract_order_id(response)
            log.set_state(run_key, "open", side=side, entry_time=entry_time, order_id=order_id)
            log.record_event(run_key, "entry", side, transaction_type, instrument_token, quantity, True, str(order_id or ""))
            messages.append(f"Entered {side}: sandbox order {order_id}")
        except UpstoxSandboxError as exc:
            log.record_event(run_key, "entry", side, transaction_type, instrument_token, quantity, False, str(exc))
            messages.append(f"Entry FAILED: {exc}")
        return messages

    # state["status"] == "open"
    still_same_position = open_snapshot is not None and str(open_snapshot["entry_time"]) == state["entry_time"]
    if still_same_position:
        return messages  # nothing changed, no duplicate order
    transaction_type = "SELL" if state["side"] == "LONG" else "BUY"
    try:
        response = client.place_order(instrument_token, int(quantity), transaction_type, order_type="MARKET")
        order_id = extract_order_id(response)
        log.record_event(run_key, "exit", state["side"], transaction_type, instrument_token, quantity, True, str(order_id or ""))
        log.set_state(run_key, "flat")
        messages.append(f"Exited {state['side']}: sandbox order {order_id}")
    except UpstoxSandboxError as exc:
        log.record_event(run_key, "exit", state["side"], transaction_type, instrument_token, quantity, False, str(exc))
        messages.append(f"Exit FAILED: {exc}")
    return messages
