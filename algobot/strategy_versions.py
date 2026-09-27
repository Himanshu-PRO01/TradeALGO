"""Strategy version history: an original rule set plus AI-drafted candidates.

The rule this module exists to enforce (see AI_STRATEGY_REWRITE_SWITCH_PROPERTY
below) is the most important thing here, more than any single function:

  * An AI-drafted candidate is ALWAYS a new, separate version. It can never
    overwrite the original, and creating one never changes what is active.
  * A candidate only ever becomes active after a human explicitly approves it
    (`approve`), and only while the "AI Strategy Rewrite" switch is ON.
  * Turning that switch OFF does not mean "AI stops proposing changes" -- it
    means "go back to running the original version", immediately, even if a
    candidate was approved five minutes ago. `get_active()` is the one
    function every caller should use to decide what to actually run; it holds
    this rule regardless of what is stored as "approved".

This module never touches strategy execution, broker credentials, the kill
switch, or the live-trading flag -- it only stores rule sets (plain dicts,
the same shape pages/10_Strategy_Builder.py already uses) and records of
backtest metrics that some OTHER, deterministic part of the app already
computed. It never computes a metric itself.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import dataclass
from typing import Optional

AI_STRATEGY_REWRITE_SWITCH_PROPERTY = (
    "OFF => the active version is always the original, no matter what is approved. "
    "ON => the active version is the most recently approved candidate, or the "
    "original if none has been approved yet."
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS strategy_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id     TEXT NOT NULL,
    version_label   TEXT NOT NULL,
    parent_label    TEXT,
    created_at      TEXT NOT NULL,
    source          TEXT NOT NULL,        -- 'user' or 'ai'
    is_original     INTEGER NOT NULL,     -- 1 for exactly one row per strategy_id
    ai_generated    INTEGER NOT NULL,
    change_summary  TEXT NOT NULL,
    prompt          TEXT,                 -- the user's own words requesting the change, if any
    rules_json      TEXT NOT NULL,
    status          TEXT NOT NULL,        -- 'original' | 'pending' | 'approved' | 'rejected'
    backtest_json   TEXT,                 -- metrics dict some OTHER code already computed
    UNIQUE(strategy_id, version_label)
)
"""

REWRITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS rewrite_switch (
    strategy_id TEXT PRIMARY KEY,
    enabled     INTEGER NOT NULL
)
"""


class VersionError(ValueError):
    """A version-history operation was asked to do something inconsistent."""


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


@dataclass
class VersionRecord:
    id: int
    strategy_id: str
    version_label: str
    parent_label: Optional[str]
    created_at: str
    source: str
    is_original: bool
    ai_generated: bool
    change_summary: str
    prompt: Optional[str]
    rules: dict
    status: str
    backtest: Optional[dict]

    @property
    def is_active_candidate(self) -> bool:
        return self.status == "approved"


def _row_to_record(row: sqlite3.Row) -> VersionRecord:
    return VersionRecord(
        id=row["id"], strategy_id=row["strategy_id"], version_label=row["version_label"],
        parent_label=row["parent_label"], created_at=row["created_at"], source=row["source"],
        is_original=bool(row["is_original"]), ai_generated=bool(row["ai_generated"]),
        change_summary=row["change_summary"], prompt=row["prompt"],
        rules=json.loads(row["rules_json"]), status=row["status"],
        backtest=json.loads(row["backtest_json"]) if row["backtest_json"] else None,
    )


class StrategyVersionStore:
    def __init__(self, path: str = ":memory:", check_same_thread: bool = True):
        self.db = sqlite3.connect(path, check_same_thread=check_same_thread)
        self.db.row_factory = sqlite3.Row
        self.db.execute(SCHEMA)
        self.db.execute(REWRITE_SCHEMA)
        self.db.commit()

    def close_db(self) -> None:
        self.db.close()

    def create_original(self, strategy_id: str, rules: dict, version_label: str = "v1") -> VersionRecord:
        if self.list_versions(strategy_id):
            raise VersionError(f"'{strategy_id}' already has version history; cannot re-create the original.")
        self.db.execute(
            "INSERT INTO strategy_versions (strategy_id, version_label, parent_label, created_at, source, "
            "is_original, ai_generated, change_summary, prompt, rules_json, status) "
            "VALUES (?, ?, NULL, ?, 'user', 1, 0, 'Original strategy', NULL, ?, 'original')",
            (strategy_id, version_label, _now(), json.dumps(rules, sort_keys=True)),
        )
        self.db.commit()
        return self.get(strategy_id, version_label)

    def create_ai_candidate(self, strategy_id: str, parent_label: str, rules: dict,
                             change_summary: str, prompt: Optional[str] = None) -> VersionRecord:
        parent = self.get(strategy_id, parent_label)
        if parent is None:
            raise VersionError(f"Parent version '{parent_label}' not found for '{strategy_id}'.")
        n = 1 + self.db.execute(
            "SELECT COUNT(*) AS n FROM strategy_versions WHERE strategy_id=? AND parent_label=?",
            (strategy_id, parent_label),
        ).fetchone()["n"]
        version_label = f"{parent_label}-AI-{n:03d}"
        self.db.execute(
            "INSERT INTO strategy_versions (strategy_id, version_label, parent_label, created_at, source, "
            "is_original, ai_generated, change_summary, prompt, rules_json, status) "
            "VALUES (?, ?, ?, ?, 'ai', 0, 1, ?, ?, ?, 'pending')",
            (strategy_id, version_label, parent_label, _now(), change_summary, prompt,
             json.dumps(rules, sort_keys=True)),
        )
        self.db.commit()
        return self.get(strategy_id, version_label)

    def get(self, strategy_id: str, version_label: str) -> Optional[VersionRecord]:
        row = self.db.execute(
            "SELECT * FROM strategy_versions WHERE strategy_id=? AND version_label=?",
            (strategy_id, version_label),
        ).fetchone()
        return _row_to_record(row) if row else None

    def list_versions(self, strategy_id: str) -> list[VersionRecord]:
        rows = self.db.execute(
            "SELECT * FROM strategy_versions WHERE strategy_id=? ORDER BY id", (strategy_id,)
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def _original_label(self, strategy_id: str) -> Optional[str]:
        row = self.db.execute(
            "SELECT version_label FROM strategy_versions WHERE strategy_id=? AND is_original=1", (strategy_id,)
        ).fetchone()
        return row["version_label"] if row else None

    def record_backtest(self, strategy_id: str, version_label: str, metrics: dict) -> None:
        if self.get(strategy_id, version_label) is None:
            raise VersionError(f"Version '{version_label}' not found for '{strategy_id}'.")
        self.db.execute(
            "UPDATE strategy_versions SET backtest_json=? WHERE strategy_id=? AND version_label=?",
            (json.dumps(metrics, sort_keys=True, default=str), strategy_id, version_label),
        )
        self.db.commit()

    def approve(self, strategy_id: str, version_label: str) -> VersionRecord:
        record = self.get(strategy_id, version_label)
        if record is None:
            raise VersionError(f"Version '{version_label}' not found for '{strategy_id}'.")
        if record.is_original:
            raise VersionError("The original version does not need approval; it is always available.")
        if record.status == "rejected":
            raise VersionError(f"'{version_label}' was rejected; create a new candidate instead of re-approving it.")
        self.db.execute(
            "UPDATE strategy_versions SET status='pending' WHERE strategy_id=? AND status='approved'",
            (strategy_id,),
        )
        self.db.execute(
            "UPDATE strategy_versions SET status='approved' WHERE strategy_id=? AND version_label=?",
            (strategy_id, version_label),
        )
        self.db.commit()
        return self.get(strategy_id, version_label)

    def reject(self, strategy_id: str, version_label: str) -> VersionRecord:
        record = self.get(strategy_id, version_label)
        if record is None:
            raise VersionError(f"Version '{version_label}' not found for '{strategy_id}'.")
        if record.is_original:
            raise VersionError("The original version cannot be rejected.")
        self.db.execute(
            "UPDATE strategy_versions SET status='rejected' WHERE strategy_id=? AND version_label=?",
            (strategy_id, version_label),
        )
        self.db.commit()
        return self.get(strategy_id, version_label)

    def get_rewrite_enabled(self, strategy_id: str) -> bool:
        row = self.db.execute(
            "SELECT enabled FROM rewrite_switch WHERE strategy_id=?", (strategy_id,)
        ).fetchone()
        return bool(row["enabled"]) if row else False

    def set_rewrite_enabled(self, strategy_id: str, enabled: bool) -> None:
        self.db.execute(
            "INSERT INTO rewrite_switch (strategy_id, enabled) VALUES (?, ?) "
            "ON CONFLICT(strategy_id) DO UPDATE SET enabled=excluded.enabled",
            (strategy_id, int(enabled)),
        )
        self.db.commit()

    def get_active(self, strategy_id: str) -> Optional[str]:
        original = self._original_label(strategy_id)
        if not self.get_rewrite_enabled(strategy_id):
            return original
        row = self.db.execute(
            "SELECT version_label FROM strategy_versions WHERE strategy_id=? AND status='approved' "
            "ORDER BY id DESC LIMIT 1",
            (strategy_id,),
        ).fetchone()
        return row["version_label"] if row else original

    def diff(self, strategy_id: str, label_a: str, label_b: str) -> dict:
        a, b = self.get(strategy_id, label_a), self.get(strategy_id, label_b)
        if a is None or b is None:
            raise VersionError("Both versions must exist to compare them.")
        rule_keys = sorted(set(a.rules) | set(b.rules))
        rule_diff = {
            k: {"a": a.rules.get(k), "b": b.rules.get(k)}
            for k in rule_keys if a.rules.get(k) != b.rules.get(k)
        }
        metric_diff = {}
        if a.backtest and b.backtest:
            for k in sorted(set(a.backtest) & set(b.backtest)):
                va, vb = a.backtest.get(k), b.backtest.get(k)
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                    metric_diff[k] = {"a": va, "b": vb, "delta": vb - va}
                elif va != vb:
                    metric_diff[k] = {"a": va, "b": vb}
        return {
            "a_label": label_a, "b_label": label_b,
            "rule_changes": rule_diff,
            "metric_changes": metric_diff,
            "a_has_backtest": bool(a.backtest), "b_has_backtest": bool(b.backtest),
        }
