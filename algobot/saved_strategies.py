"""Saved strategy and backtest-result library."""

from __future__ import annotations
import datetime as dt
import json
import sqlite3
import uuid

SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_strategies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    market TEXT,
    timeframe TEXT,
    config_json TEXT NOT NULL,
    result_json TEXT,
    metrics_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    use_count INTEGER NOT NULL DEFAULT 0
)
"""

class SavedStrategyLibrary:
    def __init__(self, path=":memory:", check_same_thread=True):
        self.db = sqlite3.connect(path, check_same_thread=check_same_thread)
        self.db.execute(SCHEMA)
        self.db.commit()

    def close_db(self):
        self.db.close()

    def count(self):
        return int(self.db.execute("SELECT COUNT(*) FROM saved_strategies").fetchone()[0])

    def save(self, name, cfg, result=None, market="", timeframe=""):
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        sid = uuid.uuid4().hex
        metrics = getattr(result, "metrics", {}) or {}
        payload = None
        if result is not None:
            payload = {
                "trades": result.trades.to_dict("records"),
                "rejections": result.rejections,
            }
        self.db.execute(
            "INSERT INTO saved_strategies "
            "(id,name,market,timeframe,config_json,result_json,metrics_json,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (sid, name.strip(), market, timeframe, json.dumps(cfg, default=str),
             json.dumps(payload, default=str) if payload else None,
             json.dumps(metrics, default=str), now, now),
        )
        self.db.commit()
        return sid

    def list(self):
        rows = self.db.execute(
            "SELECT id,name,market,timeframe,metrics_json,created_at,use_count "
            "FROM saved_strategies ORDER BY updated_at DESC"
        ).fetchall()
        return [
            {"id": r[0], "name": r[1], "market": r[2], "timeframe": r[3],
             "metrics": json.loads(r[4] or "{}"), "created_at": r[5], "use_count": r[6]}
            for r in rows
        ]

    def get(self, sid):
        r = self.db.execute(
            "SELECT id,name,market,timeframe,config_json,result_json,metrics_json,created_at,use_count "
            "FROM saved_strategies WHERE id=?", (sid,)
        ).fetchone()
        if not r:
            return None
        return {
            "id": r[0], "name": r[1], "market": r[2], "timeframe": r[3],
            "config": json.loads(r[4]), "result": json.loads(r[5]) if r[5] else None,
            "metrics": json.loads(r[6] or "{}"), "created_at": r[7], "use_count": r[8],
        }

    def mark_used(self, sid):
        self.db.execute("UPDATE saved_strategies SET use_count=use_count+1, updated_at=? WHERE id=?",
                        (dt.datetime.now(dt.timezone.utc).isoformat(), sid))
        self.db.commit()

    def delete(self, sid):
        self.db.execute("DELETE FROM saved_strategies WHERE id=?", (sid,))
        self.db.commit()
