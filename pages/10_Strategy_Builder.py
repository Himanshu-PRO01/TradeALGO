"""Deterministic strategy builder: write rules down before testing them."""

import json

import streamlit as st

from algobot import ui

ui.setup("Strategy Builder", "🧠")
ui.header(
    "Strategy Builder",
    "Turn a trading idea into explicit rules that can be backtested. This page does not place orders.",
    mode="research:Strategy",
)

st.info("Build the rule first. The next step is to test it on historical data before considering any live use.")

with st.form("strategy_builder"):
    name = st.text_input("Strategy name", placeholder="Example: Previous-week level reversal")
    timeframe = st.selectbox("Timeframe", ["5m", "15m", "30m", "1h", "Daily"], index=1)
    market = st.selectbox("Market", ["NIFTY", "BANKNIFTY", "Other"])
    side = st.selectbox("Direction", ["Long only", "Short only", "Long and short"])
    level = st.text_area(
        "Entry level rule",
        placeholder="Example: price touches previous week's high or low.",
        height=90,
    )
    confirmation = st.text_area(
        "Confirmation rule",
        placeholder="Example: 15-minute candle closes back inside the level AND volume is above its 20-bar average.",
        height=100,
    )
    stop = st.text_input("Stop-loss rule", placeholder="Example: 30 Nifty points beyond the level.")
    target = st.text_input(
        "Take-profit rule",
        placeholder="Use a precise rule, not 'I decide as it happens'. Example: 1.5R or opposite level.",
    )
    skip = st.text_area(
        "Skip-trade rule",
        placeholder="Example: skip during scheduled major news and outside 09:30–11:00 / 13:00–15:15.",
        height=80,
    )
    sizing = st.text_input("Position-sizing rule", placeholder="Example: 1 lot while testing.")
    notes = st.text_area("Notes / unresolved questions", height=80)
    submitted = st.form_submit_button("Save rule set")

if submitted:
    if not name.strip() or not level.strip() or not confirmation.strip() or not stop.strip() or not target.strip():
        st.error("Name, entry level, confirmation, stop-loss and take-profit are required.")
    else:
        rules = {
            "name": name.strip(),
            "market": market,
            "timeframe": timeframe,
            "direction": side,
            "entry_level": level.strip(),
            "confirmation": confirmation.strip(),
            "stop_loss": stop.strip(),
            "take_profit": target.strip(),
            "skip_trade": skip.strip(),
            "position_sizing": sizing.strip(),
            "notes": notes.strip(),
        }
        st.session_state["strategy_rules"] = rules
        st.success("Rule set captured. Review it below before using it in a backtest.")

rules = st.session_state.get("strategy_rules")
if rules:
    st.divider()
    st.markdown("### Current rule set")
    st.json(rules)
    st.download_button(
        "Download strategy JSON",
        json.dumps(rules, indent=2),
        file_name="strategy_rules.json",
        mime="application/json",
    )
    st.page_link("pages/5_Backtest.py", label="Next: Backtest this strategy", icon="📊")

st.divider()
ui.check_row("PASS", "No broker connection", "The builder only records deterministic rules.")
ui.check_row("PASS", "No live orders", "Saving or downloading a strategy cannot place an order.")
ui.check_row("WARN", "Discretionary exits are not testable as written", "Convert 'I decide as it happens' into a measurable rule.")
ui.footer_note()
