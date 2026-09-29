"""TradeALGO Market Desk: live Upstox V3 market data."""
import streamlit as st

from algobot import charts, ui
from algobot.appstate import storage_note
from algobot.live_market import INSTRUMENTS, get_market_hub, market_data_token

ui.setup("Market Desk", "📈")
ui.header(
    "Market Desk",
    "Live market data from Upstox V3. Research and paper-trading only.",
    mode="research:Market",
)

st.info(
    "🟢 MARKET DATA · Upstox Market Data Feed V3 is the live price source. "
    "Nifty 50 is supplied directly through the NSE_INDEX|Nifty 50 instrument feed."
)

token = market_data_token()
if not token:
    st.warning(
        "Upstox live data is not configured. Add UPSTOX_ANALYTICS_TOKEN to Streamlit Secrets "
        "(preferred for read-only market data) or UPSTOX_ACCESS_TOKEN. Never put the token in GitHub."
    )
    st.stop()

market_label = st.selectbox("Market", list(INSTRUMENTS), index=0, key="desk_upstox_market")
instrument_key = INSTRUMENTS[market_label]
window = st.slider("Candles", 60, 600, 240, step=30, key="desk_upstox_window")

hub = get_market_hub(token)
hub.start([instrument_key])
status_box = st.empty()

@st.fragment(run_every="2s")
def market_panel():
    status = hub.status()
    latest = hub.latest(instrument_key)
    bars = hub.snapshot(instrument_key, max_bars=window)

    if status["connected"]:
        mode_note = " · REST fallback (~3s)" if status.get("mode") == "rest-polling" else " · WebSocket"
        status_box.success(
            f"🟢 Upstox live{mode_note} · {len(bars)} one-minute candles · "
            f"{status['ticks']:,} ticks cached"
        )
    elif status["last_error"]:
        status_box.error(f"🔴 Upstox feed error: {status['last_error']}")
    else:
        status_box.info("🟡 Connecting to Upstox Market Data Feed V3…")

    if latest:
        previous = bars["close"].iloc[-2] if len(bars) >= 2 else latest["price"]
        change = latest["price"] - float(previous)
        ui.ticker([
            ("Market", market_label, None),
            ("LTP", f"₹{latest['price']:,.2f}", ui.tone(change)),
            ("Move", f"{change:+,.2f}", ui.tone(change)),
            ("Last tick", latest["datetime"].strftime("%H:%M:%S"), None),
            ("Feed", "LIVE", "up"),
        ])

    if bars.empty:
        st.info("Waiting for the first Upstox tick. The live chart will populate automatically.")
        return

    ui.show_chart(charts.candlestick(bars, height=600, max_bars=window, volume=True))
    st.caption(
        "Candles are built from observed Upstox V3 ticks in this TradeALGO server process. "
        "No AI-generated prices and no broker orders are used."
    )

market_panel()

st.divider()
st.subheader("TradeALGO workspace")
a, b, c = st.columns(3)
with a:
    st.markdown(ui.card("Before a trade", "Size the position, check your loss limit, and record the idea before taking risk.", "🧮"), unsafe_allow_html=True)
    st.page_link("pages/1_Position_size.py", label="Position size", icon="🧮")
    st.page_link("pages/2_Journal_and_report.py", label="Journal and daily report", icon="📒")
with b:
    st.markdown(ui.card("Practise", "Use fake money to rehearse option trades and understand time decay and spread.", "🎯"), unsafe_allow_html=True)
    st.page_link("pages/3_Practice_room.py", label="Practice room", icon="🎯")
    st.page_link("pages/4_Option_breakeven_and_ruin.py", label="Option breakeven and ruin", icon="⏳")
with c:
    st.markdown(ui.card("Research", "Backtest rules, stress-test them, and inspect whether the evidence survives.", "🔬"), unsafe_allow_html=True)
    st.page_link("pages/5_Backtest.py", label="Backtest", icon="📊")
    st.page_link("pages/6_Reality_check.py", label="Reality check", icon="🛡️")
    st.page_link("pages/7_Test_lab.py", label="Test lab", icon="🧪")

st.markdown("### What this market page uses")
ui.check_row("PASS", "Upstox V3 market feed", "Live ticks are supplied by Upstox. The selected market is read directly from its configured Upstox instrument key.")
ui.check_row("PASS", "REST fallback", "If the Upstox WebSocket is refused with 403, TradeALGO can fall back to REST LTP polling so the market view can continue updating.")
ui.check_row("PASS", "Nifty 50", "Nifty 50 uses the NSE_INDEX|Nifty 50 instrument key in the shared live-market hub.")
ui.check_row("PASS", "No live orders", "This Market Desk is for visualization and research. It does not place broker orders.")

st.info(storage_note())
st.markdown(
    "V3 note: Upstox sends market status first, then a market-data snapshot, followed by live updates. "
    "The current TradeALGO market hub consumes the live price stream and builds one-minute research candles."
)
ui.footer_note("Upstox market data + research only. No live orders.")
