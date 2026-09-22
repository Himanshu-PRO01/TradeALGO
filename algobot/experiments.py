"""Experiment log.

The most common way to fool yourself: try many variations of a strategy on
the same history, then keep the best-looking one. Even if every variation is
pure noise, the best of many looks good. The more variants tried, the more
impressive the winner looks by luck alone.

This log counts the variants. The audit uses the count to raise the bar for
"statistically significant", so the honest question becomes: "is this result
better than the best I would expect from N random tries?"
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import sqlite3

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    data_fp     TEXT NOT NULL,
    cfg_hash    TEXT NOT NULL,
    name        TEXT NOT NULL,
    trades      INTEGER NOT NULL,
    net_pnl     REAL NOT NULL,
    expectancy  REAL
)
"""


def fingerprint_df(df: pd.DataFrame) -> str:
    """Short identity of a price history: same data gives the same fingerprint."""
    key = f"{len(df)}|{df.index[0]}|{df.index[-1]}|{float(df['close'].sum()):.4f}|{float(df['high'].max()):.4f}"
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def config_hash(cfg: dict) -> str:
    """Identity of a strategy setup: any change to rules, stops, risk or costs is a new variant."""
    relevant = {k: v for k, v in cfg.items() if k not in ("name", "data")}
    return hashlib.sha1(json.dumps(relevant, sort_keys=True, default=str).encode()).hexdigest()[:12]


def required_t_stat(trials: int) -> float:
    """t-statistic needed to beat the best of `trials` random tries.

    The expected maximum of N independent standard normal results is about
    sqrt(2 ln N). With one try the usual bar of 2.0 applies. With about 100
    tries the bar is about 3.0, the level academics ask of new "discoveries".
    """
    if trials <= 1:
        return 2.0
    return max(2.0, math.sqrt(2.0 * math.log(trials)))


class ExperimentLog:
    def __init__(self, path: str = ":memory:", check_same_thread: bool = True):
        self.db = sqlite3.connect(path, check_same_thread=check_same_thread)
        self.db.execute(SCHEMA)
        self.db.commit()

    def record(self, df: pd.DataFrame, cfg: dict, result) -> None:
        m = result.metrics
        self.db.execute(
            "INSERT INTO runs (ts, data_fp, cfg_hash, name, trades, net_pnl, expectancy) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (dt.datetime.now().isoformat(timespec="seconds"), fingerprint_df(df), config_hash(cfg),
             str(cfg.get("name", "")), int(m["trades"]), float(m["net_pnl"]), m["expectancy_per_trade"]),
        )
        self.db.commit()

    def count_trials(self, df: pd.DataFrame) -> int:
        """Distinct strategy variants ever run on this exact data."""
        row = self.db.execute(
            "SELECT COUNT(DISTINCT cfg_hash) FROM runs WHERE data_fp = ?", (fingerprint_df(df),)
        ).fetchone()
        return int(row[0])

    def all_runs(self) -> list:
        return self.db.execute(
            "SELECT ts, name, data_fp, trades, net_pnl FROM runs ORDER BY id"
        ).fetchall()

    def close_db(self) -> None:
        self.db.close()
