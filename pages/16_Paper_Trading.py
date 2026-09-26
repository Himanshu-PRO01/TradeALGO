"""Paper Trading: run your saved strategy against real (delayed) prices and
log what it would have done. This is the step between Backtest and ever
touching real money -- it never places an order or connects to a broker.
"""
import os

import streamlit as st

from algobot import ui
from algobot.appstate import kill_switch_scope, paper_scope
from algobot.config import ConfigError, load_config, validate_config
from algobot.live_data import INTERVALS, MARKETS, LiveDataError, fetch_ohlc
from algobot.paper_trading import evaluate, log_new_trades, run_key_for, split_open_and_closed

ui.setup("Paper Trading", "📝")
ui.header(
    "Paper Trading",
    "Runs your saved strategy against real market prices and writes down what it would have done, "
    "with no money and no broker involved. This is the honest middle step before Live Trading: a "
    "backtest can look great on data it already knows; this checks the same rules against prices "
    "as they actually arrive.",
    mode="execution:Paper Trading",
)

with kill_switch_scope() as switch:
    ks_status = switch.status()

    st.subheader("Kill switch")
    st.caption(
        "This is the same shared switch that will gate Live Trading once your brother turns that on. "
        "Proving it stops NEW paper entries correctly here, before it is ever load-bearing for real money."
    )
    if ks_status["halted"]:
        st.error(f"🛑 Trading halted since {ks_status['since']} by {ks_status['by']}. Reason: {ks_status['reason'] or '(none given)'}")
        if st.button("▶️ Resume trading", key="ks_resume"):
            switch.resume(by="manual")
            st.rerun()
    else:
        st.success("🟢 Not halted -- new paper entries are being evaluated normally.")
        with st.form("ks_halt_form"):
            reason = st.text_input("Reason (shown in the log)", key="ks_halt_reason")
            halt_now = st.form_submit_button("🛑 Halt everything now")
        if halt_now:
            switch.halt(reason or "no reason given", by="manual")
            st.rerun()
    with st.expander("Kill switch history"):
        hist = switch.history()
        if not hist.empty:
            ui.show_table(hist)
        else:
            st.caption("No halts or resumes recorded yet.")

raw = st.session_state.get("last_raw")
try:
    if raw is not None:
        base_cfg = validate_config(raw)
        st.info("Using the strategy from your last Backtest.")
    else:
        demo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "demo_rules.yaml")
        base_cfg = load_config(demo)
        st.info("Using the demo strategy. Run a Backtest first to paper-trade your own strategy.")
except ConfigError as exc:
    st.error(f"The settings are not valid: {exc}")
    st.stop()

c1, c2 = st.columns(2)
symbol_label = c1.selectbox("Market", list(MARKETS), key="paper_symbol")
interval_label = c2.selectbox("Timeframe", list(INTERVALS), index=1, key="paper_interval")

st.caption(
    "Free Yahoo Finance data, typically 15-20 minutes delayed, with a limited look-back window "
    "(a few days for 5-minute bars). Trades that finish inside that window are saved permanently "
    "below, so history builds up over time even though the feed's own memory is short. If you never "
    "check in during a stretch longer than the window, whatever happened in that gap is missed -- "
    "that is a limit of the free feed, not of the log."
)


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

run_key = run_key_for(base_cfg, symbol_label, interval_label)

if ks_status["halted"]:
    # The kill switch actually blocks here: no new evaluation, no new trades logged --
    # the same behaviour real order placement will follow once this gates live money.
    open_snapshot, closed = None, None
    st.warning("New evaluation is paused while the kill switch is on. Showing history saved before the halt.")
else:
    result = evaluate(base_cfg, df)
    open_snapshot, closed = split_open_and_closed(result)

with paper_scope() as log:
    added = log_new_trades(log, run_key, symbol_label, closed) if closed is not None else 0
    summary = log.summary(run_key)
    history = log.all_trades(run_key)

    if st.button("🔄 Refresh now", key="paper_refresh"):
        cached_ohlc.clear()
        st.rerun()

    if added:
        st.success(f"{added} newly finished paper trade(s) saved.")

    st.subheader("Right now")
    if ks_status["halted"]:
        st.markdown(ui.card("Status frozen by kill switch", "No new checks are running, so this may be stale. Resume to get a current read.", "⏸️"), unsafe_allow_html=True)
    elif open_snapshot:
        side = open_snapshot["side"]
        st.markdown(
            ui.card(
                f"Open paper position: {side}",
                f"Entered at {open_snapshot['entry_price']:.2f} on {open_snapshot['entry_time']}. "
                f"Marked at {open_snapshot['exit_price']:.2f} as of the latest bar -- not a real exit yet.",
                "🟢" if side == "LONG" else "🔴",
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(ui.card("No open paper position", "The strategy is flat right now.", "⚪"), unsafe_allow_html=True)

    st.subheader("Track record so far")
    ui.ticker([
        ("Paper trades logged", summary["trades"], None),
        ("Net (paper) Rs", ui.inr(summary["net"], sign=True) if summary["trades"] else "--", ui.tone(summary["net"]) if summary["trades"] else None),
        ("Win rate", f"{summary['win_rate_pct']:.0f}%" if summary["win_rate_pct"] is not None else "--", None),
        ("Best / worst Rs", f"{summary['best']:,.0f} / {summary['worst']:,.0f}" if summary["trades"] else "--", None),
    ])

    if not history.empty:
        ui.show_table(history.sort_values("exit_time", ascending=False))
    else:
        st.caption("No finished paper trades logged yet for this market, timeframe and strategy.")

    with st.expander("Reset this paper log"):
        st.caption("Clears logged paper trades for this exact strategy + market + timeframe combination only.")
        confirm = st.checkbox("I understand this deletes that history and cannot be undone.", key="paper_reset_confirm")
        if st.button("Delete this paper log", disabled=not confirm, key="paper_reset_btn"):
            log.reset(run_key)
            st.rerun()

st.info(
    "This page never places, modifies, or cancels a broker order -- it only replays your strategy's "
    "own rules against real prices and writes the result down. Real execution stays where it is: "
    "locked in Live Trading."
)
ui.footer_note("Paper trading uses delayed, free market data. It never places an order or connects to a broker.")
