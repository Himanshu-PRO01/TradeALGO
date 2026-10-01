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
    "The live feed supplies the current LTP separately; chart candles remain official Upstox OHLCV."
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

with st.expander("📐 Signal controls", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        signal_mode = st.toggle("Research signals", value=True, key="desk_signal_mode")
    with c2:
        hma_period = st.number_input("HMA period", min_value=5, max_value=100, value=21, step=1, key="desk_hma_period")
    with c3:
        stop_pct = st.number_input("Stop-loss %", min_value=0.1, max_value=5.0, value=0.5, step=0.1, key="desk_stop_pct")
    st.caption("Signals combine HMA direction with a candle-derived order-flow pressure proxy. They are research markers, not predictions or trade instructions.")
instrument_key = INSTRUMENTS[market_label]

hub = get_market_hub(token)
hub.start([instrument_key])
status_box = st.empty()

@st.fragment(run_every="2s")
def market_panel():
    status = hub.status()
    latest = hub.latest(instrument_key)
    bars = hub.snapshot(
        instrument_key,
        max_bars=window,
        interval_minutes=timeframe,
        latest_session_only=True,
    )
    history_count = int(status.get("history_bars", {}).get(instrument_key, 0))
    previous_levels = hub.session_levels(instrument_key)

    if status.get("history_error"):
        mode_note = "WebSocket" if status.get("mode") == "websocket" else ("REST LTP fallback" if status.get("mode") == "rest-polling" else "offline")
        status_box.error(
            f"🔴 HISTORICAL OHLC UNAVAILABLE · {status['history_error']} · Live feed: {mode_note}"
        )
    elif status["connected"] and history_count:
        mode_note = "WebSocket" if status.get("mode") == "websocket" else "REST LTP fallback"
        status_box.success(
            f"🟢 LIVE · {mode_note} · {history_count:,} official Upstox 1-min OHLC candles loaded"
        )
    elif status["connected"]:
        status_box.warning("🟡 LIVE FEED CONNECTED · waiting for official Upstox OHLC history")
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
        st.info("Official Upstox OHLC candles are not loaded yet. The chart will appear when the candle API returns data.")
        return

    analysis = bars.copy()

    def _wma(series, period):
        period = max(1, int(period))
        weights = pd.Series(range(1, period + 1), dtype=float)
        return series.rolling(period, min_periods=period).apply(
            lambda values: float((values * weights.to_numpy()).sum() / weights.sum()),
            raw=True,
        )

    half = max(1, int(hma_period) // 2)
    root = max(1, int(round(hma_period ** 0.5)))
    wma_half = _wma(analysis["close"], half)
    wma_full = _wma(analysis["close"], int(hma_period))
    analysis["HMA"] = _wma((2.0 * wma_half) - wma_full, root)

    # Historical OHLCV does not contain exchange-level aggressor buy/sell volume.
    # This is an explicitly labelled candle-derived order-flow pressure proxy.
    candle_range = (analysis["high"] - analysis["low"]).replace(0, pd.NA)
    close_location = ((2.0 * analysis["close"]) - analysis["high"] - analysis["low"]) / candle_range
    close_location = close_location.clip(-1.0, 1.0).fillna(0.0)
    analysis["Buy volume proxy"] = analysis["volume"].fillna(0.0) * ((close_location + 1.0) / 2.0)
    analysis["Sell volume proxy"] = analysis["volume"].fillna(0.0) - analysis["Buy volume proxy"]
    analysis["Order-flow delta"] = analysis["Buy volume proxy"] - analysis["Sell volume proxy"]
    analysis["Cumulative delta"] = analysis["Order-flow delta"].cumsum()

    live_price = float(latest["price"]) if latest else None
    if live_price is not None:
        analysis["Live price"] = live_price

    hlines = {}
    if previous_levels.get("previous_high") is not None:
        hlines["Previous high"] = previous_levels["previous_high"]
    if previous_levels.get("previous_low") is not None:
        hlines["Previous low"] = previous_levels["previous_low"]

    overlays = {"HMA": "HMA"}
    if live_price is not None:
        overlays["Live price"] = "Live price"

    hma_rising = analysis["HMA"] > analysis["HMA"].shift(1)
    hma_falling = analysis["HMA"] < analysis["HMA"].shift(1)
    flow_positive = analysis["Order-flow delta"] > 0
    flow_negative = analysis["Order-flow delta"] < 0
    buy_condition = (analysis["close"] > analysis["HMA"]) & hma_rising & flow_positive
    sell_condition = (analysis["close"] < analysis["HMA"]) & hma_falling & flow_negative
    buy_signal = buy_condition & ~buy_condition.shift(1).fillna(False)
    sell_signal = sell_condition & ~sell_condition.shift(1).fillna(False)

    signal_rows = []
    for ts, row in analysis.loc[buy_signal].iterrows():
        signal_rows.append({"datetime": ts, "price": float(row["close"]), "kind": "BUY", "shape": "triangle-up",
                            "reason": "Price above rising HMA with positive order-flow delta"})
    for ts, row in analysis.loc[sell_signal].iterrows():
        signal_rows.append({"datetime": ts, "price": float(row["close"]), "kind": "SELL", "shape": "triangle-down",
                            "reason": "Price below falling HMA with negative order-flow delta"})
    signals = pd.DataFrame(signal_rows)

    risk_lines = {}
    if live_price is not None:
        latest_signal = signals.iloc[-1]["kind"] if not signals.empty else None
        if latest_signal == "BUY":
            risk_lines =    ui.show_chart(
        charts.candlestick(
            analysis,
            height=600,
            max_bars=window,
            volume=True,
            interval_minutes=timeframe,
            overlays=overlays,
            hlines=hlines,
            signals=signals if signal_mode else None,
            risk_lines=risk_lines,
        )
    )

    st.markdown("#### Order Flow")
    st.caption("OHLCV-derived order-flow pressure proxy · positive delta = stronger buying pressure, negative = stronger selling pressure.")
    ui.show_chart(charts.order_flow_chart(analysis, height=190))

    session_date = pd.Timestamp(bars.index[-1]).strftime("%d %b %Y") if len(bars) else "—"
    signal_text = "signals enabled" if signal_mode else "signals hidden"
    st.caption(
        f"Session: {session_date} · Official Upstox V3 OHLCV candles · live LTP shown separately · {timeframe}-minute candles · {signal_text}. "
        "HMA and live price are the only chart overlays; previous-session levels remain reference levels. "
        "Order-flow is an OHLCV-derived pressure proxy, not exchange-level aggressor-side data. Signals are research rules, not predictions."
    )
    with st.expander("Latest OHLCV data", expanded=False):
        table = bars.tail(20).reset_index()
        table["datetime"] = pd.to_datetime(table["datetime"]).dt.strftime("%d %b %Y %H:%M")
        st.dataframe(
            table[["datetime", "open", "high", "low", "close", "volume"]],
            width="stretch",
            hide_index=True,
        )

    st.markdown("### Market analysis")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Last", f"₹{live_price:,.2f}" if live_price is not None else "—")
    with m2:
        hma_last = analysis["HMA"].dropna().iloc[-1] if analysis["HMA"].notna().any() else None
        st.metric("HMA", f"₹{hma_last:,.2f}" if hma_last is not None else "—")
    with m3:
        st.metric("Flow delta", f"{float(analysis['Order-flow delta'].iloc[-1]):+,.0f}")
    with m4:
        st.metric("Cumulative delta", f"{float(analysis['Cumulative delta'].iloc[-1]):+,.0f}")

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
ui.check_row("PASS", "Live updates", "The V3 market feed supplies the latest traded price separately from the official OHLC candle series.")
ui.check_row("PASS", "No synthetic prices", "TradeALGO does not create or randomize market prices.")
ui.check_row("PASS", "No live orders", "This Market Desk only visualizes data and supports research/paper trading.")

st.info(storage_note())
st.markdown(
    "V3 note: Upstox sends market status first, then a market-data snapshot, followed by live updates. "
    "The current TradeALGO market hub uses Upstox OHLC history as the chart source and keeps the live price stream separate."
)
ui.footer_note("Upstox market data + research only. No live orders.")
