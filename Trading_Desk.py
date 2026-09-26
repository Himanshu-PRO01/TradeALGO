"""Front page of the trading desk. Start it with:  streamlit run Trading_Desk.py"""
import json
import streamlit as st

from algobot import ui
from algobot.appstate import is_hosted, storage_note

ui.setup("Trading Desk", "🏠")
ui.header("Trading Desk", "Research • Test • Validate")

# 1. Market Selector — India only (NSE)
chart_controls = st.columns([2, 2, 3])
with chart_controls[0]:
    dashboard_symbol = st.selectbox(
        "Indian Market",
        ["NSE:NIFTY", "NSE:BANKNIFTY", "NSE:FINNIFTY", "NSE:MIDCPNIFTY",
         "NSE:RELIANCE", "NSE:HDFCBANK", "NSE:ICICIBANK"],
        index=0,
        key="dashboard_chart_symbol",
    )
with chart_controls[1]:
    dashboard_interval = st.selectbox(
        "Timeframe",
        ["1", "5", "15", "30", "60", "D", "W"],
        index=2,
        format_func=lambda x: {
            "1": "1 minute", "5": "5 minutes", "15": "15 minutes",
            "30": "30 minutes", "60": "1 hour", "D": "1 day", "W": "1 week"
        }[x],
        key="dashboard_chart_interval",
    )
with chart_controls[2]:
    dashboard_height = st.slider(
        "Chart height",
        min_value=400,
        max_value=1200,
        value=600,
        step=20,
        key="dashboard_chart_height",
    )

# 2. KPI Cards
ui.ticker([
    ("Market", dashboard_symbol.split(":")[1], None),
    ("Signal", "WAIT", "warn"),
    ("Position", "FLAT", None),
    ("Risk", "STRICT", "up"),
    ("Today P&L", "₹0", None),
    ("Max Drawdown", "0%", None)
])

# 3. Indian Market Chart — Groww
GROWW_NIFTY_URL = "https://groww.in/charts/indices/nifty"

st.markdown("### Indian NIFTY 50 Market View")
st.iframe(GROWW_NIFTY_URL, height=dashboard_height + 15)
st.caption("NIFTY 50 chart from Groww. Research visualization only; no broker connection or live orders.")

# 4. Lower Dashboard Panels
col1, col2 = st.columns(2)
with col1:
    st.markdown("### Strategy State")
    ui.check_row("PASS", "Data Feed", "Connected to research feed")
    ui.check_row("WARN", "Broker Sync", "Broker not connected")
    ui.check_row("TODO", "Execution", "Live trading locked")

with col2:
    st.markdown("### Risk Status")
    ui.check_row("PASS", "Kill Switch", "Armed")
    ui.check_row("PASS", "Max Loss", "Within limits")
    ui.check_row("PASS", "Position Size", "Checked")

st.markdown("---")

# 5. Quick Links / Workflow
st.markdown("### Research Workflow")
a, b, c = st.columns(3)
with a:
    st.markdown(ui.card("Practice", "Trade with fake money to test risk limits and execution rules.", "🎯"), unsafe_allow_html=True)
    st.page_link("pages/3_Practice_room.py", label="Practice Room", icon="🎯")
with b:
    st.markdown(ui.card("Backtest", "Test your strategy against historical data and analyze drawdowns.", "📊"), unsafe_allow_html=True)
    st.page_link("pages/5_Backtest.py", label="Backtest Strategy", icon="📊")
with c:
    st.markdown(ui.card("Auto Tester", "Generate and test variations of strategies automatically.", "🤖"), unsafe_allow_html=True)
    st.page_link("pages/13_Auto_Tester.py", label="Auto Tester", icon="🤖")

st.info(storage_note())
ui.footer_note()
