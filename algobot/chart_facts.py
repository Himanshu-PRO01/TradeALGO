"""Plain facts about the most recent candles on a real chart.

None of this needs an AI call -- it's exact arithmetic on real OHLCV data, the
same kind of thing a trader would otherwise have to read off the chart by eye
(which candle was up or down, how many of the last few were green, where RSI
sits). Strategy Builder shows these directly; algobot.ai_strategy_agent's
suggest_from_chart() can also turn them into a suggested rule, citation-checked
against this same dict so it cannot invent a number that isn't here.

Dotted keys match the convention in research_context.py's clean_metrics() /
backtest_facts(), so these can be displayed or logged the same way.
"""
from __future__ import annotations

import math

import pandas as pd

from .indicators import rsi as _rsi
from .indicators import sma as _sma


def _round(v, places=2):
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return v
    return None if not math.isfinite(v) else round(v, places)


def _direction(row) -> str:
    if row["close"] > row["open"]:
        return "bullish"
    if row["close"] < row["open"]:
        return "bearish"
    return "flat"


def _change_pct(row) -> float:
    return (row["close"] - row["open"]) / row["open"] * 100.0 if row["open"] else 0.0


def chart_facts(df: pd.DataFrame, lookback: int = 5) -> dict:
    """Facts about the most recent `lookback` candles of `df` (needs open, high,
    low, close; at least 2 rows). Returns {} if there isn't enough data yet.
    """
    if df is None or len(df) < 2:
        return {}

    lookback = max(2, int(lookback))
    recent = df.tail(lookback)
    last, prev = df.iloc[-1], df.iloc[-2]

    facts = {
        "chart.bars_available": int(len(df)),
        "chart.last_close": _round(last["close"]),
        "chart.last_open": _round(last["open"]),
        "chart.last_high": _round(last["high"]),
        "chart.last_low": _round(last["low"]),
        "candle.last.direction": _direction(last),
        "candle.last.change_pct": _round(_change_pct(last)),
        "candle.prev.direction": _direction(prev),
        "candle.prev.change_pct": _round(_change_pct(prev)),
        f"candle.last{lookback}.bullish_count": int((recent["close"] > recent["open"]).sum()),
        f"candle.last{lookback}.bearish_count": int((recent["close"] < recent["open"]).sum()),
        f"candle.last{lookback}.flat_count": int((recent["close"] == recent["open"]).sum()),
    }

    if len(df) >= 14:
        r = _rsi(df["close"], 14).iloc[-1]
        if pd.notna(r):
            facts["trend.rsi14"] = _round(float(r))
    sma_period = min(20, len(df))
    if sma_period >= 2:
        s = _sma(df["close"], sma_period).iloc[-1]
        if pd.notna(s):
            facts["trend.sma20"] = _round(float(s))
            facts["trend.price_vs_sma20"] = "above" if last["close"] > s else "below"

    window = df.tail(max(lookback * 4, 20))
    facts["levels.recent_swing_high"] = _round(float(window["high"].max()))
    facts["levels.recent_swing_low"] = _round(float(window["low"].min()))

    return facts


def describe_chart_facts(facts: dict) -> list[str]:
    """Plain-English lines for `facts`, in the order a trader would want to read
    them. Skips anything not present rather than guessing a value."""
    if not facts:
        return []
    lines = []
    arrow = {"bullish": "🟢", "bearish": "🔴", "flat": "⚪"}
    if "candle.prev.direction" in facts:
        d = facts["candle.prev.direction"]
        pct = facts.get("candle.prev.change_pct")
        pct_txt = f", {pct:+.2f}% open-to-close" if pct is not None else ""
        lines.append(f"{arrow.get(d, '')} Previous candle: **{d}**{pct_txt}")
    if "candle.last.direction" in facts:
        d = facts["candle.last.direction"]
        pct = facts.get("candle.last.change_pct")
        pct_txt = f", {pct:+.2f}% open-to-close" if pct is not None else ""
        lines.append(f"{arrow.get(d, '')} Most recent candle: **{d}**{pct_txt}")
    bull_keys = [k for k in facts if k.startswith("candle.last") and k.endswith(".bullish_count")]
    if bull_keys:
        k = bull_keys[0]
        n = k[len("candle.last"):-len(".bullish_count")]
        lines.append(f"Last {n} candles: **{facts[k]} up**, **{facts.get(f'candle.last{n}.bearish_count', 0)} down**")
    if "trend.rsi14" in facts:
        lines.append(f"RSI(14): **{facts['trend.rsi14']}**")
    if "trend.price_vs_sma20" in facts:
        lines.append(f"Price is **{facts['trend.price_vs_sma20']}** its 20-bar average "
                      f"({facts.get('trend.sma20')})")
    if "levels.recent_swing_high" in facts and "levels.recent_swing_low" in facts:
        lines.append(f"Recent range: **{facts['levels.recent_swing_low']}** to "
                      f"**{facts['levels.recent_swing_high']}**")
    return lines
