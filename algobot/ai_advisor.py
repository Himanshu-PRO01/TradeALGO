"""AI Trade Advisor for the Practice Room.

Uses real-time market snapshot (spot, recent bars) and Black-Scholes greeks
to produce plain-English trade suggestions with entry / stop / target.

Design constraints:
  * No external LLM or internet call other than what live_data.py already does.
  * All math is the same Black-Scholes model the practice room already uses.
  * Returns a structured dict so the UI can display it however it wants.
  * Conservative: prefers risk/reward >= 1.5 and only suggests when a clear
    trend or momentum signal is present.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from .options import bs_greeks, bs_price

# ── constants ──────────────────────────────────────────────────────────────────
_MIN_RR = 1.5          # minimum reward-to-risk ratio for a suggestion
_TREND_BARS = 10       # bars used for trend slope
_MOM_BARS   = 5        # bars for short momentum
_IV_DEFAULT = 14.0     # fallback IV when none supplied


@dataclass
class TradeIdea:
    """One AI-generated trade suggestion."""
    kind:       str            # "CE" or "PE"
    strike:     int
    entry_ask:  float          # premium you would pay
    stop:       float          # exit if premium falls to this
    target:     float          # take profit at this premium
    rr:         float          # reward-to-risk ratio
    delta:      float
    theta:      float          # Rs per day per lot
    breakeven_points: float    # index points the market must move to break even
    lot_size:   int
    signals:    list[str] = field(default_factory=list)   # plain-English reasons
    warnings:   list[str] = field(default_factory=list)


def _ema(series: pd.Series, n: int) -> float:
    """Single EMA value for the last bar, fast."""
    return float(series.ewm(span=n, adjust=False).mean().iloc[-1])


def _rsi(close: pd.Series, n: int = 14) -> float:
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(n).mean()
    loss  = (-delta.clip(upper=0)).rolling(n).mean()
    if loss.iloc[-1] == 0:
        return 100.0
    rs = gain.iloc[-1] / loss.iloc[-1]
    return float(100.0 - 100.0 / (1.0 + rs))


def _trend_slope(close: pd.Series, n: int) -> float:
    """Slope of a linear regression of the last n closes, normalised by the last close."""
    c = close.iloc[-n:]
    if len(c) < 2:
        return 0.0
    x = range(len(c))
    xm = sum(x) / len(x)
    ym = sum(c) / len(c)
    num   = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, c))
    denom = sum((xi - xm) ** 2 for xi in x)
    slope = (num / denom) if denom else 0.0
    return slope / float(c.iloc[-1])   # normalise


def _strikes_around(spot: float, step: int, each_side: int = 5) -> list[int]:
    atm = int(round(spot / step) * step)
    return [atm + k * step for k in range(-each_side, each_side + 1)]


def analyse(
    bars:      pd.DataFrame,
    spot:      float,
    dte:       float,
    iv_pct:    float,
    strike_step: int = 50,
    lot_size:  int   = 75,
    spread:    float = 0.6,
    charges:   float = 40.0,
    rate:      float = 0.065,
) -> Optional[TradeIdea]:
    """
    Analyse the current market snapshot and return a TradeIdea or None.

    Parameters
    ----------
    bars        : revealed OHLCV dataframe (most-recent-last)
    spot        : current index level
    dte         : calendar days to expiry
    iv_pct      : implied volatility in percent (e.g. 14.0)
    strike_step : strike spacing for the index (50 for Nifty, 100 for Bank Nifty)
    lot_size    : one lot = this many units
    spread      : bid-ask spread in premium points
    charges     : round-trip charges in Rs
    rate        : risk-free rate as fraction
    """
    if bars is None or len(bars) < max(_TREND_BARS, 14) + 2:
        return None          # not enough data to form a view
    if dte <= 0.25:
        return None          # less than 6 hours to expiry: too risky to suggest

    close = bars["close"].dropna()
    iv    = iv_pct / 100.0

    # ── signals ────────────────────────────────────────────────────────────────
    trend_slope  = _trend_slope(close, _TREND_BARS)
    mom_slope    = _trend_slope(close, _MOM_BARS)
    rsi_val      = _rsi(close)
    ema20        = _ema(close, 20)
    ema9         = _ema(close, 9)

    signals  : list[str] = []
    warnings : list[str] = []
    bias = 0   # +ve = bullish, -ve = bearish

    # Trend
    if trend_slope > 0.0002:
        bias += 1
        signals.append(f"10-bar trend is UP (slope {trend_slope*100:+.3f}%/bar).")
    elif trend_slope < -0.0002:
        bias -= 1
        signals.append(f"10-bar trend is DOWN (slope {trend_slope*100:+.3f}%/bar).")
    else:
        signals.append("10-bar trend is flat — no strong directional edge.")

    # Momentum
    if mom_slope > 0.0003:
        bias += 1
        signals.append("Short-term momentum is positive (market accelerating up).")
    elif mom_slope < -0.0003:
        bias -= 1
        signals.append("Short-term momentum is negative (market accelerating down).")

    # EMA stack
    if ema9 > ema20:
        bias += 1
        signals.append(f"9 EMA ({ema9:,.1f}) is above 20 EMA ({ema20:,.1f}) — bullish stack.")
    elif ema9 < ema20:
        bias -= 1
        signals.append(f"9 EMA ({ema9:,.1f}) is below 20 EMA ({ema20:,.1f}) — bearish stack.")

    # RSI
    if rsi_val > 60:
        signals.append(f"RSI {rsi_val:.0f} — momentum in buyers' favour.")
        bias += 1
    elif rsi_val < 40:
        signals.append(f"RSI {rsi_val:.0f} — momentum in sellers' favour.")
        bias -= 1
    elif rsi_val > 70:
        warnings.append(f"RSI {rsi_val:.0f} — overbought, risk of pullback.")
    elif rsi_val < 30:
        warnings.append(f"RSI {rsi_val:.0f} — oversold, risk of bounce.")

    # DTE caution
    if dte < 1.0:
        warnings.append(f"Only {dte:.1f} DTE left — time decay is very fast. Use tight stops.")
    elif dte < 2.0:
        warnings.append(f"{dte:.1f} DTE — theta burn is accelerating. Keep holding time short.")

    # Need at least 2 signals pointing the same way
    if abs(bias) < 2:
        return None   # no clear edge — don't suggest anything

    kind = "CE" if bias > 0 else "PE"

    # ── pick the best strike (slightly OTM for cost efficiency) ────────────────
    atm    = int(round(spot / strike_step) * strike_step)
    otm_1  = atm + strike_step if kind == "CE" else atm - strike_step
    otm_2  = atm + 2 * strike_step if kind == "CE" else atm - 2 * strike_step

    best_idea = None
    for candidate_strike in (atm, otm_1, otm_2):
        mid   = bs_price(spot, candidate_strike, dte, iv, "call" if kind == "CE" else "put", rate)
        ask   = mid + spread / 2.0
        bid   = max(mid - spread / 2.0, 0.05)
        if ask < 0.5:
            continue   # premium too low to trade sensibly

        greeks = bs_greeks(spot, candidate_strike, dte, iv, "call" if kind == "CE" else "put", rate)
        delta  = greeks["delta"]
        theta  = greeks["theta"] * lot_size   # Rs/day for one lot

        # Stop: 35% of the ask (common intraday option stop)
        stop   = max(ask * 0.65, 0.05)
        # Target: enough to give RR >= _MIN_RR
        risk   = (ask - stop) * lot_size + charges
        target_premium = ask + risk * _MIN_RR / lot_size
        rr     = (target_premium - ask) * lot_size / risk

        # Breakeven: how far must index move?
        one_day_later = bs_price(spot, candidate_strike, max(dte - 1, 0), iv,
                                 "call" if kind == "CE" else "put", rate)
        # simple bisection on 0..50% of spot
        be = _fast_breakeven(spot, candidate_strike, dte, iv, kind, ask + spread / 2.0, rate)

        idea = TradeIdea(
            kind=kind,
            strike=candidate_strike,
            entry_ask=round(ask, 2),
            stop=round(stop, 2),
            target=round(target_premium, 2),
            rr=round(rr, 2),
            delta=round(delta, 3),
            theta=round(theta, 0),
            breakeven_points=round(be, 1),
            lot_size=lot_size,
            signals=list(signals),
            warnings=list(warnings),
        )
        if best_idea is None or abs(idea.delta) > 0.25:
            best_idea = idea
            break   # take first viable (ATM-or-slightly-OTM with decent delta)

    return best_idea


def _fast_breakeven(spot: float, strike: float, dte: float, iv: float,
                    kind: str, cost: float, rate: float) -> float:
    """Index points the market must move for the option to reach `cost` (break even)."""
    call = kind == "CE"
    sign = 1.0 if call else -1.0
    lo, hi = 0.0, spot * 0.5
    if bs_price(spot + sign * hi, strike, dte, iv, "call" if call else "put", rate) < cost:
        return float("inf")
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if bs_price(spot + sign * mid, strike, dte, iv, "call" if call else "put", rate) < cost:
            lo = mid
        else:
            hi = mid
    return hi


def format_idea(idea: TradeIdea) -> str:
    """Plain-English summary of a TradeIdea, for the Practice Room's AI panel."""
    direction = "UP" if idea.kind == "CE" else "DOWN"
    lines = [
        f"**🤖 AI Suggestion: Buy {idea.kind} {idea.strike} ({direction} bet)**",
        "",
        "**Why:**",
    ]
    for s in idea.signals:
        lines.append(f"- {s}")
    lines += [
        "",
        f"**Entry (ask):** ₹{idea.entry_ask:.2f}  ·  One lot costs ₹{idea.entry_ask * idea.lot_size:,.0f}",
        f"**Stop-loss:**   ₹{idea.stop:.2f}  (exit if premium falls to this)",
        f"**Target:**      ₹{idea.target:.2f}  (reward-to-risk ≈ {idea.rr:.1f}×)",
        f"**Delta:** {idea.delta:+.3f}  ·  **Theta:** ₹{abs(idea.theta):,.0f}/day decay (per lot)",
        f"**Breakeven:** index must move **{idea.breakeven_points:,.1f} points** in your favour just to cover costs.",
        "",
    ]
    if idea.warnings:
        lines.append("**⚠️ Cautions:**")
        for w in idea.warnings:
            lines.append(f"- {w}")
    lines += [
        "",
        "_These are model prices, not live quotes. Treat this as a learning aid, not financial advice._",
    ]
    return "\n".join(lines)
