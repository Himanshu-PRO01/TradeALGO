"""Live Markets: real-time Nifty charts plus isolated fake-money trading."""

import copy
import os

import streamlit as st

from algobot import ui
from algobot.ai_strategy_agent import StrategyAgent
from algobot.charts import candlestick
from algobot.config import ConfigError, load_config, validate_config
from algobot.live_market import INSTRUMENTS, get_market_hub, market_data_token
from algobot.paper_trading import evaluate, log_new_trades, run_key_for, split_open_and_closed


ui.setup("Live Markets", "📈")
ui.header(
    "Live Markets",
    "Real-time Nifty market data with a separate fake-money paper account. AI analyzes the feed; it never invents prices or executes trades.",
    mode="execution:Paper",
)

st.info(
    "🟢 MARKET DATA ONLY · The chart comes from Upstox Market Data Feed V3. "
    "The AI receives the observed snapshot and explains it; it is not the market-data source and cannot place orders."
)

token = market_data_token()
if not token:
    st.warning(
        "Live feed is not configured. Add UPSTOX_ANALYTICS_TOKEN to Streamlit Secrets "
        "(preferred for read-only market data) or UPSTOX_ACCESS_TOKEN. No token value belongs in GitHub."
    )
    st.markdown(
        "For a dashboard-only deployment, Upstox's Analytics Token is read-only, valid for one year, "
        "and officially supports WebSocket market data."
    )
    st.stop()

market_label = st.selectbox("Market", list(INSTRUMENTS), index=0, key="live_market_symbol")
instrument_key = INSTRUMENTS[market_label]
window = st.slider("Candles on chart", 60, 600, 240, step=30, key="live_window")

hub = get_market_hub(token)
hub.start([instrument_key])

status_box = st.empty()


@st.fragment(run_every="2s")
def live_panel():
    status = hub.status()
    latest = hub.latest(instrument_key)
    bars = hub.snapshot(instrument_key, max_bars=window)

    if status["connected"]:
        status_box.success(
            f"🟢 Live feed connected · {len(bars)} one-minute candles · "
            f"{status['ticks']:,} ticks cached in this server process"
        )
    elif status["last_error"]:
        status_box.error(f"🔴 Live feed error: {status['last_error']}")
    else:
        status_box.info("🟡 Connecting to Upstox Market Data Feed V3…")

    if latest:
        ui.ticker([
            ("Selected LTP", f"₹{latest['price']:,.2f}", None),
            ("Last tick", latest["datetime"].strftime("%H:%M:%S"), None),
            ("Ticks cached", f"{status['ticks']:,}", None),
            ("Mode", "LIVE", "up"),
        ])

    if bars.empty:
        st.info("Waiting for the first live ticks. The chart will populate automatically.")
        return

    ui.show_chart(candlestick(bars, height=430, max_bars=window, volume=True))
    st.caption(
        "Prices and candles above are observed market data. They are not AI-generated. "
        "Paper trades below are virtual and do not place broker orders."
    )


live_panel()

st.divider()
st.subheader("Fake trading account")
st.caption(
    "Each browser session gets its own virtual ledger. Multiple users can use the same live feed concurrently "
    "without sharing paper positions or P&L. The market stream itself is shared once per server process."
)

raw = st.session_state.get("last_raw")
try:
    if raw is not None:
        base_cfg = validate_config(raw)
        st.caption("Using the strategy from your last Backtest.")
    else:
        demo = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "configs",
            "demo_rules.yaml",
        )
        base_cfg = load_config(demo)
        st.caption("Using the demo strategy. Run Backtest/Strategy Builder to use your own rules.")
except ConfigError as exc:
    st.error(f"Could not load the paper strategy: {exc}")
    st.stop()

c1, c2, c3 = st.columns(3)
virtual_capital = c1.number_input("Virtual capital (₹)", min_value=10000, value=500000, step=10000, key="live_virtual_capital")
virtual_qty = c2.number_input("Virtual quantity", min_value=1, value=1, step=1, key="live_virtual_qty")
paper_enabled = c3.toggle("Run fake trading", value=False, key="live_paper_enabled")

paper_cfg = copy.deepcopy(base_cfg)
paper_cfg["capital"] = float(virtual_capital)
paper_cfg["strategy"]["quantity"] = int(virtual_qty)
paper_cfg["risk"]["max_position_value"] = None
paper_cfg["name"] = f"live_paper::{market_label}::{virtual_qty}"

run_key = run_key_for(paper_cfg, market_label, "1 minute live")

if paper_enabled:
    bars = hub.snapshot(instrument_key, max_bars=max(window, 400))
    if len(bars) < 3:
        st.info("Waiting for enough live candles before evaluating the strategy.")
    else:
        result = evaluate(paper_cfg, bars)
        open_snapshot, closed = split_open_and_closed(result)
        from algobot.appstate import paper_scope
        with paper_scope() as log:
            added = log_new_trades(log, run_key, market_label, closed)
            summary = log.summary(run_key)
            ledger = log.virtual_ledger(run_key, paper_cfg["capital"], open_snapshot)

        if added:
            st.success(f"{added} newly completed virtual trade(s) recorded.")

        ui.ticker([
            ("Virtual equity", ui.inr(ledger["virtual_equity"], sign=True), ui.tone(ledger["virtual_equity"] - ledger["starting_capital"])),
            ("Realized P&L", ui.inr(ledger["realized_pnl"], sign=True), ui.tone(ledger["realized_pnl"])),
            ("Unrealized P&L", ui.inr(ledger["unrealized_pnl"], sign=True), ui.tone(ledger["unrealized_pnl"])),
            ("Trades", summary["trades"], None),
        ])

        if open_snapshot:
            st.info(
                f"Open virtual {open_snapshot['side']} position · entry ₹{open_snapshot['entry_price']:,.2f} "
                f"· marked at latest candle ₹{open_snapshot['exit_price']:,.2f}. "
                "This is a simulation snapshot, not an executed order."
            )
        else:
            st.caption("Strategy is currently flat on the observed live candle history.")

        st.session_state["live_market_snapshot"] = {
            "market": market_label,
            "instrument_key": instrument_key,
            "latest_price": float(bars["close"].iloc[-1]),
            "latest_time": str(bars.index[-1]),
            "open": float(bars["open"].iloc[-1]),
            "high": float(bars["high"].iloc[-1]),
            "low": float(bars["low"].iloc[-1]),
            "close": float(bars["close"].iloc[-1]),
            "virtual_equity": float(ledger["virtual_equity"]),
            "realized_pnl": float(ledger["realized_pnl"]),
            "unrealized_pnl": float(ledger["unrealized_pnl"]),
            "paper_trades": int(summary["trades"]),
            "strategy_state": open_snapshot["side"] if open_snapshot else "FLAT",
        }

st.divider()
st.subheader("AI market analysis")
st.caption(
    "AI analysis is on-demand rather than on every tick, so a slow model/API call cannot block the live chart. "
    "The supplied numbers are validated against the observed feed before the response is shown."
)

snapshot = st.session_state.get("live_market_snapshot")
if snapshot is None:
    st.caption("Start fake trading or wait for the live chart to populate a market snapshot.")
else:
    if st.button("🤖 Analyze current live market", key="live_ai_analyze"):
        agent = StrategyAgent()
        if not agent.available:
            st.warning("AI provider is not configured.")
        else:
            with st.spinner("AI is analyzing the observed market snapshot…"):
                response = agent.analyze_live_market(snapshot)
            if response.ok:
                st.session_state["live_ai_analysis"] = response.data
            else:
                st.warning(response.message)

analysis = st.session_state.get("live_ai_analysis")
if analysis:
    st.markdown("**AI observation**")
    st.write(analysis.get("summary", ""))
    if analysis.get("observations"):
        st.markdown("**Observed facts**")
        for item in analysis["observations"]:
            st.write(f"• {item}")
    st.markdown(f"**Strategy state:** {analysis.get('strategy_state', 'Unknown')}")
    if analysis.get("watch_items"):
        st.markdown("**Watch items**")
        for item in analysis["watch_items"]:
            st.write(f"• {item}")
    if analysis.get("data_limits"):
        st.caption("Data limits: " + " · ".join(str(x) for x in analysis["data_limits"]))

st.divider()
ui.check_row("PASS", "Real-time source", "Upstox Market Data Feed V3 is the price source; the AI is never used to fabricate market data.")
ui.check_row("PASS", "Concurrent paper accounts", "The market stream is shared per server process while each browser session keeps its own virtual paper ledger.")
ui.check_row("PASS", "No broker execution", "This page only evaluates the deterministic strategy and records virtual trades. It has no order-placement path.")
ui.check_row("PASS", "AI guardrails", "Live-market AI receives the observed snapshot, must cite supplied values, and rejects certainty claims.")
ui.footer_note("Live market data + fake-money paper trading only. No live orders.")
