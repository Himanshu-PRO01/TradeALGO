"""Market research agent for TradeALGO.

The agent is deliberately a research system, not an auto-trader. It combines
price history from supported providers, headline metadata from permitted RSS
feeds, generates a small set of transparent rule strategies, runs them through
TradeALGO's existing backtester and reality checks, and ranks the evidence.

"Learning" here means parameter variation and robustness testing; it does not
silently train a model on future prices.
"""
from __future__ import annotations
import datetime as dt
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd
import requests
try:
    import yfinance as yf
except ImportError:
    yf = None
from .audit import run_audit
from .config import validate_config
from .engine import run_backtest
from .strategy import build_strategy

@dataclass
class SourceResult:
    name: str
    kind: str
    ok: bool
    rows: int = 0
    detail: str = ""
    data: Optional[pd.DataFrame] = None

@dataclass
class NewsItem:
    source: str
    title: str
    url: str
    published: str = ""

@dataclass
class CandidateResult:
    name: str
    config: dict
    metrics: dict
    audit: object | None = None
    score: float = 0.0
    notes: list[str] = field(default_factory=list)

@dataclass
class AgentReport:
    symbol: str
    period: str
    sources: list[SourceResult]
    news: list[NewsItem]
    candidates: list[CandidateResult]
    selected: Optional[CandidateResult]
    created_at: str

NEWS_FEEDS = {
    "Economic Times Markets": "https://economictimes.indiatimes.com/markets/stocks/rss.cms",
    "Moneycontrol India": "https://www.moneycontrol.com/news/india/rss-/amp",
}

def _yf_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if s in {"NIFTY", "NIFTY50", "^NSEI"}:
        return "^NSEI"
    if s in {"SENSEX", "^BSESN"}:
        return "^BSESN"
    if "." in s or s.startswith("^"):
        return s
    return f"{s}.NS"

def fetch_yfinance(symbol: str, period: str = "2y", interval: str = "1d") -> SourceResult:
    if yf is None:
        return SourceResult("Yahoo Finance", "price", False, detail="yfinance is not installed.")
    ticker = _yf_symbol(symbol)
    try:
        raw = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
        if raw.empty:
            return SourceResult("Yahoo Finance", "price", False, detail=f"No data for {ticker}.")
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw = raw.rename(columns=str.lower)
        needed = ["open", "high", "low", "close"]
        if not all(c in raw.columns for c in needed):
            return SourceResult("Yahoo Finance", "price", False, detail="Missing OHLC columns.")
        out = raw[needed + (["volume"] if "volume" in raw.columns else [])].copy()
        out["volume"] = out["volume"].fillna(0) if "volume" in out else 0
        out.index = pd.to_datetime(out.index)
        out = out.dropna(subset=needed)
        return SourceResult("Yahoo Finance", "price", True, len(out), f"{ticker}, {interval}", out)
    except Exception as exc:
        return SourceResult("Yahoo Finance", "price", False, detail=str(exc))

def fetch_openalgo(symbol: str, start: str, end: str, interval: str = "D") -> SourceResult:
    try:
        from .openalgo_bridge import OpenAlgoClient
        client = OpenAlgoClient()
        raw = client.history(symbol, "NSE_EQ", interval, start, end)
        if raw is None or len(raw) == 0:
            return SourceResult("OpenAlgo/Upstox", "price", False, detail="No rows returned.")
        df = pd.DataFrame(raw)
        df = df.rename(columns={c: c.lower() for c in df.columns})
        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.set_index("datetime")
        for c in ["open", "high", "low", "close", "volume"]:
            if c not in df.columns:
                if c == "volume":
                    df[c] = 0
                else:
                    return SourceResult("OpenAlgo/Upstox", "price", False, detail=f"Missing {c}.")
        return SourceResult("OpenAlgo/Upstox", "price", True, len(df), "Broker history adapter",
                            df[["open","high","low","close","volume"]])
    except Exception as exc:
        return SourceResult("OpenAlgo/Upstox", "price", False, detail=f"Optional source unavailable: {exc}")

def fetch_news(feeds: Optional[dict[str, str]] = None, limit: int = 8) -> list[NewsItem]:
    items: list[NewsItem] = []
    for source, url in (feeds or NEWS_FEEDS).items():
        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": "TradeALGO-Research/1.0"})
            response.raise_for_status()
            root = ET.fromstring(response.content)
            for node in root.findall(".//item")[:limit]:
                title = (node.findtext("title") or "").strip()
                link = (node.findtext("link") or "").strip()
                pub = (node.findtext("pubDate") or "").strip()
                if title and link:
                    items.append(NewsItem(source, title, link, pub))
        except Exception:
            continue
    return items[:limit * max(1, len(feeds or NEWS_FEEDS))]

def _base_config(name: str, indicators: list[dict], entry_long: str, exit_long: str,
                 entry_short: str, exit_short: str, capital: float = 100000) -> dict:
    return validate_config({
        "name": name, "capital": capital, "data": {"path": ""},
        "strategy": {"name": "rules", "params": {
            "indicators": indicators, "entry_long": entry_long, "exit_long": exit_long,
            "entry_short": entry_short, "exit_short": exit_short},
            "quantity": 1, "allow_short": True, "stop_loss_pct": 1.0, "target_pct": 2.0},
        "risk": {"max_daily_loss": 3000, "max_trades_per_day": 4, "max_position_value": 100000,
                 "trading_start": "09:20", "no_new_entries_after": "14:45", "square_off_time": "15:15"},
        "costs": {"brokerage_pct": 0.03, "brokerage_cap": 20, "stt_sell_pct": 0.025,
                  "exchange_txn_pct": 0.003, "sebi_fee_pct": 0.0001, "stamp_buy_pct": 0.003,
                  "gst_pct": 18, "slippage_bps": 2},
    })

def candidate_strategies() -> list[dict]:
    return [
        _base_config("Agent EMA trend",
            [{"name":"ema_fast","type":"ema","period":9},{"name":"ema_slow","type":"ema","period":21},{"name":"rsi_14","type":"rsi","period":14}],
            "ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev and rsi_14 > 50","ema_fast < ema_slow",
            "ema_fast < ema_slow and ema_fast_prev >= ema_slow_prev and rsi_14 < 50","ema_fast > ema_slow"),
        _base_config("Agent breakout",
            [{"name":"high_20","type":"highest","period":20},{"name":"low_20","type":"lowest","period":20}],
            "close > high_20 and close_prev <= high_20_prev","close < low_20",
            "close < low_20 and close_prev >= low_20_prev","close > high_20"),
        _base_config("Agent RSI mean reversion",
            [{"name":"rsi_14","type":"rsi","period":14},{"name":"ema_50","type":"ema","period":50}],
            "rsi_14 < 30 and close > ema_50","rsi_14 > 55",
            "rsi_14 > 70 and close < ema_50","rsi_14 < 45"),
    ]

def _rank(metrics: dict, audit) -> float:
    trades = metrics.get("trades") or 0
    pf = metrics.get("profit_factor")
    pf = 0 if pf is None or not np.isfinite(pf) else float(pf)
    ret = float(metrics.get("return_pct") or 0)
    dd = abs(float(metrics.get("max_drawdown_pct") or 0))
    wr = float(metrics.get("win_rate_pct") or 0)
    penalty = 20 if trades < 30 else (8 if trades < 100 else 0)
    audit_penalty = 0 if audit is None else 25 * sum(c.status == "FAIL" for c in audit.checks) + 6 * sum(c.status == "WARN" for c in audit.checks)
    return ret + min(pf, 4) * 4 + wr * 0.04 - dd * 0.5 - penalty - audit_penalty

def run_agent(df: pd.DataFrame, symbol: str, period_label: str = "custom",
              audit_candidates: bool = True, n_random: int = 30, n_mc: int = 300) -> AgentReport:
    df = df.copy().sort_index()
    df.index = pd.to_datetime(df.index)
    results: list[CandidateResult] = []
    for cfg in candidate_strategies():
        try:
            result = run_backtest(df, cfg, build_strategy(cfg))
            audit = run_audit(df, cfg, trials=1, n_random=n_random, n_mc=n_mc) if audit_candidates else None
            metrics = result.metrics
            notes = []
            if metrics.get("trades", 0) < 30:
                notes.append("Too few trades for a strong conclusion.")
            if audit and audit.verdict.startswith("NOT READY"):
                notes.append("Reality check found material weaknesses.")
            results.append(CandidateResult(cfg["name"], cfg, metrics, audit, _rank(metrics, audit), notes))
        except Exception as exc:
            results.append(CandidateResult(cfg["name"], cfg, {"trades":0,"net_pnl":0,"return_pct":0},
                                           None, -9999, [str(exc)]))
    results.sort(key=lambda x: x.score, reverse=True)
    return AgentReport(symbol, period_label, [], [], results, results[0] if results else None,
                       dt.datetime.now(dt.timezone.utc).isoformat())

def merge_sources(sources: list[SourceResult]) -> Optional[pd.DataFrame]:
    valid = [s.data for s in sources if s.ok and s.data is not None and len(s.data)]
    if not valid:
        return None
    base = valid[0].copy()
    base.index = pd.to_datetime(base.index)
    return base[~base.index.duplicated(keep="last")].sort_index()

def consensus_label(results: list[CandidateResult]) -> str:
    if not results: return "NO RESULT"
    top = results[0]
    if top.audit and top.audit.verdict.startswith("PASSED"): return "RESEARCH-PASS / PAPER TEST ONLY"
    if top.audit and top.audit.verdict.startswith("PROMISING"): return "PROMISING / NEEDS MORE TESTING"
    return "NOT READY"

def summarize(report: AgentReport) -> str:
    if not report.selected: return "No candidate strategy produced a valid result."
    m = report.selected.metrics
    return (f"{report.selected.name}: {m.get('return_pct',0):.2f}% return, "
            f"{m.get('net_pnl',0):,.2f} net P&L, {m.get('trades',0)} trades, "
            f"{m.get('win_rate_pct') or 0:.1f}% win rate, "
            f"profit factor {m.get('profit_factor') if m.get('profit_factor') is not None else '—'}, "
            f"max drawdown {m.get('max_drawdown_pct',0):.2f}%. "
            f"Verdict: {consensus_label(report.candidates)}.")
