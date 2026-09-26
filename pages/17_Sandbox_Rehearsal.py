"""Sandbox Rehearsal: the same strategy signal Paper Trading evaluates, now actually placed
as Upstox Sandbox orders. Still zero real money -- Upstox's sandbox fakes the fill -- but this
is the real order-placement code path being exercised end to end, not just a log entry.
"""
import os

import streamlit as st

from algobot import ui
from algobot.appstate import kill_switch_scope, rehearsal_scope
from algobot.config import ConfigError, load_config, validate_config
from algobot.live_data import INTERVALS, MARKETS, LiveDataError, fetch_ohlc
from algobot.paper_trading import evaluate, run_key_for, split_open_and_closed
from algobot.sandbox_rehearsal import step
from algobot.upstox_sandbox import UpstoxSandboxClient, clean_token, sandbox_token, token_preview

ui.setup("Sandbox Rehearsal", "🎬")
ui.header(
    "Sandbox Rehearsal",
    "Connects your strategy's own BUY/SELL/EXIT signal -- the same one Paper Trading evaluates -- "
    "to real Upstox Sandbox orders for one instrument you choose. This exercises the actual order "
    "code (place, and later exit) against Upstox's sandbox, which fakes the fill but is otherwise "
    "the real API. No live endpoint, no live token, and no real money is ever reachable from here.",
    mode="execution:Sandbox Rehearsal",
)

token = sandbox_token()
if not token:
    try:
        token = clean_token(st.secrets.get("UPSTOX_SANDBOX_ACCESS_TOKEN"))
    except Exception:
        token = None

# ── Sidebar: allow pasting the token manually ────────────────────────────────
with st.sidebar:
    st.markdown("### 🔐 Upstox Sandbox token")
    manual_token = clean_token(
        st.text_input(
            "Paste token here",
            value="",
            type="password",
            placeholder="eyJ0eXAiOiJKV1Qi...",
            help="Get this from https://sandbox.upstox.com → My Apps → Access Token",
            key="reh_token_input",
        )
    )
    if manual_token:
        token = manual_token
    if token:
        st.caption(f"✅ Token loaded: `{token_preview(token)}`")
    else:
        st.caption("⚠️ No token — paste it above.")
    from algobot.dom_fixups import fix_password_autocomplete
    fix_password_autocomplete()


with kill_switch_scope() as switch:
    ks_status = switch.status()
    if ks_status["halted"]:
        st.error(f"🛑 Trading halted since {ks_status['since']} by {ks_status['by']}. "
                 f"Reason: {ks_status['reason'] or '(none given)'} -- no sandbox orders will be placed. "
                 "Resume it from the Paper Trading page when ready.")
    else:
        st.success("🟢 Kill switch is clear.")

if not token:
    st.warning("No sandbox token detected. Set it up on the Upstox Sandbox page first.")
    st.stop()
st.caption(f"Sandbox token: `{token_preview(token)}`")

raw = st.session_state.get("last_raw")
try:
    if raw is not None:
        base_cfg = validate_config(raw)
        st.info("Using the strategy from your last Backtest.")
    else:
        demo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "demo_rules.yaml")
        base_cfg = load_config(demo)
        st.info("Using the demo strategy. Run a Backtest first to rehearse your own strategy.")
except ConfigError as exc:
    st.error(f"The settings are not valid: {exc}")
    st.stop()

c1, c2 = st.columns(2)
symbol_label = c1.selectbox("Signal market (for the strategy's decisions)", list(MARKETS), key="reh_symbol")
interval_label = c2.selectbox("Timeframe", list(INTERVALS), index=1, key="reh_interval")

st.markdown("### Instrument to actually order in the sandbox")
st.caption(
    "The market above only drives the strategy's timing signal (its price data has no relationship "
    "to any tradeable Upstox contract). The instrument below is what actually gets bought/sold in "
    "the sandbox when a signal fires -- use the exact instrument_token Upstox gives you for the "
    "contract you're rehearsing (see the Upstox Sandbox page for how to find one)."
)
instrument_token = st.text_input("Instrument token", placeholder="Example: NSE_FO|...", key="reh_instrument")
quantity = int(base_cfg["strategy"]["quantity"])
st.caption(f"Quantity per order: {quantity} (from the strategy's own config).")

enabled = st.checkbox(
    "I understand this will automatically place real Upstox Sandbox orders when a signal fires.",
    key="reh_enabled",
)

st.divider()

if not instrument_token.strip():
    st.info("Enter an instrument token above to begin.")
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

run_key = run_key_for(base_cfg, symbol_label, interval_label) + f"::{instrument_token.strip()}"

with rehearsal_scope() as log:
    if st.button("🔄 Refresh now", key="reh_refresh"):
        cached_ohlc.clear()
        st.rerun()

    if enabled and not ks_status["halted"]:
        result = evaluate(base_cfg, df)
        open_snapshot, _closed = split_open_and_closed(result)
        client = UpstoxSandboxClient(token=token)
        messages = step(open_snapshot, run_key, client, instrument_token.strip(), quantity, log)
        for m in messages:
            (st.success if "FAILED" not in m else st.error)(m)
    elif not enabled:
        st.warning("Not armed -- tick the checkbox above to let this page place sandbox orders.")

    # Read state AFTER step() above, which may have just flipped flat -> open (or
    # vice versa) on this very rerun -- reading it before step() showed the stale
    # pre-order status even on the run where an order was just placed.
    state = log.get_state(run_key)
    st.subheader("Current state")
    if state["status"] == "open":
        st.markdown(ui.card(f"Sandbox position open: {state['side']}",
                             f"Entered at {state['entry_time']} · sandbox order {state['order_id']}.", "🟢"),
                    unsafe_allow_html=True)
    else:
        st.markdown(ui.card("Flat", "No sandbox position currently tracked for this instrument.", "⚪"),
                    unsafe_allow_html=True)

    st.subheader("Order history for this instrument")
    hist = log.history(run_key)
    if not hist.empty:
        ui.show_table(hist)
    else:
        st.caption("No sandbox orders placed yet through this page for this instrument.")

    with st.expander("Reset local tracking for this instrument"):
        st.caption(
            "Clears what this page remembers about this instrument only. It does NOT cancel any "
            "order already sitting in Upstox Sandbox -- do that from the Upstox Sandbox page if "
            "one is still open there."
        )
        confirm = st.checkbox("I understand this only resets local tracking.", key="reh_reset_confirm")
        if st.button("Reset tracking", disabled=not confirm, key="reh_reset_btn"):
            log.reset(run_key)
            st.rerun()

ui.footer_note("Sandbox only. No live endpoint or live token is reachable from this page.")
