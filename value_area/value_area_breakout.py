#!/usr/bin/env python3
"""Backtest: prior-day Value Area breakout (long only).

Rules (see STRATEGY_SPEC.md for the assumptions behind each one)
  1. Build yesterday's volume profile -> POC, VAH, VAL (value area = 70% of volume).
  2. On 15-minute candles, signal when a candle CLOSES above VAH on LOW relative volume.
  3. Optional: the price must have come back into the zone earlier the same day.
  4. Enter at the NEXT candle's open. Stop = signal candle low. Target = entry + RR x risk.
  5. One trade per day, flat by the square-off time.

Needs an instrument with REAL volume (stocks, futures). Index data has volume 0 and is refused.
Input CSV columns: datetime,open,high,low,close,volume (any intraday timeframe <= 15 min).

    python value_area_breakout.py --csv data/stock_1min.csv
    python value_area_breakout.py --csv data/stock_1min.csv --grid
    python value_area_breakout.py --synthetic        # code check only, results are meaningless
"""
from __future__ import annotations

import argparse
import itertools
import os
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Params:
    value_area_pct: float = 0.70
    tick: float | None = None          # price bin width; None = auto (~2 bps of price)
    low_volume_ratio: float | None = 0.8   # signal needs rel. volume <= this; None = no volume filter
    vol_lookback_days: int = 20        # same-time-of-day volume baseline
    require_return_to_zone: bool = True  # price must have overlapped [VAL, VAH] earlier that day
    require_fresh_cross: bool = True   # previous 15m close must be <= VAH
    rr: float = 2.0
    min_risk_pct: float = 0.05         # skip trades whose stop is closer than this (% of entry)
    max_risk_pct: float = 1.5          # skip trades whose stop is farther than this
    first_signal_time: str = "09:30"   # first candle that may close a signal
    last_entry_time: str = "14:45"     # no signal candles starting after this
    square_off_time: str = "15:15"
    cost_bps_per_side: float = 3.0
    slippage_bps_per_side: float = 2.0


# --------------------------------------------------------------------------- data
def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def resample_15m(df: pd.DataFrame) -> pd.DataFrame:
    out = df.resample("15min", label="left", closed="left", offset="15min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return out.dropna(subset=["open", "close"])


def synthetic(days: int = 60, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows, price = [], 1000.0
    for d in pd.bdate_range("2025-01-01", periods=days):
        idx = pd.date_range(d + pd.Timedelta(hours=9, minutes=15), d + pd.Timedelta(hours=15, minutes=29), freq="1min")
        for i, ts in enumerate(idx):
            ret = rng.normal(0, 0.0004)
            o, c = price, price * (1 + ret)
            h, l = max(o, c) * (1 + abs(rng.normal(0, 0.0002))), min(o, c) * (1 - abs(rng.normal(0, 0.0002)))
            u = i / len(idx)
            vol = max(1.0, rng.gamma(2.0, 400) * (1.8 if u < 0.1 or u > 0.9 else 1.0))
            rows.append((ts, o, h, l, c, vol))
            price = c
    return pd.DataFrame(rows, columns=["datetime", "open", "high", "low", "close", "volume"]).set_index("datetime")


def fetch_upstox_1m(instrument_key: str, start: str, end: str) -> pd.DataFrame:
    """Optional: 1-minute candles from Upstox (token from UPSTOX_ANALYTICS_TOKEN). Not covered by tests."""
    import requests
    from urllib.parse import quote

    token = os.environ["UPSTOX_ANALYTICS_TOKEN"].strip()
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    rows, cur, stop = [], pd.Timestamp(start), pd.Timestamp(end)
    while cur <= stop:
        chunk_end = min(cur + pd.Timedelta(days=28), stop)
        url = (f"https://api.upstox.com/v3/historical-candle/{quote(instrument_key, safe='')}"
               f"/minutes/1/{chunk_end.date()}/{cur.date()}")
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        for c in (r.json().get("data") or {}).get("candles") or []:
            ts = pd.Timestamp(c[0]).tz_convert("Asia/Kolkata").tz_localize(None)
            rows.append((ts, c[1], c[2], c[3], c[4], c[5] or 0.0))
        cur = chunk_end + pd.Timedelta(days=1)
    df = pd.DataFrame(rows, columns=["datetime", "open", "high", "low", "close", "volume"]).set_index("datetime")
    return df.sort_index()[~df.sort_index().index.duplicated()].astype(float)


# ------------------------------------------------------------------ value area
def value_area(day: pd.DataFrame, pct: float = 0.70, tick: float | None = None) -> tuple[float, float, float]:
    """Return (VAL, POC, VAH) from one session of OHLCV bars.

    Each bar's volume is spread evenly over the price bins it traded through.
    The value area grows out from the POC, adding whichever side (two bins at a time) has more volume,
    until it holds `pct` of the session's volume.
    """
    lo, hi = float(day["low"].min()), float(day["high"].max())
    if tick is None:
        tick = max(round(float(day["close"].median()) * 0.0002 / 0.05) * 0.05, 0.05)
    n = max(int(np.ceil((hi - lo) / tick)) + 1, 1)
    hist = np.zeros(n)
    for l, h, v in zip(day["low"].to_numpy(), day["high"].to_numpy(), day["volume"].to_numpy()):
        a, b = int((l - lo) // tick), int((h - lo) // tick)
        hist[a:b + 1] += v / (b - a + 1)
    total = hist.sum()
    poc = int(hist.argmax())
    low_i = high_i = poc
    acc = hist[poc]
    while acc < pct * total and (low_i > 0 or high_i < n - 1):
        up = hist[high_i + 1:high_i + 3].sum() if high_i < n - 1 else -1.0
        dn = hist[max(low_i - 2, 0):low_i].sum() if low_i > 0 else -1.0
        if up >= dn:
            step = hist[high_i + 1:high_i + 3]
            acc += step.sum()
            high_i = min(high_i + len(step), n - 1)
        else:
            step = hist[max(low_i - 2, 0):low_i]
            acc += step.sum()
            low_i = max(low_i - len(step), 0)
    price = lambda i: lo + i * tick
    return price(low_i), price(poc), price(high_i + 1)


def prior_day_levels(fine: pd.DataFrame, p: Params) -> pd.DataFrame:
    """One row per session with the PREVIOUS session's VAL/POC/VAH (no look-ahead)."""
    rows = {}
    for day, g in fine.groupby(fine.index.normalize()):
        if g["volume"].sum() > 0:
            rows[day] = value_area(g, p.value_area_pct, p.tick)
    lv = pd.DataFrame.from_dict(rows, orient="index", columns=["val", "poc", "vah"]).sort_index()
    return lv.shift(1).dropna()


# ----------------------------------------------------------------------- engine
def _minutes(s: str) -> int:
    return int(s[:2]) * 60 + int(s[3:])


def add_relative_volume(b: pd.DataFrame, days: int) -> pd.Series:
    """Volume divided by the average of the same time slot over the PRIOR `days` sessions."""
    slot = b.index.strftime("%H:%M")
    base = (b["volume"].groupby(slot).transform(lambda s: s.shift(1).rolling(days, min_periods=max(days // 2, 3)).mean()))
    return b["volume"] / base.replace(0, np.nan)


def run_backtest(fine: pd.DataFrame, p: Params = Params()) -> pd.DataFrame:
    """Return one row per trade. `fine` is OHLCV at <= 15-minute resolution."""
    if fine["volume"].sum() <= 0:
        raise ValueError("No volume in this data (indices have none). Use a stock or a futures contract.")
    bars = resample_15m(fine)
    bars["relvol"] = add_relative_volume(bars, p.vol_lookback_days)
    levels = prior_day_levels(fine, p)
    first, last_entry, sq = _minutes(p.first_signal_time), _minutes(p.last_entry_time), _minutes(p.square_off_time)
    trades = []
    for day, g in bars.groupby(bars.index.normalize()):
        if day not in levels.index:
            continue
        val, vah = levels.loc[day, "val"], levels.loc[day, "vah"]
        mins = g.index.hour * 60 + g.index.minute
        touched, prev_close, i = False, np.nan, 0
        rows = list(g.itertuples())
        while i < len(rows) - 1:
            r = rows[i]
            m = mins[i]
            touched = touched or (r.low <= vah and r.high >= val)
            ok_time = first <= m + 15 and m <= last_entry          # candle closes at m+15
            fresh = (not p.require_fresh_cross) or (np.isnan(prev_close) or prev_close <= vah)
            vol_ok = p.low_volume_ratio is None or (not np.isnan(r.relvol) and r.relvol <= p.low_volume_ratio)
            zone_ok = touched or not p.require_return_to_zone
            prev_close = r.close
            if ok_time and r.close > vah and fresh and vol_ok and zone_ok:
                entry_bar = rows[i + 1]
                entry_fill = entry_bar.open * (1 + p.slippage_bps_per_side / 1e4)
                stop = r.low
                risk = entry_fill - stop
                risk_pct = risk / entry_fill * 100
                if risk <= 0 or not (p.min_risk_pct <= risk_pct <= p.max_risk_pct):
                    i += 1
                    continue
                target = entry_fill + p.rr * risk
                exit_px, reason, exit_time = None, "square_off", None
                for j in range(i + 1, len(rows)):
                    c = rows[j]
                    cm = mins[j]
                    if j > i + 1 and cm >= sq:
                        exit_px, exit_time = c.open, g.index[j]; break
                    if j == i + 1 and c.open <= stop:
                        exit_px, reason, exit_time = c.open, "stop_gap", g.index[j]; break
                    if c.low <= stop:                      # stop checked first: the pessimistic choice
                        exit_px, reason, exit_time = stop, "stop", g.index[j]; break
                    if c.high >= target:
                        exit_px, reason, exit_time = target, "target", g.index[j]; break
                if exit_px is None:
                    exit_px, exit_time = rows[-1].close, g.index[-1]
                gross = exit_px - entry_fill
                net = gross - exit_px * (p.cost_bps_per_side + p.slippage_bps_per_side) / 1e4
                trades.append({"date": day, "entry_time": g.index[i + 1], "exit_time": exit_time,
                               "entry": entry_fill, "stop": stop, "target": target, "exit": exit_px,
                               "reason": reason, "risk_pct": risk_pct, "r_multiple": net / risk,
                               "ret_pct": net / entry_fill * 100, "vah": vah, "val": val, "relvol": r.relvol})
                break                                          # one trade per day
            i += 1
    return pd.DataFrame(trades)


# ---------------------------------------------------------------------- metrics
def summarize(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"trades": 0}
    r, w, l = t["r_multiple"], t[t["r_multiple"] > 0]["r_multiple"], t[t["r_multiple"] <= 0]["r_multiple"]
    eq = r.cumsum()
    streak = best = 0
    for x in r:
        streak = streak + 1 if x <= 0 else 0
        best = max(best, streak)
    return {"trades": len(t), "win_rate_%": round(float(100 * (r > 0).mean()), 1), "avg_R": round(float(r.mean()), 3),
            "profit_factor": round(float(w.sum() / abs(l.sum())), 2) if l.sum() != 0 else float("inf"),
            "total_R": round(float(r.sum()), 2), "max_drawdown_R": round(float((eq.cummax() - eq).max()), 2),
            "longest_losing_streak": best, "avg_ret_%": round(float(t["ret_pct"].mean()), 3)}


def split_report(t: pd.DataFrame, frac: float = 0.6) -> None:
    if len(t) < 10:
        print("  (too few trades to split in-sample / out-of-sample)"); return
    cut = int(len(t) * frac)
    print("  in-sample :", summarize(t.iloc[:cut]))
    print("  out-sample:", summarize(t.iloc[cut:]))


def grid(fine: pd.DataFrame, base: Params) -> pd.DataFrame:
    rows = []
    for lv, ret, rr in itertools.product([0.6, 0.8, 1.0, None], [True, False], [1.5, 2.0, 3.0]):
        p = replace(base, low_volume_ratio=lv, require_return_to_zone=ret, rr=rr)
        s = summarize(run_backtest(fine, p))
        rows.append({"low_vol_ratio": "none" if lv is None else lv, "return_to_zone": ret, "rr": rr, **s})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv"); ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--upstox-key"); ap.add_argument("--start"); ap.add_argument("--end")
    ap.add_argument("--grid", action="store_true"); ap.add_argument("--save-trades")
    a = ap.parse_args()
    if a.synthetic:
        df = synthetic(); print("SYNTHETIC random data: this only checks that the code runs. Results mean nothing.")
    elif a.upstox_key:
        df = fetch_upstox_1m(a.upstox_key, a.start, a.end)
    elif a.csv:
        df = load_csv(a.csv)
    else:
        ap.error("give --csv, --upstox-key (with --start/--end) or --synthetic")
    base = Params()
    trades = run_backtest(df, base)
    print("Base rules:", summarize(trades)); split_report(trades)
    if len(trades) < 100:
        print(f"WARNING: only {len(trades)} trades. Under ~100 trades, results are mostly noise.")
    if a.save_trades:
        trades.to_csv(a.save_trades, index=False)
    if a.grid:
        with pd.option_context("display.width", 200, "display.max_columns", 20):
            print(grid(df, base).to_string(index=False))


if __name__ == "__main__":
    main()
