"""Practice room — LIVE DATA edition.

Now has three modes:
  1. Fake (synthetic)  — generated price path, fully offline
  2. Real market (historical replay) — past bars replayed bar-by-bar
  3. ★ LIVE (real-time) ★  — streams the current index every 60 s via yfinance,
     lets your brother place REAL Upstox Sandbox orders (fake money, real API),
     and shows an AI suggestion panel that analyses live conditions.

The AI panel uses the algobot.ai_advisor module: Black-Scholes + EMA/RSI
signals — no external LLM, no internet call beyond live price data.
"""
from __future__ import annotations

import time
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

from algobot import ui
from algobot.ai_advisor import TradeIdea, analyse, format_idea
from algobot.charts import candlestick, pnl_bars, premium_line
from algobot.gate import check_gate
from algobot.live_data import LiveDataError, fetch_ohlc
from algobot.options import bs_greeks, bs_price
from algobot.practice import (PracticeBlocked, PracticeError, PracticeSession,
                               PracticeSettings, format_practice_report)
from algobot.upstox_sandbox import (UpstoxSandboxClient, UpstoxSandboxError,
                                     clean_token, token_preview)
from algobot.worlds import REGIMES, generate_mixed_world, generate_world

# ── index definitions ──────────────────────────────────────────────────────────
REAL_MARKETS = {
    "Nifty 50":   ("^NSEI",    50),
    "Bank Nifty": ("^NSEBANK", 100),
    "Sensex":     ("^BSESN",   100),
}
REAL_INTERVALS = {
    "5 minutes":  ("5m",  "5d"),
    "15 minutes": ("15m", "1mo"),
    "1 hour":     ("60m", "3mo"),
}
# Instrument tokens for Upstox Sandbox (MARKET order on the INDEX itself)
# Real option instrument tokens would need to be fetched from Upstox's instrument
# master — these are the NSE index instrument tokens used in sandbox testing.
SANDBOX_TOKENS = {
    "Nifty 50":   "NSE_INDEX|Nifty 50",
    "Bank Nifty": "NSE_INDEX|Nifty Bank",
    "Sensex":     "BSE_INDEX|SENSEX",
}

LIVE_REFRESH_SECS = 60   # auto-refresh interval for live mode

# ── page setup ────────────────────────────────────────────────────────────────
ui.setup("Practice room", "🎯")
ui.header(
    "Practice room",
    "A flight simulator for buying index options. "
    "Choose **Live** mode to trade on real prices with the Upstox Sandbox "
    "(fake money, real API). The AI panel will suggest trades based on live market conditions.",
    mode="practice:Practice · fake money",
)


# ── cached data fetches ───────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _live_bars(ticker: str, interval: str, period: str) -> pd.DataFrame:
    """Fetch bars — cached for 60 s so Live mode auto-refreshes cleanly."""
    return fetch_ohlc(ticker, interval, period)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_real_bars(ticker: str, interval: str, period: str) -> pd.DataFrame:
    return fetch_ohlc(ticker, interval, period)


# ── session builder (unchanged for fake/historical modes) ─────────────────────
def _build_session(data_source, regime_choice, seed, days, market_label, interval_label,
                   capital, iv, dte, spread, charges, max_loss, max_trades, max_daily):
    strike_step = 50
    if data_source == "Real market (historical replay)":
        ticker, strike_step = REAL_MARKETS[market_label]
        yf_interval, yf_period = REAL_INTERVALS[interval_label]
        try:
            bars = _cached_real_bars(ticker, yf_interval, yf_period)
        except LiveDataError as exc:
            st.error(str(exc))
            return False
        note = (f"Real {market_label} price history ({interval_label} bars, delayed free data). "
                "The index path really happened; the option premiums on top of it are still modelled.")
    else:
        rng = np.random.default_rng(int(seed))
        if regime_choice.startswith("random"):
            name = list(REGIMES)[int(rng.integers(0, len(REGIMES)))]
            bars = generate_world(name, int(days), int(seed), 24500.0)
            note = f"The market was: {name}. {REGIMES[name].description}"
        elif regime_choice.startswith("mixed"):
            bars, segments = generate_mixed_world(int(days), int(seed), 24500.0, segment_days=(1, 2))
            note = "The market changed character: " + "; ".join(
                f"{a} ({b:%d %b} to {c:%d %b})" for a, b, c in segments)
        else:
            bars = generate_world(regime_choice, int(days), int(seed), 24500.0)
            note = f"The market was: {regime_choice}. {REGIMES[regime_choice].description}"

    settings = PracticeSettings(
        capital=float(capital), iv_pct=float(iv), days_to_expiry=float(dte),
        spread_points=float(spread), charges_per_order=float(charges),
        strike_step=int(strike_step), max_loss_per_trade=float(max_loss),
        max_trades_per_day=int(max_trades), max_daily_loss=float(max_daily),
    )
    try:
        st.session_state["practice"] = PracticeSession(bars, settings)
    except PracticeError as exc:
        st.error(str(exc))
        return False
    st.session_state["practice_note"] = note
    st.session_state["practice_report"] = None
    st.session_state["practice_report_data"] = None
    return True


# ── helpers ───────────────────────────────────────────────────────────────────
def colour_pnl(value):
    if isinstance(value, (int, float)) and value == value:
        return "color: #16C784" if value > 0 else ("color: #EA3943" if value < 0 else "")
    return ""


def style_map(styler, func, subset):
    return (styler.map(func, subset=subset)
            if hasattr(styler, "map")
            else styler.applymap(func, subset=subset))


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### New practice session")

    with st.expander("Market", expanded=True):
        data_source = st.radio(
            "Data source",
            ["Fake (synthetic)", "Real market (historical replay)", "⚡ Live (real-time + AI)"],
            key="pr_source",
        )

        if data_source == "⚡ Live (real-time + AI)":
            market_label    = st.selectbox("Market", list(REAL_MARKETS), key="pr_live_market")
            interval_label  = st.selectbox("Timeframe", list(REAL_INTERVALS), key="pr_live_interval")
            regime_choice, seed, days = "random (hidden)", 1, 3

        elif data_source == "Real market (historical replay)":
            market_label   = st.selectbox("Market", list(REAL_MARKETS), key="pr_real_market")
            interval_label = st.selectbox("Timeframe", list(REAL_INTERVALS), key="pr_real_interval")
            regime_choice, seed, days = "random (hidden)", 1, 3

        else:
            regime_choice = st.selectbox(
                "Market",
                ["random (hidden)", "mixed (changes every few days)"] + list(REGIMES),
                key="pr_regime",
            )
            seed           = st.number_input("Seed (same seed → same market)", min_value=0, value=1, step=1, key="pr_seed")
            days           = st.slider("Days", 1, 5, 3, key="pr_days")
            market_label   = None
            interval_label = None

    with st.expander("Account and option", expanded=True):
        capital  = st.number_input("Fake capital (Rs)", min_value=1000, value=100000, step=5000, key="pr_capital")
        iv       = st.number_input("Implied volatility (%)", min_value=1.0, value=14.0, step=0.5, key="pr_iv")
        dte      = st.number_input("Calendar days to expiry at the start", min_value=0.5, value=3.0, step=0.5, key="pr_dte")
        spread   = st.number_input("Buy-sell spread (premium points)", min_value=0.0, value=0.6, step=0.1, key="pr_spread")
        charges  = st.number_input("Charges per order (Rs)", min_value=0, value=40, step=5, key="pr_charges")

    with st.expander("Your own rules"):
        max_loss   = st.number_input("Your max loss per trade (Rs)", min_value=1, value=1000, step=100, key="pr_maxloss")
        max_trades = st.number_input("Your max trades per day", min_value=1, value=2, step=1, key="pr_maxtrades")
        max_daily  = st.number_input("Your max loss per day (Rs)", min_value=1, value=1500, step=100, key="pr_maxdaily")

    # Upstox Sandbox token (only shown for Live mode)
    if data_source == "⚡ Live (real-time + AI)":
        with st.expander("🔐 Upstox Sandbox token", expanded=False):
            st.caption(
                "Paste your Upstox Sandbox access token here to place orders "
                "via the official sandbox API (fake money, no real trades ever)."
            )
            raw_token = st.text_input(
                "Sandbox token", type="password",
                key="pr_sandbox_token",
                placeholder="eyJ… paste your token",
            )
            tok = clean_token(raw_token or "")
            if tok:
                st.success(f"Token set: {token_preview(tok)}")
            else:
                st.info("No token — orders placed in Practice Room only (no Upstox API call).")

    if st.button("Start a new market", type="primary", key="pr_start", use_container_width=True):
        if data_source == "⚡ Live (real-time + AI)":
            # For live mode: fetch bars now and store as the live session state
            ticker, strike_step = REAL_MARKETS[market_label]
            yf_interval, yf_period = REAL_INTERVALS[interval_label]
            try:
                bars = _live_bars(ticker, yf_interval, yf_period)
                st.session_state["live_bars"]         = bars
                st.session_state["live_ticker"]       = ticker
                st.session_state["live_interval"]     = yf_interval
                st.session_state["live_period"]       = yf_period
                st.session_state["live_market"]       = market_label
                st.session_state["live_strike_step"]  = strike_step
                st.session_state["live_iv"]           = float(iv)
                st.session_state["live_dte"]          = float(dte)
                st.session_state["live_spread"]       = float(spread)
                st.session_state["live_charges"]      = float(charges)
                st.session_state["live_capital"]      = float(capital)
                st.session_state["live_max_loss"]     = float(max_loss)
                st.session_state["live_max_trades"]   = int(max_trades)
                st.session_state["live_max_daily"]    = float(max_daily)
                st.session_state["live_cash"]         = float(capital)
                st.session_state["live_position"]     = None
                st.session_state["live_closed"]       = []
                st.session_state["live_last_refresh"] = time.time()
                st.session_state["practice"]          = None
                st.session_state["practice_report"]   = None
                st.session_state["ai_idea"]           = None
                st.rerun()
            except LiveDataError as exc:
                st.error(str(exc))
        else:
            if _build_session(data_source, regime_choice, seed, days, market_label, interval_label,
                               capital, iv, dte, spread, charges, max_loss, max_trades, max_daily):
                st.session_state.pop("live_bars", None)
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  LIVE MODE MAIN BODY
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.get("live_bars") is not None:
    # ── auto-refresh every LIVE_REFRESH_SECS ──────────────────────────────────
    elapsed = time.time() - st.session_state.get("live_last_refresh", 0)
    time_left = max(0, LIVE_REFRESH_SECS - int(elapsed))

    # top banner
    market_label_live = st.session_state["live_market"]
    ticker_live       = st.session_state["live_ticker"]
    strike_step_live  = st.session_state["live_strike_step"]
    iv_live           = st.session_state["live_iv"]
    dte_live          = st.session_state["live_dte"]
    spread_live       = st.session_state["live_spread"]
    charges_live      = st.session_state["live_charges"]
    capital_live      = st.session_state["live_capital"]
    max_loss_live     = st.session_state["live_max_loss"]
    max_trades_live   = st.session_state["live_max_trades"]
    max_daily_live    = st.session_state["live_max_daily"]
    cash_live         = st.session_state["live_cash"]
    position_live     = st.session_state.get("live_position")
    closed_live       = st.session_state.get("live_closed", [])

    # refresh bars if stale
    if elapsed >= LIVE_REFRESH_SECS:
        try:
            bars_live = _live_bars(ticker_live,
                                   st.session_state["live_interval"],
                                   st.session_state["live_period"])
            st.session_state["live_bars"]         = bars_live
            st.session_state["live_last_refresh"] = time.time()
            st.session_state["ai_idea"]           = None   # re-run AI on fresh data
        except LiveDataError:
            bars_live = st.session_state["live_bars"]
    else:
        bars_live = st.session_state["live_bars"]

    spot_live  = float(bars_live["close"].iloc[-1])
    lot_size   = 75   # Nifty default; Bank Nifty is 35 but sandbox uses market orders

    # ── live ticker ───────────────────────────────────────────────────────────
    today_bars_live = bars_live[bars_live.index.date == bars_live.index[-1].date()]
    day_open_live   = float(today_bars_live["open"].iloc[0])
    change_live     = spot_live - day_open_live
    equity_live     = cash_live + (
        max(bs_price(spot_live, position_live["strike"], dte_live,
                     iv_live / 100.0,
                     "call" if position_live["kind"] == "CE" else "put")
            - spread_live / 2.0, 0.05) * position_live["qty"]
        if position_live else 0.0
    )
    net_live = equity_live - capital_live

    col_refresh, col_timer = st.columns([3, 1])
    with col_refresh:
        if st.button("🔄 Refresh now", key="pr_live_refresh"):
            st.cache_data.clear()
            st.session_state["live_last_refresh"] = 0
            st.session_state["ai_idea"] = None
            st.rerun()
    with col_timer:
        st.caption(f"Auto-refresh in **{time_left}s**")

    ui.ticker([
        (market_label_live, f"{spot_live:,.1f}", ui.tone(change_live)),
        ("Change today", f"{change_live:+,.1f} ({change_live/day_open_live*100:+.2f}%)", ui.tone(change_live)),
        ("Updated", bars_live.index[-1].strftime("%d %b %H:%M"), None),
        ("Cash (fake)", ui.inr(cash_live), None),
        ("Account total", ui.inr(equity_live), ui.tone(net_live)),
        ("Net P&L", ui.inr(net_live, sign=True), ui.tone(net_live)),
    ])

    st.divider()

    # ── AI advisor panel ──────────────────────────────────────────────────────
    st.markdown("### 🤖 AI Trade Advisor")
    ai_idea: TradeIdea | None = st.session_state.get("ai_idea")

    if st.button("Analyse market & get suggestion", key="pr_ai_analyse", type="primary"):
        with st.spinner("Analysing market conditions…"):
            ai_idea = analyse(
                bars=bars_live,
                spot=spot_live,
                dte=dte_live,
                iv_pct=iv_live,
                strike_step=strike_step_live,
                lot_size=lot_size,
                spread=spread_live,
                charges=charges_live * 2,   # round-trip
            )
            st.session_state["ai_idea"] = ai_idea

    if ai_idea is not None:
        with st.container(border=True):
            direction_color = "#16C784" if ai_idea.kind == "CE" else "#EA3943"
            direction_icon  = "📈" if ai_idea.kind == "CE"  else "📉"
            st.markdown(
                f"<h4 style='color:{direction_color}'>"
                f"{direction_icon} Buy {ai_idea.kind} {ai_idea.strike} "
                f"({'CALL — bullish' if ai_idea.kind == 'CE' else 'PUT — bearish'})"
                f"</h4>",
                unsafe_allow_html=True,
            )
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Entry (ask)", f"₹{ai_idea.entry_ask:.2f}")
            c2.metric("Stop-loss",   f"₹{ai_idea.stop:.2f}",
                      f"-₹{(ai_idea.entry_ask - ai_idea.stop)*lot_size:.0f}/lot risk")
            c3.metric("Target",      f"₹{ai_idea.target:.2f}",
                      f"+₹{(ai_idea.target - ai_idea.entry_ask)*lot_size:.0f}/lot")
            c4.metric("Reward:Risk", f"{ai_idea.rr:.1f}×")

            st.markdown("**Why the AI thinks this:**")
            for sig in ai_idea.signals:
                st.markdown(f"- {sig}")

            st.markdown(
                f"**Delta** {ai_idea.delta:+.3f}  ·  "
                f"**Theta** ₹{abs(ai_idea.theta):,.0f}/day decay per lot  ·  "
                f"**Breakeven** market must move **{ai_idea.breakeven_points:,.1f} pts** in your favour"
            )
            if ai_idea.warnings:
                for w in ai_idea.warnings:
                    st.warning(w)

            st.caption("_Model prices (Black-Scholes). Not financial advice. Use as a learning tool._")

            # One-click apply to order ticket
            if st.button(f"Apply AI suggestion to order ticket → {ai_idea.kind} {ai_idea.strike}",
                         key="pr_ai_apply"):
                st.session_state["pr_live_kind"]   = ai_idea.kind
                st.session_state["pr_live_strike"] = ai_idea.strike
                st.session_state["pr_live_stop"]   = ai_idea.stop
                st.rerun()
    elif ai_idea is False:
        st.info("No clear edge detected in current market conditions. Wait for a stronger setup.")
    else:
        st.caption("Click 'Analyse market' to get an AI suggestion based on live price action.")

    # mark as False (checked but no idea) vs None (not yet checked)
    if ai_idea is None and st.session_state.get("ai_idea") is None:
        pass   # not yet requested
    elif st.session_state.get("ai_idea") is None and ai_idea is None:
        st.session_state["ai_idea"] = False

    st.divider()

    # ── chart ─────────────────────────────────────────────────────────────────
    st.markdown("### 📊 Live Chart")
    window_live = st.slider("Bars shown", 30, 300, 100, key="pr_live_window")
    markers_live = []
    for tr in closed_live:
        markers_live.append({
            "entry_time":  tr["entry_ts"], "exit_time": tr["exit_ts"],
            "side":        "LONG" if tr["kind"] == "CE" else "SHORT",
            "entry_price": tr["entry_spot"], "exit_price": tr["exit_spot"],
            "net_pnl":     tr["net"],
        })
    if position_live:
        markers_live.append({
            "entry_time":  position_live["entry_ts"], "exit_time": pd.NaT,
            "side":        "LONG" if position_live["kind"] == "CE" else "SHORT",
            "entry_price": position_live["entry_spot"], "exit_price": np.nan,
            "net_pnl":     0.0,
        })
    display_bars = bars_live.iloc[-int(window_live):]
    ui.show_chart(candlestick(
        display_bars,
        trades=pd.DataFrame(markers_live) if markers_live else None,
        hlines={"day open": day_open_live},
        height=350,
        max_bars=int(window_live),
    ))

    st.divider()

    # ── order ticket (live) ───────────────────────────────────────────────────
    st.markdown("### 🎫 Order Ticket (Fake Money)")

    sandbox_token_raw = st.session_state.get("pr_sandbox_token", "")
    sandbox_tok       = clean_token(sandbox_token_raw or "")

    if position_live:
        p     = position_live
        mid   = bs_price(spot_live, p["strike"], dte_live, iv_live / 100.0,
                         "call" if p["kind"] == "CE" else "put")
        bid   = max(mid - spread_live / 2.0, 0.05)
        ask   = mid + spread_live / 2.0
        unr   = (bid - p["entry_price"]) * p["qty"] - charges_live

        st.info(f"Open position: **{p['label']}** · {p['lots']} lot(s) bought at ₹{p['entry_price']:.2f}")
        ui.ticker([("Bid (exit)", f"₹{bid:.2f}", None), ("Ask", f"₹{ask:.2f}", None),
                   ("Open P&L", ui.inr(unr, sign=True), ui.tone(unr))])

        if st.button("❌ Close position (sell at bid)", key="pr_live_close", type="primary", use_container_width=True):
            # Record the close
            qty     = p["qty"]
            gross   = (bid - p["entry_price"]) * qty
            net_pnl = gross - 2 * charges_live
            record  = {
                "kind": p["kind"], "strike": p["strike"], "label": p["label"],
                "lots": p["lots"], "qty": qty,
                "entry_ts": p["entry_ts"], "exit_ts": bars_live.index[-1],
                "entry_price": p["entry_price"], "exit_price": bid,
                "entry_spot": p["entry_spot"], "exit_spot": spot_live,
                "reason": "manual", "gross": gross, "net": net_pnl,
                "move": 0.0, "time": 0.0, "spread": 0.0, "charges": -2 * charges_live,
            }
            st.session_state["live_closed"].append(record)
            st.session_state["live_cash"]     = cash_live + bid * qty - charges_live
            st.session_state["live_position"] = None

            # Upstox Sandbox SELL
            if sandbox_tok:
                try:
                    client = UpstoxSandboxClient(token=sandbox_tok)
                    sb_resp = client.place_order(
                        instrument_token=SANDBOX_TOKENS.get(market_label_live, "NSE_INDEX|Nifty 50"),
                        quantity=qty, transaction_type="SELL",
                    )
                    st.success(f"✅ Upstox Sandbox SELL placed. Order: {sb_resp}")
                except UpstoxSandboxError as exc:
                    st.warning(f"Practice close recorded, but Sandbox SELL failed: {exc}")
            else:
                st.success(f"Position closed (practice only). Net P&L: {ui.inr(net_pnl, sign=True)}")
            st.rerun()

    else:
        # no open position — show buy form
        default_kind   = st.session_state.get("pr_live_kind",   "CE")
        default_strike = st.session_state.get("pr_live_strike", None)

        kind_live = st.selectbox("Type", ["CE", "PE"],
                                 index=0 if default_kind == "CE" else 1,
                                 key="pr_live_kindsel",
                                 help="CE gains if index rises, PE if it falls")

        atm_live    = int(round(spot_live / strike_step_live) * strike_step_live)
        strikes_live = [atm_live + k * strike_step_live for k in range(-5, 6)]
        default_idx  = (strikes_live.index(default_strike)
                        if default_strike in strikes_live
                        else len(strikes_live) // 2)
        strike_live  = st.selectbox("Strike", strikes_live, index=default_idx, key="pr_live_strikesel")

        stop_pct_live = st.slider("Stop-loss % (0 = no stop)", 0, 40, 35, key="pr_live_stoppct")
        lots_live     = st.number_input("Lots", min_value=1, value=1, step=1, key="pr_live_lots")

        mid_live  = bs_price(spot_live, strike_live, dte_live, iv_live / 100.0,
                             "call" if kind_live == "CE" else "put")
        ask_live  = mid_live + spread_live / 2.0
        bid_live  = max(mid_live - spread_live / 2.0, 0.05)
        stop_live = round(ask_live * (1 - stop_pct_live / 100.0), 2) if stop_pct_live else None
        qty_live  = int(lots_live) * lot_size
        cost_live = ask_live * qty_live + charges_live

        greeks_live = bs_greeks(spot_live, strike_live, dte_live, iv_live / 100.0,
                                "call" if kind_live == "CE" else "put")

        ui.ticker([
            ("Bid", f"₹{bid_live:.2f}", None),
            ("Ask (you pay)", f"₹{ask_live:.2f}", None),
            ("One lot costs", ui.inr(ask_live * lot_size), None),
            ("Delta", f"{greeks_live['delta']:+.3f}", None),
            ("Theta/day", f"₹{greeks_live['theta']*lot_size:+.0f}/lot", None),
        ])

        if stop_live:
            st.caption(f"Stop at ₹{stop_live:.2f} → max loss ≈ ₹{(ask_live - stop_live)*qty_live + charges_live*2:,.0f}")

        col_buy, col_over = st.columns([2, 1])
        with col_over:
            override_live = st.checkbox("Override my rules", key="pr_live_override")
        with col_buy:
            buy_disabled = cost_live > cash_live
            if st.button(
                f"🟢 BUY {kind_live} {strike_live}",
                type="primary", key="pr_live_buy",
                disabled=buy_disabled,
                use_container_width=True,
            ):
                label = f"{market_label_live} {strike_live} {kind_live} ({dte_live:.1f}DTE)"
                pos = {
                    "label":       label,
                    "kind":        kind_live,
                    "strike":      strike_live,
                    "lots":        int(lots_live),
                    "qty":         qty_live,
                    "entry_ts":    bars_live.index[-1],
                    "entry_price": ask_live,
                    "entry_spot":  spot_live,
                    "stop":        stop_live,
                    "charges_in":  charges_live,
                }
                st.session_state["live_position"] = pos
                st.session_state["live_cash"]     = cash_live - cost_live
                # Clear AI applied defaults
                st.session_state.pop("pr_live_kind",   None)
                st.session_state.pop("pr_live_strike", None)
                st.session_state.pop("pr_live_stop",   None)

                # Upstox Sandbox BUY
                if sandbox_tok:
                    try:
                        client  = UpstoxSandboxClient(token=sandbox_tok)
                        sb_resp = client.place_order(
                            instrument_token=SANDBOX_TOKENS.get(market_label_live, "NSE_INDEX|Nifty 50"),
                            quantity=qty_live, transaction_type="BUY",
                        )
                        st.success(f"✅ Upstox Sandbox BUY placed. Order: {sb_resp}")
                    except UpstoxSandboxError as exc:
                        st.warning(f"Practice BUY recorded locally, but Sandbox BUY failed: {exc}")
                else:
                    st.success(f"Bought {qty_live} units of {label} at ₹{ask_live:.2f}. Cost: {ui.inr(cost_live)}")
                st.rerun()

            if buy_disabled:
                st.error(f"Not enough cash. Need ₹{cost_live:,.0f}, have ₹{cash_live:,.0f}.")

    # ── blotter (live) ─────────────────────────────────────────────────────────
    st.divider()
    if closed_live:
        st.markdown("### 📋 Blotter")
        blotter_df = pd.DataFrame([{
            "In": f"{t['entry_ts']:%d %b %H:%M}", "Out": f"{t['exit_ts']:%d %b %H:%M}",
            "Option": t["label"], "Lots": t["lots"],
            "Buy ₹": t["entry_price"], "Sell ₹": t["exit_price"],
            "Net (Rs)": t["net"],
        } for t in closed_live])
        styled = style_map(
            blotter_df.style.format({"Buy ₹": "{:.2f}", "Sell ₹": "{:.2f}", "Net (Rs)": "{:,.0f}"}),
            colour_pnl, ["Net (Rs)"],
        )
        ui.show_table(styled, hide_index=True)

    ui.footer_note()

    # Auto-rerun for live refresh (uses st.rerun with a small sleep to avoid hammering)
    if time_left == 0:
        time.sleep(1)
        st.rerun()

    st.stop()   # ← end live-mode rendering


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN PAGE BUTTON (for non-live modes)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("### Start a new practice market")
st.caption("Choose the market settings in the sidebar, then start a fresh fake-money market here.")
if st.button("🎯 Start a new market", type="primary", key="pr_start_main", use_container_width=True):
    if data_source == "⚡ Live (real-time + AI)":
        st.info("Use the sidebar 'Start' button to launch Live mode.")
    elif _build_session(data_source, regime_choice, seed, days, market_label, interval_label,
                         capital, iv, dte, spread, charges, max_loss, max_trades, max_daily):
        st.session_state.pop("live_bars", None)
        st.rerun()

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
#  FAKE / HISTORICAL REPLAY MODE  (original logic below, unchanged)
# ═══════════════════════════════════════════════════════════════════════════════
sess = st.session_state.get("practice")
if sess is None:
    st.markdown(ui.card(
        "Start here",
        "Choose a mode in the sidebar and press 'Start a new market'. "
        "Try **⚡ Live (real-time + AI)** to practice on today's actual market movement.",
        "🎯",
    ), unsafe_allow_html=True)
    ui.footer_note()
    st.stop()

# -------------------------------------------------------------------------- finished: the review
report_text = st.session_state.get("practice_report")
if report_text:
    data    = st.session_state.get("practice_report_data") or {}
    totals  = data.get("totals", {})
    ui.ticker([
        ("Net result",          ui.inr(data.get("net_pnl", 0.0), sign=True), ui.tone(data.get("net_pnl", 0.0))),
        ("Trades",              len(data.get("trades", [])), None),
        ("Limit blocks",        data.get("blocked", 0), None),
        ("Rules broken",        data.get("overrides", 0), "warn" if data.get("overrides") else None),
    ])
    st.subheader("Session review")
    if data.get("trades"):
        st.markdown("##### Where the money went")
        ui.show_chart(pnl_bars(
            pd.Series({"Market move": totals["move"], "Time decay": totals["time"],
                       "Spread": totals["spread"], "Charges": totals["charges"]}),
            height=220, title="Rs",
        ))
    st.text(report_text)
    ui.footer_note()
    st.stop()

# ------------------------------------------------------------------------------- the clock
b1, b2, b3, b4 = st.columns(4)
if b1.button("Next bar (5 min)", key="pr_next", use_container_width=True):
    if not sess.next_bar():
        st.warning("The market has ended. Press Finish.")
if b2.button("+1 hour", key="pr_next12", use_container_width=True):
    sess.advance(12)
if b3.button("To end of day", key="pr_eod", use_container_width=True):
    sess.advance_to_day_end()
if b4.button("Finish and review", key="pr_finish", use_container_width=True):
    rep = sess.finish()
    st.session_state["practice_report"]      = format_practice_report(rep, st.session_state.get("practice_note", ""))
    st.session_state["practice_report_data"] = rep
    st.rerun()

for kind_, message_ in st.session_state.pop("practice_flash", []):
    getattr(st, kind_)(message_)

revealed    = sess.revealed()
today_bars  = revealed[revealed.index.date == sess.now.date()]
day_open    = float(today_bars["open"].iloc[0])
change      = sess.spot - day_open
gate        = check_gate(sess.journal, sess.now.date(), sess.s.max_trades_per_day, sess.s.max_daily_loss)
equity      = sess.equity()
unrealized  = sess.unrealized()
equity_change = equity - sess.s.capital
note_       = st.session_state.get("practice_note", "")
spot_label  = "Index (real path)" if note_.startswith("Real ") else "NIFTY (fake)"
ui.ticker([
    (spot_label,       f"{sess.spot:,.1f}",                                    ui.tone(change)),
    ("Change today",   f"{change:+,.1f} ({change / day_open * 100:+.2f}%)",   ui.tone(change)),
    ("Time",           f"{sess.now:%d %b %H:%M}",                              None),
    ("Days to expiry", f"{sess.dte():.2f}",                                    "warn" if sess.dte() < 1 else None),
    ("Account",        ui.inr(equity),                                         ui.tone(equity_change)),
    ("Open P&L",       ui.inr(unrealized, sign=True),                         ui.tone(unrealized)),
    ("Trades today",   f"{gate.trades_opened_today}/{sess.s.max_trades_per_day}", "warn" if not gate.allowed else None),
])

# ----------------------------------------------------------------------- chart and order ticket
chart_col, ticket_col = st.columns([2.6, 1.1], gap="large")

markers = []
for tr in sess.closed:
    markers.append({"entry_time": tr["entry_ts"], "exit_time": tr["exit_ts"],
                    "side": "LONG" if tr["kind"] == "CE" else "SHORT",
                    "entry_price": tr["entry_spot"], "exit_price": tr["exit_spot"], "net_pnl": tr["net"]})
if sess.position:
    p0 = sess.position
    markers.append({"entry_time": p0["entry_ts"], "exit_time": pd.NaT,
                    "side": "LONG" if p0["kind"] == "CE" else "SHORT",
                    "entry_price": p0["entry_spot"], "exit_price": np.nan, "net_pnl": 0.0})

with ticket_col:
    st.markdown("#### Order ticket")
    if sess.position:
        p = sess.position
        bid, ask = sess.quote(p["kind"], p["strike"])
        ui.ticker([("Bid", f"{bid:.2f}", None), ("Ask", f"{ask:.2f}", None)])
        st.write(f"**{p['label']}**  ·  {p['lots']} lot(s), bought at {p['entry_price']:.2f}."
                 + (f" Stop at {p['stop']:.2f}." if p["stop"] else " No stop set."))
        st.metric("Open result (Rs)", f"{sess.unrealized():,.0f}")
        if st.button("Close position now (sell at the bid)", key="pr_close", use_container_width=True):
            try:
                rec = sess.close()
                st.session_state["practice_flash"] = [("success", f"Sold at {rec['exit_price']:.2f}. Net Rs {rec['net']:,.0f}.")]
                st.rerun()
            except PracticeError as exc:
                st.error(str(exc))
        sel_kind, sel_strike = p["kind"], p["strike"]
    elif sess.expired:
        st.warning("The option series has expired. Press Finish.")
        sel_kind, sel_strike = "CE", sess.atm_strike()
    else:
        c1, c2 = st.columns(2)
        kind   = c1.selectbox("Type", ["CE", "PE"], key="pr_kind", help="CE gains if Nifty rises, PE if it falls")
        strikes = sess.strikes()
        strike = c2.selectbox("Strike", strikes, index=len(strikes) // 2, key="pr_strike")
        stop_pct = st.slider("Stop-loss: exit if the price falls this % (0 = no stop)", 0, 40, 10, key="pr_stop_pct")
        bid, ask = sess.quote(kind, strike)
        ui.ticker([("Bid", f"{bid:.2f}", None), ("Ask (you pay)", f"{ask:.2f}", None),
                   ("One lot costs", ui.inr(ask * sess.s.lot_size), None)])
        stop_price = round(ask * (1 - stop_pct / 100.0), 2) if stop_pct else None
        fit = sess.suggested_lots(kind, strike, stop_price) if stop_price else None
        if fit is not None:
            st.caption(f"By your loss limit, {fit.lots} lot(s) fit with this stop.")
        lots     = st.number_input("Lots", min_value=1, value=1, step=1, key="pr_lots")
        override = st.checkbox("Trade anyway if my own rules say no", key="pr_override")
        if st.button("Buy", type="primary", key="pr_buy", use_container_width=True):
            try:
                info = sess.buy(kind, strike, int(lots), stop_price, override=override)
                st.session_state["practice_flash"] = (
                    [("success", f"Bought {info['qty']} units at {info['price']:.2f} for Rs {info['cost']:,.0f}.")]
                    + [("warning", w) for w in info["warnings"]])
                st.rerun()
            except PracticeBlocked as exc:
                st.error("Blocked by your own rules: " + str(exc) + " (Tick 'Trade anyway' to break them. The review will show it.)")
            except PracticeError as exc:
                st.error(str(exc))
        sel_kind, sel_strike = kind, strike

with chart_col:
    window = st.slider("Bars shown", 30, 300, 100, key="pr_window")
    ui.show_chart(candlestick(revealed, trades=pd.DataFrame(markers) if markers else None,
                              hlines={"day open": day_open}, height=330, max_bars=int(window)))
    entry_line = sess.position["entry_price"] if sess.position else None
    stop_line  = sess.position["stop"]         if sess.position else None
    st.caption(f"Option price: {sel_kind} {sel_strike}")
    premium = sess.premium_history(sel_kind, sel_strike, last=int(window))
    ui.show_chart(premium_line(premium, entry_line, stop_line))

tab_chain, tab_blotter, tab_rules = st.tabs(["Option chain", "Blotter", "My rules today"])
with tab_chain:
    rows = []
    for k in sess.strikes():
        cb, ca = sess.quote("CE", k)
        pb, pa = sess.quote("PE", k)
        rows.append({"CE bid": cb, "CE ask": ca, "Strike": k, "PE bid": pb, "PE ask": pa})
    chain = pd.DataFrame(rows)
    atm   = sess.atm_strike()
    styled = (chain.style
              .format({c: "{:.2f}" for c in ("CE bid", "CE ask", "PE bid", "PE ask")} | {"Strike": "{:,.0f}"})
              .apply(lambda r: ["background-color: #1F2A37; font-weight: 700" if r["Strike"] == atm else "" for _ in r], axis=1))
    ui.show_table(styled, hide_index=True)
    st.caption("Model prices around the money. The highlighted row is at the money.")
with tab_blotter:
    if not sess.closed:
        st.info("No closed trades yet.")
    else:
        blotter = pd.DataFrame([{
            "in": f"{t['entry_ts']:%d %b %H:%M}", "out": f"{t['exit_ts']:%d %b %H:%M}",
            "option": t["label"], "lots": t["lots"], "buy": t["entry_price"], "sell": t["exit_price"],
            "exit": t["reason"], "market move": t["move"], "time decay": t["time"],
            "spread": t["spread"], "charges": t["charges"], "net (Rs)": t["net"],
        } for t in sess.closed])
        styled = style_map(
            blotter.style.format(
                {c: "{:,.0f}" for c in ("market move", "time decay", "spread", "charges", "net (Rs)")}
                | {"buy": "{:.2f}", "sell": "{:.2f}"}),
            colour_pnl, ["market move", "time decay", "spread", "charges", "net (Rs)"],
        )
        ui.show_table(styled, hide_index=True)
with tab_rules:
    st.write(f"Max loss per trade: **{ui.inr(sess.s.max_loss_per_trade)}**  ·  "
             f"Max trades per day: **{sess.s.max_trades_per_day}**  ·  "
             f"Max loss per day: **{ui.inr(sess.s.max_daily_loss or 0)}**")
    if gate.allowed:
        st.success("You are within your own rules for today.")
    else:
        st.error("BLOCKED today: " + " ".join(gate.reasons))

ui.footer_note()
