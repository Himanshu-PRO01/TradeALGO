"""Practice room: buy and sell Nifty options with fake money in a fake market, for as long as you like."""
import numpy as np
import pandas as pd
import streamlit as st

from algobot import ui
from algobot.charts import candlestick, pnl_bars, premium_line
from algobot.gate import check_gate
from algobot.practice import (PracticeBlocked, PracticeError, PracticeSession, PracticeSettings,
                              format_practice_report)
from algobot.worlds import REGIMES, generate_mixed_world, generate_world

ui.setup("Practice room", "🎯")
ui.header("Practice room", "A flight simulator for buying Nifty options. The market is made up, so you can practise as long "
          "as you like. You only see bars up to now, never ahead. Time decay, spread, charges and your own rules work like "
          "the real thing. Model prices: the shape is real, the numbers are not.", mode="practice:Practice · fake money")


def colour_pnl(value):
    if isinstance(value, (int, float)) and value == value:
        return "color: #16C784" if value > 0 else ("color: #EA3943" if value < 0 else "")
    return ""


def style_map(styler, func, subset):
    return styler.map(func, subset=subset) if hasattr(styler, "map") else styler.applymap(func, subset=subset)


# ----------------------------------------------------------------------- start a new session
with st.sidebar:
    st.markdown("### New practice session")
    with st.expander("Market", expanded=True):
        regime_choice = st.selectbox("Market", ["random (hidden)", "mixed (changes every few days)"] + list(REGIMES),
                                     key="pr_regime")
        seed = st.number_input("Seed (same seed, same market)", min_value=0, value=1, step=1, key="pr_seed")
        days = st.slider("Days", 1, 5, 3, key="pr_days")
    with st.expander("Account and option", expanded=True):
        capital = st.number_input("Fake capital (Rs)", min_value=1000, value=10000, step=1000, key="pr_capital")
        iv = st.number_input("Implied volatility (%)", min_value=1.0, value=14.0, step=0.5, key="pr_iv")
        dte = st.number_input("Calendar days to expiry at the start", min_value=0.5, value=3.0, step=0.5, key="pr_dte")
        spread = st.number_input("Buy-sell spread (premium points)", min_value=0.0, value=0.6, step=0.1, key="pr_spread")
        charges = st.number_input("Charges per order (Rs)", min_value=0, value=40, step=5, key="pr_charges")
    with st.expander("Your own rules"):
        max_loss = st.number_input("Your max loss per trade (Rs)", min_value=1, value=1000, step=100, key="pr_maxloss")
        max_trades = st.number_input("Your max trades per day", min_value=1, value=2, step=1, key="pr_maxtrades")
        max_daily = st.number_input("Your max loss per day (Rs)", min_value=1, value=1500, step=100, key="pr_maxdaily")
    if st.button("Start a new market", type="primary", key="pr_start", width="stretch"):
        rng = np.random.default_rng(int(seed))
        if regime_choice.startswith("random"):
            name = list(REGIMES)[int(rng.integers(0, len(REGIMES)))]
            bars, note = generate_world(name, int(days), int(seed), 24500.0), f"The market was: {name}. {REGIMES[name].description}"
        elif regime_choice.startswith("mixed"):
            bars, segments = generate_mixed_world(int(days), int(seed), 24500.0, segment_days=(1, 2))
            note = "The market changed character: " + "; ".join(f"{a} ({b:%d %b} to {c:%d %b})" for a, b, c in segments)
        else:
            bars, note = generate_world(regime_choice, int(days), int(seed), 24500.0), f"The market was: {regime_choice}. {REGIMES[regime_choice].description}"
        settings = PracticeSettings(capital=float(capital), iv_pct=float(iv), days_to_expiry=float(dte),
                                    spread_points=float(spread), charges_per_order=float(charges),
                                    max_loss_per_trade=float(max_loss), max_trades_per_day=int(max_trades),
                                    max_daily_loss=float(max_daily))
        st.session_state["practice"] = PracticeSession(bars, settings)
        st.session_state["practice_note"] = note
        st.session_state["practice_report"] = None
        st.session_state["practice_report_data"] = None

sess = st.session_state.get("practice")
if sess is None:
    st.markdown(ui.card("Start here", "Press 'Start a new market' in the sidebar. Leave the market on 'random (hidden)' so "
                        "you cannot peek. Nothing here uses real money.", "🎯"), unsafe_allow_html=True)
    ui.footer_note()
    st.stop()

# -------------------------------------------------------------------------- finished: the review
report_text = st.session_state.get("practice_report")
if report_text:
    data = st.session_state.get("practice_report_data") or {}
    totals = data.get("totals", {})
    ui.ticker([("Net result", ui.inr(data.get("net_pnl", 0.0), sign=True), ui.tone(data.get("net_pnl", 0.0))),
               ("Trades", len(data.get("trades", [])), None), ("Limit blocks", data.get("blocked", 0), None),
               ("Rules broken on purpose", data.get("overrides", 0), "warn" if data.get("overrides") else None)])
    st.subheader("Session review")
    if data.get("trades"):
        st.markdown("##### Where the money went")
        ui.show_chart(pnl_bars(pd.Series({"Market move": totals["move"], "Time decay": totals["time"],
                                          "Spread": totals["spread"], "Charges": totals["charges"]}),
                               height=220, title="Rs"))
    st.text(report_text)
    ui.footer_note()
    st.stop()

# ------------------------------------------------------------------------------- the clock
b1, b2, b3, b4 = st.columns(4)
if b1.button("Next bar (5 min)", key="pr_next", width="stretch"):
    if not sess.next_bar():
        st.warning("The market has ended. Press Finish.")
if b2.button("+1 hour", key="pr_next12", width="stretch"):
    sess.advance(12)
if b3.button("To end of day", key="pr_eod", width="stretch"):
    sess.advance_to_day_end()
if b4.button("Finish and review", key="pr_finish", width="stretch"):
    rep = sess.finish()
    st.session_state["practice_report"] = format_practice_report(rep, st.session_state.get("practice_note", ""))
    st.session_state["practice_report_data"] = rep
    st.rerun()

for kind_, message_ in st.session_state.pop("practice_flash", []):
    getattr(st, kind_)(message_)

today_bars = sess.revealed()[sess.revealed().index.date == sess.now.date()]
day_open = float(today_bars["open"].iloc[0])
change = sess.spot - day_open
gate = check_gate(sess.journal, sess.now.date(), sess.s.max_trades_per_day, sess.s.max_daily_loss)
equity_change = sess.equity() - sess.s.capital
ui.ticker([("NIFTY (fake)", f"{sess.spot:,.1f}", ui.tone(change)),
           ("Change today", f"{change:+,.1f} ({change / day_open * 100:+.2f}%)", ui.tone(change)),
           ("Time", f"{sess.now:%d %b %H:%M}", None), ("Days to expiry", f"{sess.dte():.2f}", "warn" if sess.dte() < 1 else None),
           ("Account", ui.inr(sess.equity()), ui.tone(equity_change)), ("Open P&L", ui.inr(sess.unrealized(), sign=True), ui.tone(sess.unrealized())),
           ("Trades today", f"{gate.trades_opened_today}/{sess.s.max_trades_per_day}", "warn" if not gate.allowed else None)])

# ----------------------------------------------------------------------- chart and order ticket
chart_col, ticket_col = st.columns([2.6, 1.1], gap="large")

markers = []
for tr in sess.closed:
    markers.append({"entry_time": tr["entry_ts"], "exit_time": tr["exit_ts"], "side": "LONG" if tr["kind"] == "CE" else "SHORT",
                    "entry_price": tr["entry_spot"], "exit_price": tr["exit_spot"], "net_pnl": tr["net"]})
if sess.position:
    p0 = sess.position
    markers.append({"entry_time": p0["entry_ts"], "exit_time": pd.NaT, "side": "LONG" if p0["kind"] == "CE" else "SHORT",
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
        if st.button("Close position now (sell at the bid)", key="pr_close", width="stretch"):
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
        kind = c1.selectbox("Type", ["CE", "PE"], key="pr_kind", help="CE gains if Nifty rises, PE if it falls")
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
        lots = st.number_input("Lots", min_value=1, value=1, step=1, key="pr_lots")
        override = st.checkbox("Trade anyway if my own rules say no", key="pr_override")
        if st.button("Buy", type="primary", key="pr_buy", width="stretch"):
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
    ui.show_chart(candlestick(sess.revealed(), trades=pd.DataFrame(markers) if markers else None,
                              hlines={"day open": day_open}, height=330, max_bars=int(window)))
    entry_line = sess.position["entry_price"] if sess.position else None
    stop_line = sess.position["stop"] if sess.position else None
    st.caption(f"Option price: {sel_kind} {sel_strike}")
    ui.show_chart(premium_line(sess.premium_history(sel_kind, sel_strike, last=int(window)), entry_line, stop_line))

tab_chain, tab_blotter, tab_rules = st.tabs(["Option chain", "Blotter", "My rules today"])
with tab_chain:
    rows = []
    for k in sess.strikes():
        cb, ca = sess.quote("CE", k)
        pb, pa = sess.quote("PE", k)
        rows.append({"CE bid": cb, "CE ask": ca, "Strike": k, "PE bid": pb, "PE ask": pa})
    chain = pd.DataFrame(rows)
    atm = sess.atm_strike()
    styled = (chain.style.format({c: "{:.2f}" for c in ("CE bid", "CE ask", "PE bid", "PE ask")} | {"Strike": "{:,.0f}"})
              .apply(lambda r: ["background-color: #1F2A37; font-weight: 700" if r["Strike"] == atm else "" for _ in r], axis=1))
    ui.show_table(styled, hide_index=True)
    st.caption("Model prices around the money. The highlighted row is at the money.")
with tab_blotter:
    if not sess.closed:
        st.info("No closed trades yet.")
    else:
        blotter = pd.DataFrame([{"in": f"{t['entry_ts']:%d %b %H:%M}", "out": f"{t['exit_ts']:%d %b %H:%M}", "option": t["label"],
                                 "lots": t["lots"], "buy": t["entry_price"], "sell": t["exit_price"], "exit": t["reason"],
                                 "market move": t["move"], "time decay": t["time"], "spread": t["spread"],
                                 "charges": t["charges"], "net (Rs)": t["net"]} for t in sess.closed])
        styled = style_map(blotter.style.format({c: "{:,.0f}" for c in ("market move", "time decay", "spread", "charges", "net (Rs)")}
                                                | {"buy": "{:.2f}", "sell": "{:.2f}"}),
                           colour_pnl, ["market move", "time decay", "spread", "charges", "net (Rs)"])
        ui.show_table(styled, hide_index=True)
with tab_rules:
    st.write(f"Max loss per trade: **{ui.inr(sess.s.max_loss_per_trade)}**  ·  Max trades per day: **{sess.s.max_trades_per_day}**  ·  "
             f"Max loss per day: **{ui.inr(sess.s.max_daily_loss or 0)}**")
    if gate.allowed:
        st.success("You are within your own rules for today.")
    else:
        st.error("BLOCKED today: " + " ".join(gate.reasons))
ui.footer_note()
