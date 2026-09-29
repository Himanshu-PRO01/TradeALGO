"""TradeALGO Market Desk: live Upstox V3 market data."""
import streamlit as st
import pandas as pd

from algobot import charts, ui
from algobot.appstate import storage_note
from algobot.live_market import INSTRUMENTS, get_market_hub, market_data_token

ui.setup("Market Desk", "📈")
ui.header(
    "Market Desk",
    "Official Upstox OHLCV candles + live price updates. Research and paper-trading only.",
    mode="research:Market",
)

st.info(
    "🟢 DATA SOURCE · Candles come from Upstox V3 OHLC history. "
    "The live feed updates the current 1-minute candle; TradeALGO does not generate market prices."
)

token = market_data_token()
if not token:
    st.warning(
        "Upstox live data is not configured. Add UPSTOX_ANALYTICS_TOKEN to Streamlit Secrets "
        "(preferred for read-only market data) or UPSTOX_ACCESS_TOKEN. Never put the token in GitHub."
    )
    st.stop()

left, mid, right = st.columns([1.35, 1, 1.2])
with left:
    market_label = st.selectbox("Market", list(INSTRUMENTS), index=0, key="desk_upstox_market")
with mid:
    timeframe = st.selectbox("Timeframe", [1, 3, 5, 15, 30], index=0, format_func=lambda x: f"{x} min", key="desk_timeframe")
with right:
    window = st.slider("Candles", 60, 500, 240, step=20, key="desk_upstox_window")
instrument_key = INSTRUMENTS[market_label]

hub = get_market_hub(token)
hub.start([instrument_key])
status_box = st.empty()

@st.fragment(run_every="2s")
def market_panel():
    status = hub.status()
    latest = hub.latest(instrument_key)
    bars = hub.snapshot(instrument_key, max_bars=window, interval_minutes=timeframe)
    history_count = int(status.get("history_bars", {}).get(instrument_key, 0))

    if status["connected"]:
        mode_note = "WebSocket" if status.get("mode") == "websocket" else "REST LTP fallback"
        if history_count:
            status_box.success(
                f"🟢 LIVE · {mode_note} · {history_count:,} official Upstox 1-min OHLC candles loaded"
            )
        else:
            status_box.warning("🟡 LIVE · official historical OHLC candles are not loaded yet")
    elif status.get("history_error"):
        status_box.error(f"🔴 Historical OHLC error: {status['history_error']}")
    elif status["last_error"]:
        status_box.error(f"🔴 Upstox feed error: {status['last_error']}")
    else:
        status_box.info("🟡 Connecting to Upstox V3 and loading official OHLC history…")

    if latest:
        previous = bars["close"].iloc[-2] if len(bars) >= 2 else latest["price"]
        change = latest["price"] - float(previous)
        last_bar = bars.iloc[-1] if len(bars) else None
        ui.ticker([
            ("Market", market_label, None),
            ("LTP", f"₹{latest['price']:,.2f}", ui.tone(change)),
            ("O/H/L", f"₹{last_bar['open']:,.2f} / ₹{last_bar['high']:,.2f} / ₹{last_bar['low']:,.2f}" if last_bar is not None else "—", None),
            ("Volume", f"{last_bar['volume']:,.0f}" if last_bar is not None else "—", None),
            ("Change", f"{change:+,.2f}", ui.tone(change)),
            ("Last", latest["datetime"].strftime("%d %b %H:%M:%S"), None),
        ])

    if bars.empty:
        st.info("Waiting for the first Upstox tick. The live chart will populate automatically.")
        return

    ui.show_chart(charts.candlestick(bars, height=600, max_bars=window, volume=True))
    st.caption(
        f"Source: Upstox V3 historical OHLCV + live market feed · {timeframe}-minute candles. "
        "Historical candles are not synthesized; live ticks only update the current 1-minute bar."
    )
    with st.expander("Latest OHLCV data", expanded=False):
        table = bars.tail(20).reset_index()
        table["datetime"] = pd.to_datetime(table["datetime"]).dt.strftime("%d %b %Y %H:%M")
        st.dataframe(
            table[["datetime", "open", "high", "low", "close", "volume"]],
            width="stretch",
            hide_index=True,
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

st.markdown("### Data integrity")
ui.check_row("PASS", "Official OHLCV", "Historical candles come from Upstox V3 historical/intraday candle APIs.")
ui.check_row("PASS", "Live updates", "The V3 market feed supplies the latest traded price and updates the current minute.")
ui.check_row("PASS", "No synthetic prices", "TradeALGO does not create or randomize market prices.")
ui.check_row("PASS", "No live orders", "This Market Desk only visualizes data and supports research/paper trading.")

st.info(storage_note())
st.markdown(
    "V3 note: Upstox sends market status first, then a market-data snapshot, followed by live updates. "
    "The current TradeALGO market hub consumes the live price stream and builds one-minute research candles."
)
ui.footer_note("Upstox market data + research only. No live orders.")
