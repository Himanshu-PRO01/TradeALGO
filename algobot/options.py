"""What a bought option is really up against.

SEBI's FY26 study found that about 97% of individual F&O traders mostly BUY
options and that options account for about 92% of retail losses. One reason:
being right about the direction is not enough. The option also loses value
every day (time decay, "theta"), it can lose value when volatility drops (an
"IV crush", common right after events), and you pay the gap between the buy
and sell price (the spread) plus charges.

This module answers a practical question before you click buy:

    "How far must Nifty move, in my favour, within the time I plan to hold,
     just for this option to break even?"

Prices come from the Black-Scholes model (European options, which Nifty index
options are). A model is only an estimate: real prices differ, especially near
expiry and on event days. Read the numbers as a guide to the SIZE of the
hurdle, not as exact prices. Take days to expiry, the strike and implied
volatility (IV) from your broker's option chain.
"""
from __future__ import annotations

import math

DEFAULT_RATE = 0.065          # approximate risk-free rate (as a fraction)


def _cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _kind(kind: str) -> str:
    k = str(kind).strip().lower()
    if k in ("ce", "call", "c"):
        return "call"
    if k in ("pe", "put", "p"):
        return "put"
    raise ValueError("kind must be CE (call) or PE (put)")


def _d1_d2(spot, strike, T, iv, r, q):
    sd = iv * math.sqrt(T)
    d1 = (math.log(spot / strike) + (r - q + 0.5 * iv * iv) * T) / sd
    return d1, d1 - sd


def bs_price(spot: float, strike: float, days: float, iv: float, kind: str,
             r: float = DEFAULT_RATE, q: float = 0.0) -> float:
    """Black-Scholes price. iv is a fraction (0.14 = 14%). days = calendar days to expiry."""
    call = _kind(kind) == "call"
    T = days / 365.0
    if T <= 0 or iv <= 0:                                  # at expiry: only intrinsic value is left
        return max(spot - strike, 0.0) if call else max(strike - spot, 0.0)
    d1, d2 = _d1_d2(spot, strike, T, iv, r, q)
    if call:
        return spot * math.exp(-q * T) * _cdf(d1) - strike * math.exp(-r * T) * _cdf(d2)
    return strike * math.exp(-r * T) * _cdf(-d2) - spot * math.exp(-q * T) * _cdf(-d1)


def bs_greeks(spot: float, strike: float, days: float, iv: float, kind: str,
              r: float = DEFAULT_RATE, q: float = 0.0) -> dict:
    """delta, gamma, vega (per 1 vol point) and theta (change in price over one calendar day)."""
    call = _kind(kind) == "call"
    T = days / 365.0
    if T <= 0 or iv <= 0:
        itm = spot > strike if call else spot < strike
        return {"delta": (1.0 if call else -1.0) if itm else 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0}
    d1, _ = _d1_d2(spot, strike, T, iv, r, q)
    delta = math.exp(-q * T) * (_cdf(d1) if call else _cdf(d1) - 1.0)
    gamma = math.exp(-q * T) * _pdf(d1) / (spot * iv * math.sqrt(T))
    vega = spot * math.exp(-q * T) * _pdf(d1) * math.sqrt(T) / 100.0
    tomorrow = bs_price(spot, strike, max(days - 1.0, 0.0), iv, kind, r, q)
    theta = tomorrow - bs_price(spot, strike, days, iv, kind, r, q)
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta}


def breakeven_analysis(
    spot: float, strike: float, days_to_expiry: float, iv_pct: float, kind: str, holding_days: float,
    lot_size: int = 65, spread_per_unit: float = 0.0, charges_round_trip: float = 0.0,
    iv_change_pct: float = 0.0, r: float = DEFAULT_RATE, q: float = 0.0,
    entry_premium: float | None = None,
) -> dict:
    """How far must the index move in your favour to break even after time decay and friction?

    entry_premium: the actual ASK you expect to pay per unit. If omitted, the
        Black-Scholes model price is used only as an estimate. Supplying the actual ask
        is safer because a model price may differ materially from the tradable price.
        The ask already contains the entry half of the spread, so with an actual ask only
        the exit half of the spread is added on top; with the model price, the full spread is.
    spread_per_unit: bid-ask gap in premium points (you pay the ask and sell at the bid).
    charges_round_trip: total charges for the round trip in rupees, from your broker's calculator.
    iv_change_pct: change in implied volatility, in vol points, while you hold (negative = IV crush).
    """
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be above 0")
    if days_to_expiry <= 0:
        raise ValueError("days_to_expiry must be above 0")
    if iv_pct <= 0:
        raise ValueError("iv_pct must be above 0 (for example 14 for 14%)")
    if holding_days < 0:
        raise ValueError("holding_days cannot be negative")
    if lot_size < 1 or spread_per_unit < 0 or charges_round_trip < 0:
        raise ValueError("lot_size must be 1 or more; spread and charges cannot be negative")
    if entry_premium is not None and entry_premium <= 0:
        raise ValueError("entry_premium must be above 0 when supplied")

    call = _kind(kind) == "call"
    iv = iv_pct / 100.0
    model_premium = bs_price(spot, strike, days_to_expiry, iv, kind, r, q)
    premium = float(entry_premium) if entry_premium is not None else model_premium
    premium_source = "actual market entry premium" if entry_premium is not None else "Black-Scholes model estimate"
    greeks = bs_greeks(spot, strike, days_to_expiry, iv, kind, r, q)
    # Entry at the model mid pays the whole spread over the round trip. An actual ask already includes the
    # entry half, so only the exit half is still to come (adding all of it would count the entry half twice).
    spread_still_to_pay = spread_per_unit / 2.0 if entry_premium is not None else spread_per_unit
    friction = spread_still_to_pay + charges_round_trip / lot_size

    days_left = max(days_to_expiry - holding_days, 0.0)
    iv_after = max(iv + iv_change_pct / 100.0, 0.0005)
    target = premium + friction
    sign = 1.0 if call else -1.0

    def value_after(move: float) -> float:
        return bs_price(spot + sign * move, strike, days_left, iv_after, kind, r, q)

    low, high = 0.0, spot * 0.5
    if value_after(high) < target:
        breakeven = float("inf")
    elif value_after(0.0) >= target:
        breakeven = 0.0
    else:
        for _ in range(80):
            mid = 0.5 * (low + high)
            if value_after(mid) < target:
                low = mid
            else:
                high = mid
        breakeven = high

    one_sigma = spot * iv * math.sqrt(max(holding_days, 0.0) / 365.0) if holding_days > 0 else 0.0
    # This isolates modelled time decay; it is intentionally separate from the
    # paid entry premium, which can contain a real market bid/ask premium.
    decay = model_premium - bs_price(spot, strike, days_left, iv, kind, r, q)
    return {
        "premium": premium, "model_premium": model_premium, "premium_source": premium_source,
        "cost_per_lot": premium * lot_size,
        "delta": greeks["delta"], "gamma": greeks["gamma"], "vega": greeks["vega"],
        "theta_per_day": greeks["theta"], "theta_per_day_per_lot": greeks["theta"] * lot_size,
        "friction_per_unit": friction, "time_decay_over_hold": decay,
        "decay_pct_of_premium": decay / premium * 100.0 if premium > 0 else 0.0,
        "breakeven_points": breakeven,
        "breakeven_pct_of_spot": breakeven / spot * 100.0 if breakeven != float("inf") else float("inf"),
        "one_sigma_move": one_sigma,
        "sigma_multiple": (breakeven / one_sigma) if one_sigma > 0 and breakeven != float("inf") else None,
        "holding_days": holding_days, "days_left_after": days_left,
    }


def format_breakeven(res: dict, kind: str, lot_size: int) -> str:
    direction = "up" if _kind(kind) == "call" else "down"
    lines = [
        f"Entry premium ({res['premium_source']}): Rs {res['premium']:,.2f}  "
        f"(one lot of {lot_size}: Rs {res['cost_per_lot']:,.0f})",
        f"Delta: {res['delta']:+.2f}   Theta per day: Rs {res['theta_per_day']:+.2f} per unit "
        f"(Rs {res['theta_per_day_per_lot']:+,.0f} per lot)",
        f"Time decay while you hold ({res['holding_days']:g} day(s)): Rs {res['time_decay_over_hold']:,.2f} per unit "
        f"= {res['decay_pct_of_premium']:.0f}% of the premium",
        f"Spread and charges:         Rs {res['friction_per_unit']:,.2f} per unit",
    ]
    be = res["breakeven_points"]
    if be == float("inf"):
        lines.append("Breakeven: not reachable with any realistic move. Do not take this trade.")
    else:
        lines.append(f"Nifty must move {direction} by {be:,.1f} points ({res['breakeven_pct_of_spot']:.2f}%) "
                     "just to break even.")
        if res["sigma_multiple"] is not None:
            lines.append(f"A typical move over {res['holding_days']:g} day(s) is about {res['one_sigma_move']:,.1f} points, "
                         f"so you need {res['sigma_multiple']:.1f}x a typical move before making a rupee.")
    if res["premium_source"] != "actual market entry premium":
        lines.append("You did not supply the actual premium you would pay. This uses a model estimate; do not use it as a tradable price.")
    lines.append("This is a model estimate of the future option value. Real premiums differ, especially near expiry and around events.")
    return "\n".join(lines)


def payoff_curve(
    spot: float, strike: float, days_to_expiry: float, iv_pct: float, kind: str, holding_days: float,
    lot_size: int = 65, entry_premium: float | None = None, spread_per_unit: float = 0.0,
    charges_round_trip: float = 0.0, iv_change_pct: float = 0.0, points: int = 61, span_sigma: float = 2.5,
    r: float = DEFAULT_RATE, q: float = 0.0,
):
    """Profit or loss per lot if the index has moved by X points when you sell, after holding `holding_days`.

    You buy at the ask and sell at the bid; charges are the round-trip total for one lot. The curve crosses
    zero exactly at the breakeven move that breakeven_analysis() reports. Returns a DataFrame with columns
    move (index points, positive = up) and pnl_per_lot.
    """
    import numpy as np
    import pandas as pd

    if points < 3:
        raise ValueError("points must be at least 3")
    base = breakeven_analysis(spot, strike, days_to_expiry, iv_pct, kind, holding_days, lot_size, spread_per_unit,
                              charges_round_trip, iv_change_pct, r=r, q=q, entry_premium=entry_premium)
    call = _kind(kind) == "call"
    iv_after = max(iv_pct / 100.0 + iv_change_pct / 100.0, 0.0005)
    days_left = max(days_to_expiry - holding_days, 0.0)
    ask_paid = entry_premium if entry_premium is not None else base["model_premium"] + spread_per_unit / 2.0
    typical = spot * (iv_pct / 100.0) * math.sqrt(max(holding_days, 0.5) / 365.0)
    span = max(span_sigma * typical, spot * 0.002)
    moves = np.linspace(-span, span, points)
    pnl = []
    for move in moves:
        mid_after = bs_price(spot + move, strike, days_left, iv_after, kind, r, q)
        bid_after = max(mid_after - spread_per_unit / 2.0, 0.0)
        pnl.append((bid_after - ask_paid) * lot_size - charges_round_trip)
    return pd.DataFrame({"move": moves, "pnl_per_lot": pnl})
