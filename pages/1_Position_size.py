"""How many option lots fit the maximum loss for one trade? Nothing is sent to any broker."""
import datetime as dt

import streamlit as st

from algobot import ui
from algobot.appstate import journal_scope
from algobot.gate import check_gate
from algobot.sizing import NIFTY_LOT_SIZE, format_size, option_position_size

ui.setup("Position size", "🧮")
ui.header("Position size", "Before you click buy: how many lots fit your loss limit on this trade, and are today's "
          "limits still open? It only calculates. Nothing is sent to any broker.", mode="journal:Before you trade")

plan, result_col = st.columns([1, 1.25], gap="large")
with plan:
    st.markdown("#### Trade plan")
    entry = st.number_input("Option price you plan to buy at", min_value=0.05, value=100.0, step=0.5, key="ps_entry")
    stop = st.number_input("Price where you exit if you are wrong (stop-loss)", min_value=0.0, value=85.0, step=0.5, key="ps_stop")
    max_loss = st.number_input("Most you accept losing on this trade (Rs)", min_value=1, value=1000, step=100, key="ps_max_loss")
    capital = st.number_input("Account size (Rs)", min_value=1, value=10000, step=1000, key="ps_capital")
    with st.expander("Lot size, charges and today's limits"):
        lot_size = st.number_input(f"Lot size (Nifty 50 default is {NIFTY_LOT_SIZE}; confirm on NSE or your broker)",
                                   min_value=1, value=NIFTY_LOT_SIZE, step=1, key="ps_lot")
        charges = st.number_input("Estimated charges for the round trip (Rs, from your broker's calculator)",
                                  min_value=0.0, value=0.0, step=10.0, key="ps_charges")
        g1, g2 = st.columns(2)
        max_trades = g1.number_input("Max trades per day (0 = no limit)", min_value=0, value=2, step=1, key="ps_max_trades")
        max_daily = g2.number_input("Max loss per day (Rs, 0 = no limit)", min_value=0, value=1500, step=100, key="ps_max_daily")

with result_col:
    st.markdown("#### What fits")
    try:
        result = option_position_size(max_loss=float(max_loss), entry_premium=float(entry), stop_premium=float(stop),
                                      lot_size=int(lot_size), capital=float(capital), est_charges=float(charges))
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    ui.ticker([
        ("Lots allowed", result.lots, None),
        ("You pay (Rs)", f"{result.premium_outlay:,.0f}", None),
        ("Loss at stop (Rs)", f"{result.loss_if_stopped:,.0f}", None)
    ])
    for w in result.warnings:
        st.warning(w)

    st.markdown("#### Today's limits (from your journal)")
    with journal_scope() as journal:
        gate = check_gate(journal, dt.date.today(), int(max_trades) or None, float(max_daily) or None)
    ui.ticker([("Trades opened today", gate.trades_opened_today, None),
               ("Net today", ui.inr(gate.net_pnl_today, sign=True), ui.tone(gate.net_pnl_today)),
               ("Open positions", gate.open_positions, None)])
    if gate.allowed and result.lots > 0:
        st.success("OK by your own rules. You decide, and you place the order yourself.")
    elif not gate.allowed:
        st.error("BLOCKED: " + " ".join(gate.reasons))
    else:
        st.error("BLOCKED: this trade does not fit your rules at this stop.")

with st.expander("Plain-text version (to copy)"):
    st.code(format_size(result, int(lot_size)), language="text")
ui.footer_note()
