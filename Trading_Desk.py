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

with st.expander("📐 Analysis controls", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        signal_mode = st.toggle("Research signals", value=True, key="desk_signal_mode")
    with c2:
        rsi_period = st.number_input("RSI period", min_value=5, max_value=30, value=14, step=1, key="desk_rsi_period")
    with c3:
        stop_pct = st.number_input("Stop-loss %", min_value=0.1, max_value=5.0, value=0.5, step=0.1, key="desk_stop_pct")
    with c4:
        target_pct = st.number_input("Target %", min_value=0.1, max_value=10.0, value=1.0, step=0.1, key="desk_target_pct")
    st.caption("Signals are rule-based research markers, not predictions or trade instructions. Risk lines are reference levels only.")
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
        st.info("Waiting for the first Upstox tick. The live chart will populate automatically.")
        return

    analysis = bars.copy()
    analysis["EMA 20"] = analysis["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    analysis["EMA 50"] = analysis["close"].ewm(span=50, adjust=False, min_periods=50).mean()

    volume_total = float(analysis["volume"].fillna(0).sum())
    if volume_total > 0:
        typical = (analysis["high"] + analysis["low"] + analysis["close"]) / 3.0
        analysis["VWAP"] = (typical * analysis["volume"].fillna(0)).cumsum() / analysis["volume"].fillna(0).cumsum()
    else:
        analysis["VWAP"] = pd.NA

    live_price = float(latest["price"]) if latest else None
    if live_price is not None:
        analysis["Live price"] = live_price

    hlines = {}
    if previous_levels.get("previous_high") is not None:
        hlines["Previous high"] = previous_levels["previous_high"]
    if previous_levels.get("previous_low") is not None:
        hlines["Previous low"] = previous_levels["previous_low"]

    overlays = {
        "EMA 20": "EMA 20",
        "EMA 50": "EMA 50",
    }
    if analysis["VWAP"].notna().any():
        overlays["VWAP"] = "VWAP"
    if live_price is not None:
        overlays["Live price"] = "Live price"

    # Research signal model: EMA crossover + RSI confirmation.
    delta_ema20 = analysis["EMA 20"].diff()
    crossed_up = (analysis["EMA 20"] > analysis["EMA 50"]) & (analysis["EMA 20"].shift(1) <= analysis["EMA 50"].shift(1))
    crossed_down = (analysis["EMA 20"] < analysis["EMA 50"]) & (analysis["EMA 20"].shift(1) >= analysis["EMA 50"].shift(1))

    delta = analysis["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / rsi_period, adjust=False, min_periods=rsi_period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / rsi_period, adjust=False, min_periods=rsi_period).mean()
    rs = gain / loss.replace(0, pd.NA)
    analysis["RSI"] = (100 - (100 / (1 + rs))).astype(float)

    buy_signal = crossed_up & (analysis["RSI"] >= 50)
    sell_signal = crossed_down & (analysis["RSI"] <= 50)
    signal_rows = []
    for ts, row in analysis.loc[buy_signal].iterrows():
        signal_rows.append({"datetime": ts, "price": float(row["close"]), "kind": "BUY", "shape": "triangle-up", "reason": "EMA20 crossed above EMA50 with RSI ≥ 50"})
    for ts, row in analysis.loc[sell_signal].iterrows():
        signal_rows.append({"datetime": ts, "price": float(row["close"]), "kind": "SELL", "shape": "triangle-down", "reason": "EMA20 crossed below EMA50 with RSI ≤ 50"})
    signals = pd.DataFrame(signal_rows)

    risk_lines = {}
    if live_price is not None:
        latest_signal = signals.iloc[-1]["kind"] if not signals.empty else None
        if latest_signal == "BUY":
            risk_lines = {
                "Long stop": live_price * (1 - stop_pct / 100),
                "Long target": live_price * (1 + target_pct / 100),
            }
        elif latest_signal == "SELL":
            risk_lines = {
                "Short stop": live_price * (1 + stop_pct / 100),
                "Short target": live_price * (1 - target_pct / 100),
            }
        else:
            risk_lines = {
                "Reference stop": live_price * (1 - stop_pct / 100),
                "Reference target": live_price * (1 + target_pct / 100),
            }

    ui.show_chart(
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

    rsi_chart = charts.rsi_chart(analysis["close"], period=rsi_period, height=180)
    if rsi_chart is not None:
        st.markdown("#### RSI")
        ui.show_chart(rsi_chart)

    session_date = pd.Timestamp(bars.index[-1]).strftime("%d %b %Y") if len(bars) else "—"
    signal_text = "signals enabled" if signal_mode else "signals hidden"
    st.caption(
        f"Session: {session_date} · Upstox V3 historical OHLCV + live market feed · {timeframe}-minute candles · {signal_text}. "
        "EMA 20/50, VWAP, previous-session levels and live price are overlays. "
        "Signals are research rules, not predictions; risk lines are reference levels."
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
        st.metric("EMA 20", f"₹{analysis['EMA 20'].iloc[-1]:,.2f}" if analysis["EMA 20"].notna().any() else "—")
    with m3:
        st.metric("EMA 50", f"₹{analysis['EMA 50'].iloc[-1]:,.2f}" if analysis["EMA 50"].notna().any() else "—")
    with m4:
        latest_rsi = analysis["RSI"].dropna().iloc[-1] if analysis["RSI"].notna().any() else None
        st.metric("RSI", f"{latest_rsi:.1f}" if latest_rsi is not None else "—")

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
