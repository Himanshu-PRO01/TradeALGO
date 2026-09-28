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

if st.button("Load supplied New Era Strategy 1.0 profile", key="load_new_era_profile"):
    st.session_state["strategy_rules"] = {
        "name": "New Era Strategy 1.0",
        "market": "NIFTY",
        "timeframe": "15m",
        "direction": "Long and short",
        "entry_level": "PE: formation state from EMA Smooth 9 < EMA 33 < HMA 27 < HMA 22 < HMA 18, RSI(5) > 65 and RSI SMA(5) > 60, CCI(14) > 100 and CCI SMA(5) > 80; then signal when close < captured low. CE: reverse indicator ordering, RSI(5) < 25 and RSI SMA(5) < 30, CCI(14) < -50 and CCI SMA(5) < -20; then signal when close > captured high.",
        "confirmation": "The supplied Pine Script uses a stateful formation candle range. It updates the captured high/low while the formation remains active, then requires the breakout candle to close beyond the captured boundary.",
        "stop_loss": "PE: min(previous-bar high, signal-bar high). CE: min(previous-bar low, signal-bar low). Optional SL Max Points % is 0 by default (disabled).",
        "take_profit": "Target ratio 2R by default, calculated from the signal-bar close and the signal-bar-derived stop distance.",
        "skip_trade": "Only formation/signal processing from 09:15 to before 15:00. The supplied script also squares off at the day-close window.",
        "position_sizing": "Pine strategy qty = 1.",
        "notes": "Source: brother-supplied TradingView Pine Script 'New Era Strategy 1.0'. This profile records the source rules; it does not silently alter them. The deterministic backtester has a dedicated new_era_1_0 implementation."
    }
    st.success("New Era Strategy 1.0 profile loaded. Review the captured rules before backtesting.")

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
ui.workflow_nav("strategy", complete=st.session_state.get("strategy_rules") is not None)
ui.footer_note()
