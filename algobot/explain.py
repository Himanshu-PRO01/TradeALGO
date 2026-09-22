"""Plain-English readback of a strategy config.

Why this exists: when an AI (or a person in a hurry) writes rules, a mistake
such as "RSI under 70" turned into "RSI over 70" still passes every technical
check. The only defence is to read the rules back in ordinary words, produced
by THIS code and not by the AI that wrote them, and let the trader confirm
"yes, that is what I meant".
"""
from __future__ import annotations

import re

_COMPARISONS = [
    (">=", "is at least"),
    ("<=", "is at most"),
    ("==", "equals"),
    ("!=", "is not equal to"),
    (">", "is above"),
    ("<", "is below"),
]


def expression_to_english(expr: str) -> str:
    """Turn a rule like "ema_fast > ema_slow and rsi_14 < 30" into words."""
    text = " " + str(expr).strip() + " "
    text = re.sub(r"\b([A-Za-z_][A-Za-z0-9_]*?)_prev\b", r"previous \1", text)
    text = re.sub(r"(>=|<=|==|!=|>|<)", lambda m: " @@" + m.group(1) + "@@ ", text)
    for symbol, words in _COMPARISONS:
        text = text.replace(f"@@{symbol}@@", words)
    text = re.sub(r"\band\b|&", " AND ", text)
    text = re.sub(r"\bor\b|\|", " OR ", text)
    text = re.sub(r"\bnot\b|~", " NOT ", text)
    return re.sub(r"\s+", " ", text).strip()


def describe_indicator(spec: dict) -> str:
    name, kind = spec.get("name"), spec.get("type")
    period, source = spec.get("period"), spec.get("source", "close")
    if kind == "sma":
        what = f"{period}-bar simple moving average of the {source}"
    elif kind == "ema":
        what = f"{period}-bar exponential moving average of the {source}"
    elif kind == "rsi":
        what = f"{period}-bar RSI (0 to 100) of the {source}"
    elif kind == "atr":
        what = f"{period}-bar average true range (typical bar size)"
    elif kind == "highest":
        what = f"highest high of the previous {period} bars"
    elif kind == "lowest":
        what = f"lowest low of the previous {period} bars"
    elif kind == "vwap":
        what = "volume-weighted average price since the start of the day"
    elif kind in ("prev_day_high", "prev_day_low", "prev_day_close"):
        what = f"the previous trading day's {kind.split('_')[-1]}"
    elif kind in ("prev_week_high", "prev_week_low"):
        what = f"the previous week's {kind.split('_')[-1]}"
    elif kind in ("swing_high", "swing_low"):
        side = "high" if kind == "swing_high" else "low"
        what = (f"the most recent confirmed swing {side}: a {side} that is the "
                f"{'highest' if side == 'high' else 'lowest'} of {period} bars on each side "
                f"(only known {period} bars after it happens)")
    else:
        what = f"{kind} indicator"
    return f"{name} = {what}"


def _rupees(x) -> str:
    return f"Rs {x:,.0f}" if float(x).is_integer() else f"Rs {x:,.2f}"


def explain_config(cfg: dict) -> str:
    """Describe a VALIDATED config (see config.validate_config) in plain words."""
    s, r, c = cfg["strategy"], cfg["risk"], cfg["costs"]
    p = s["params"]
    lines: list[str] = []

    lines.append(f"Account size: {_rupees(cfg['capital'])}. Each trade is {s['quantity']} share(s) or unit(s).")

    lines.append("")
    lines.append("STRATEGY")
    if s["name"] == "sma_crossover":
        fast, slow = p.get("fast", 10), p.get("slow", 30)
        lines.append(f"- Go long when the {fast}-bar average price is above the {slow}-bar average.")
        lines.append(f"- Get out (or go short, if allowed) when it falls below the {slow}-bar average.")
    elif s["name"] == "rules":
        specs = p.get("indicators") or []
        if specs:
            lines.append("Indicators:")
            lines.extend(f"- {describe_indicator(sp)}" for sp in specs)
        for key, label in (
            ("entry_long", "Buy (go long) when"),
            ("exit_long", "Sell to exit a long trade when"),
            ("entry_short", "Sell short when"),
            ("exit_short", "Buy back to exit a short trade when"),
        ):
            expr = p.get(key)
            if expr and str(expr).strip():
                lines.append(f"- {label}: {expression_to_english(expr)}")
        lines.append("(\"previous X\" means the value of X on the bar before.)")
    else:
        lines.append(f"- Custom strategy '{s['name']}' (no plain-English description available).")

    lines.append(
        "- Short selling is allowed." if s["allow_short"]
        else "- Short selling is NOT allowed: a sell signal only closes a long trade."
    )
    lines.append(
        f"- Stop-loss: exit if the price moves {s['stop_loss_pct']}% against the trade."
        if s["stop_loss_pct"] else "- No stop-loss is set (a losing trade is only closed by a rule or at the end of the day)."
    )
    lines.append(
        f"- Take profit at {s['target_pct']}% in favour." if s["target_pct"] else "- No profit target is set."
    )
    lines.append("- Decisions are made when a bar closes and the order is filled at the next bar's open.")

    lines.append("")
    lines.append("RISK LIMITS")
    lines.append(
        f"- New trades only between {r['trading_start']:%H:%M} and {r['no_new_entries_after']:%H:%M}; "
        f"everything is closed at {r['square_off_time']:%H:%M}. Nothing is held overnight."
    )
    lines.append(
        f"- Stop trading for the day after losing {_rupees(r['max_daily_loss'])}."
        if r["max_daily_loss"] else "- No daily loss limit is set."
    )
    lines.append(
        f"- At most {r['max_trades_per_day']} trade(s) a day." if r["max_trades_per_day"] else "- No limit on trades per day."
    )
    lines.append(
        f"- Largest single position: {_rupees(r['max_position_value'])}."
        if r["max_position_value"] else "- No limit on position size."
    )

    lines.append("")
    lines.append("COSTS USED IN THE TEST")
    brokerage = (
        f"flat {_rupees(c['brokerage_flat'])} per order" if c["brokerage_flat"] is not None
        else f"{c['brokerage_pct']}% of order value"
        + (f" (max {_rupees(c['brokerage_cap'])} per order)" if c["brokerage_cap"] is not None else "")
    )
    lines.append(
        f"- Brokerage {brokerage}; STT {c['stt_sell_pct']}% on sells and {c['stt_buy_pct']}% on buys; "
        f"exchange charges {c['exchange_txn_pct']}%; SEBI fee {c['sebi_fee_pct']}%; "
        f"stamp duty {c['stamp_buy_pct']}% on buys; GST {c['gst_pct']}% on brokerage and fees."
    )
    lines.append(f"- Slippage: every market-type fill is {c['slippage_bps']} bps ({c['slippage_bps'] / 100:.2f}%) worse than the quoted price.")
    lines.append("- Check these rates against your broker's charge calculator: the defaults are only examples.")
    return "\n".join(lines)
