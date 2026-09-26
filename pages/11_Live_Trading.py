"""Explicit live-execution control page.

Live orders are never automatic from this page: the operator must enable LIVE
mode outside the app and confirm each order. Strategy automation remains a
separate reviewed change.
"""
import os

import streamlit as st

from algobot import ui
from algobot.execution_policy import ExecutionMode, get_execution_mode, live_trading_allowed
from algobot.kill_switch import KillSwitch
from algobot.openalgo_bridge import OpenAlgoClient, OpenAlgoError

ui.setup("Live Trading", "🔴")
ui.header(
    "Live Trading",
    "Live execution is available only after an explicit environment-level approval and kill-switch check.",
    mode="execution:Live",
)

mode = get_execution_mode()
allowed = live_trading_allowed()
st.info(f"Execution mode: **{mode.value}**")

if not allowed:
    ui.banner("LIVE EXECUTION BLOCKED", tone="error", icon="🔒")
    st.caption(
        "Set TRADEALGO_EXECUTION_MODE=LIVE only when you deliberately want real-money execution. "
        "The default remains LIVE_DISABLED."
    )
else:
    ui.banner("LIVE EXECUTION ENABLED", tone="error", icon="⚠️")
    st.warning(
        "Orders submitted here can reach the connected broker through OpenAlgo and can lose real money. "
        "Use only a verified symbol, quantity, product and order type."
    )

st.markdown("### Pre-flight")
for status, title, detail in [
    ("PASS" if mode is ExecutionMode.LIVE else "BLOCKED", "Execution mode", "LIVE must be explicitly selected outside the UI."),
    ("PASS" if allowed else "BLOCKED", "Kill switch", "A halted kill switch blocks live orders."),
    ("PASS", "Credentials", "The OpenAlgo API key is read privately from the environment."),
    ("PASS", "Strategy automation", "This page requires a human confirmation for each submitted order."),
]:
    ui.check_row(status, title, detail)

if allowed:
    st.divider()
    st.markdown("### Place one live order")
    st.caption("This is a real-money action. Review every field before confirming.")
    c1, c2 = st.columns(2)
    strategy = c1.text_input("Strategy name", "TradeALGO")
    symbol = c1.text_input("Symbol", "NIFTY")
    exchange = c1.selectbox("Exchange", ["NSE", "NFO", "BSE", "MCX", "NSE_INDEX"])
    action = c2.selectbox("Action", ["BUY", "SELL"])
    price_type = c2.selectbox("Order type", ["MARKET", "LIMIT", "SL", "SL-M"])
    product = c2.selectbox("Product", ["MIS", "NRML", "CNC"])
    quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
    p1, p2 = st.columns(2)
    price = p1.number_input("Price (LIMIT/SL)", min_value=0.0, value=0.0, step=0.05)
    trigger = p2.number_input("Trigger price (SL/SL-M)", min_value=0.0, value=0.0, step=0.05)
    confirm = st.checkbox(
        "I understand this can place a real-money order and I have checked the symbol, side, quantity and prices.",
        key="live_order_confirm",
    )
    if st.button("PLACE LIVE ORDER", type="primary", disabled=not confirm):
        try:
            client = OpenAlgoClient()
            response = client.place_order(
                strategy=strategy, symbol=symbol, exchange=exchange, action=action,
                price_type=price_type, product=product, quantity=int(quantity),
                price=float(price), trigger_price=float(trigger),
            )
            st.success(f"OpenAlgo accepted the order. Order ID: {response.get('orderid', 'not returned')}")
        except OpenAlgoError as exc:
            st.error(str(exc))
        except RuntimeError as exc:
            st.error(str(exc))

st.divider()
st.markdown("### Kill switch")
kill_path = os.environ.get("TRADEALGO_KILL_SWITCH_DB", os.path.join("data", "kill_switch.sqlite"))
switch = KillSwitch(kill_path)
try:
    status = switch.status()
    if status["halted"]:
        st.error(f"HALTED since {status['since']}: {status['reason']}")
        if st.button("Resume live execution"):
            switch.resume(by="streamlit")
            st.rerun()
    else:
        st.success("Kill switch is clear.")
        reason = st.text_input("Reason for emergency halt", "Manual emergency stop")
        if st.button("HALT LIVE EXECUTION"):
            switch.halt(reason, by="streamlit")
            st.rerun()
finally:
    switch.close_db()

ui.footer_note()
