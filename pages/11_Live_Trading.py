"""Live trading control page. Execution stays disabled until the system is explicitly approved and wired."""

import streamlit as st

from algobot import ui
from algobot.execution_policy import require_live_disabled

require_live_disabled()

ui.setup("Live Trading", "🔴")
ui.header(
    "Live Trading",
    "A clear control surface for the future live phase. Real order execution is intentionally locked in this build.",
    mode="execution:Live",
)

ui.banner("SYSTEM HARD-LOCKED • NO LIVE TRADING", tone="error", icon="🔒")
st.markdown(
    """
    <div style='text-align: center; padding: 30px; background: repeating-linear-gradient(
        45deg,
        rgba(255,0,0,0.1),
        rgba(255,0,0,0.1) 10px,
        rgba(0,0,0,0.2) 10px,
        rgba(0,0,0,0.2) 20px
    ); border: 2px solid #ff4b4b; border-radius: 8px; margin-bottom: 20px;'>
        <h2 style='color: #ff4b4b; margin: 0;'>VAULT SECURED</h2>
        <p style='margin-top: 10px;'>The system has not authorized real-money execution. This page can prepare and verify the live-trading checklist, but it cannot place, modify, or cancel a broker order.</p>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("### Live-trading checklist")
checks = [
    ("Strategy has explicit entry, stop and exit rules", "Convert every discretionary decision into a measurable rule."),
    ("Historical backtest completed", "Test the exact rules on real historical Nifty data."),
    ("Paper trading completed", "Run the same strategy without real money and review the journal."),
    ("Risk limits verified", "Keep the existing risk and audit controls unchanged."),
    ("Broker connection separately approved", "Broker/API setup requires a deliberate approval step."),
    ("Kill switch tested", "A daily-loss halt must stop new entries."),
]
for title, detail in checks:
    ui.check_row("TODO", title, detail)

st.divider()
st.markdown("### Controls")
st.toggle("Enable live trading", value=False, disabled=True, help="Locked: this build has no live order function.")
st.button("Start live engine", disabled=True)
st.caption(
    "The live controls are intentionally disabled. Enabling them later should be a separate, reviewed change "
    "that uses the existing risk/audit layer and never exposes API keys in the app."
)

st.divider()
ui.check_row("PASS", "Existing OpenAlgo bridge remains read/notification only", "No order-placement function is enabled here.")
ui.check_row("PASS", "No credentials requested", "Keep broker/API secrets outside code and UI.")
ui.footer_note()
