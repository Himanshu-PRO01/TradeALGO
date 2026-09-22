"""Data quality checks.

Bad data quietly produces beautiful backtests: a missing bar, a price spike
from a bad tick, or a stale feed can create "profits" that never existed.
These checks look for the usual problems and say where they are.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Issue:
    severity: str          # "WARN" or "INFO"
    message: str


def _bar_minutes(df: pd.DataFrame) -> float:
    days = df.index.normalize()
    within = pd.Series(df.index, index=df.index).groupby(days).diff().dropna()
    if within.empty:
        return 24 * 60.0
    return float(within.dt.total_seconds().median() / 60.0)


def data_quality_report(
    df: pd.DataFrame, session_start: dt.time = dt.time(9, 15), session_end: dt.time = dt.time(15, 30),
    max_jump_pct: float = 5.0,
) -> list:
    issues: list[Issue] = []
    minutes = _bar_minutes(df)
    weekend = df.index.dayofweek >= 5
    if weekend.any():
        issues.append(Issue("WARN", f"{int(weekend.sum())} bar(s) fall on a Saturday or Sunday "
                                    f"(first on {df.index[weekend][0]:%Y-%m-%d}). Check the time zone and the source."))

    intraday = minutes < 24 * 60 * 0.9
    if intraday:
        t = df.index.time
        outside = np.array([(x < session_start) or (x >= session_end) for x in t])
        if outside.any():
            issues.append(Issue("WARN", f"{int(outside.sum())} bar(s) are outside {session_start:%H:%M} to "
                                        f"{session_end:%H:%M} (first at {df.index[outside][0]}). "
                                        "Wrong time zone, pre-market ticks, or a bad export."))
        per_day = df.groupby(df.index.normalize()).size()
        typical = float(per_day.median())
        thin = per_day[per_day < 0.8 * typical]
        if len(thin):
            worst = thin.idxmin()
            issues.append(Issue("WARN", f"{len(thin)} day(s) have far fewer bars than the typical {typical:.0f} "
                                        f"(worst: {worst:%Y-%m-%d} with {int(thin.min())}). Missing data or a half day."))
        step = pd.Timedelta(minutes=minutes)
        missing_total, worst_day, worst_missing = 0, None, 0
        for day, rows in df.groupby(df.index.normalize()):
            span = rows.index[-1] - rows.index[0]
            expected = int(round(span / step)) + 1
            gap = expected - len(rows)
            if gap > 0:
                missing_total += gap
                if gap > worst_missing:
                    worst_day, worst_missing = day, gap
        if missing_total:
            issues.append(Issue("WARN", f"{missing_total} bar(s) are missing inside trading days "
                                        f"(worst: {worst_day:%Y-%m-%d}, {worst_missing} missing). A strategy that "
                                        "trades through a gap sees prices that never existed."))
        day_key = df.index.normalize()
        moves = df["close"].groupby(day_key).pct_change().abs() * 100.0
    else:
        moves = df["close"].pct_change().abs() * 100.0
        max_jump_pct = max(max_jump_pct, 12.0)

    spikes = moves[moves > max_jump_pct]
    if len(spikes):
        issues.append(Issue("WARN", f"{len(spikes)} bar-to-bar move(s) above {max_jump_pct:g}% "
                                    f"(largest {spikes.max():.1f}% at {spikes.idxmax()}). Real, or a bad tick?"))

    flat = (df["open"] == df["high"]) & (df["high"] == df["low"]) & (df["low"] == df["close"])
    run, longest = 0, 0
    for value in flat.to_numpy():
        run = run + 1 if value else 0
        longest = max(longest, run)
    if longest >= 6:
        issues.append(Issue("WARN", f"A run of {longest} identical flat bars in a row: a stale or frozen feed."))

    if (df["volume"] > 0).any():
        zero_share = float((df["volume"] == 0).mean() * 100.0)
        if zero_share > 5:
            issues.append(Issue("WARN", f"{zero_share:.0f}% of bars have zero volume."))
    else:
        issues.append(Issue("INFO", "There is no volume data, so volume-based rules and VWAP will not work."))
    return issues


def format_data_quality(issues: list, df: pd.DataFrame) -> str:
    head = (f"Data check: {len(df):,} bars from {df.index[0]:%Y-%m-%d %H:%M} to {df.index[-1]:%Y-%m-%d %H:%M} "
            f"({_bar_minutes(df):g}-minute bars)")
    warns = [i for i in issues if i.severity == "WARN"]
    if not issues:
        return head + "\nNo problems found."
    lines = [head]
    lines += [f"[{i.severity}] {i.message}" for i in issues]
    lines.append("Fix the warnings before trusting any result." if warns else "Nothing serious found.")
    return "\n".join(lines)
