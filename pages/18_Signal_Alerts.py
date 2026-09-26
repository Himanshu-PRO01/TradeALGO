"""Signal Alerts: the same strategy signal Paper Trading and Sandbox Rehearsal
evaluate, sent to WhatsApp instead of turned into any kind of order. Nothing
on this page can place, modify, or cancel a broker order -- see
algobot/signal_alerts.py and algobot/whatsapp_alerts.py.
"""
import os

import streamlit as st

from algobot import ui
from algobot.appstate import alert_scope, kill_switch_scope
from algobot.config import ConfigError, load_config, validate_config
from algobot.live_data import INTERVALS, MARKETS, LiveDataError, fetch_ohlc
from algobot.paper_trading import evaluate, run_key_for, split_open_and_closed
from algobot.signal_alerts import step
from algobot.whatsapp_alerts import load_recipients

ui.setup("Signal Alerts", "\U0001F4F2")
ui.header(
    "Signal Alerts",
    "Sends a WhatsApp message when your strategy's own BUY/SELL/EXIT signal -- the same one "
    "Paper Trading evaluates -- fires or closes. This page cannot place, modify, or cancel any "
    "order; it only ever sends a text message, and you decide what to do with it.",
    mode="alerts:Signal Alerts",
)

with kill_switch_scope() as switch:
    ks_status = switch.status()
    if ks_status["halted"]:
        st.info(
            f"Note: trading is halted (since {ks_status['since']}, by {ks_status['by']}), but that "
            "only affects order-placement pages -- alerts still fire here since no order is ever placed."
        )

recipients = []
try:
    recipients = load_recipients()
except Exception as exc:
    st.error(f"WHATSAPP_RECIPIENTS is set but could not be read: {exc}")
    st.stop()

if not recipients:
    st.warning(
        "No WhatsApp recipients configured yet. Each phone that should get alerts needs its own "
        "free CallMeBot API key (see algobot/whatsapp_alerts.py for the one-time setup steps), then "
        "add WHATSAPP_RECIPIENTS=+91XXXXXXXXXX:key1,+91YYYYYYYYYY:key2 to a private .env file or "
        "Streamlit secret -- never in code or Git."
    )
    st.stop()
st.caption(f"Alerts will go to {len(recipients)} phone(s): " + ", ".join(r.phone for r in recipients))

raw = st.session_state.get("last_raw")
try:
    if raw is not None:
        base_cfg = validate_config(raw)
        st.info("Using the strategy from your last Backtest.")
    else:
        demo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "demo_rules.yaml")
        base_cfg = load_config(demo)
        st.info("Using the demo strategy. Run a Backtest first to alert on your own strategy.")
except ConfigError as exc:
    st.error(f"The settings are not valid: {exc}")
    st.stop()

c1, c2 = st.columns(2)
symbol_label = c1.selectbox("Signal market (for the strategy's decisions)", list(MARKETS), key="alert_symbol")
interval_label = c2.selectbox("Timeframe", list(INTERVALS), index=1, key="alert_interval")

instrument_label = st.text_input(
    "Instrument name to show in the alert text",
    placeholder="Example: NIFTY 25000 CE 25-Sep",
    key="alert_instrument_label",
    help="Display text only -- this page never looks up or sends a real instrument token.",
)
quantity = int(base_cfg["strategy"]["quantity"])
st.caption(f"Suggested size shown in the alert: {quantity} unit(s) (from the strategy's own config).")

enabled = st.checkbox("Send WhatsApp alerts when a signal fires or closes.", key="alert_enabled")

st.divider()

if not instrument_label.strip():
    st.info("Enter an instrument name above to begin.")
    st.stop()


@st.cache_data(ttl=30, show_spinner=False)
def cached_ohlc(ticker: str, interval: str, period: str):
    return fetch_ohlc(ticker, interval, period)


ticker = MARKETS[symbol_label]
yf_interval, yf_period = INTERVALS[interval_label]
try:
    df = cached_ohlc(ticker, yf_interval, yf_period)
except LiveDataError as exc:
    st.error(str(exc))
    st.stop()

run_key = run_key_for(base_cfg, symbol_label, interval_label) + f"::{instrument_label.strip()}"

with alert_scope() as log:
    if st.button("\U0001F504 Refresh now", key="alert_refresh"):
        cached_ohlc.clear()
        st.rerun()

    if enabled:
        result = evaluate(base_cfg, df)
        open_snapshot, _closed = split_open_and_closed(result)
        messages = step(open_snapshot, run_key, instrument_label.strip(), quantity, log)
        for m in messages:
            (st.success if "FAILED" not in m else st.error)(m)
    else:
        st.warning("Not armed -- tick the checkbox above to let this page send WhatsApp alerts.")

    state = log.get_state(run_key)
    st.subheader("Current state")
    if state["status"] == "open":
        st.markdown(ui.card(f"Signal open: {state['side']}",
                             f"Fired at {state['entry_time']}.", "\U0001F7E2"),
                    unsafe_allow_html=True)
    else:
        st.markdown(ui.card("Flat", "No open signal currently tracked for this instrument.", "\u26AA"),
                    unsafe_allow_html=True)

    st.subheader("Alert history for this instrument")
    hist = log.history(run_key)
    if not hist.empty:
        ui.show_table(hist)
    else:
        st.caption("No alerts sent yet through this page for this instrument.")

    with st.expander("Reset local tracking for this instrument"):
        st.caption("Clears what this page remembers about this instrument only. It does not un-send "
                   "any WhatsApp message already delivered.")
        confirm = st.checkbox("I understand this only resets local tracking.", key="alert_reset_confirm")
        if st.button("Reset tracking", disabled=not confirm, key="alert_reset_btn"):
            log.reset(run_key)
            st.rerun()

ui.footer_note("No order-placement code is reachable from this page -- alerts only.")
