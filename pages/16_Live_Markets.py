"""Live Markets: delayed price charts for Nifty 50, Sensex, Bank Nifty and
more -- a watch screen for building and eyeballing a strategy. Read-only:
no orders, no broker connection.
"""
import time

import streamlit as st

from algobot import ui
from algobot.charts import candlestick
from algobot.live_data import INTERVALS, MARKETS, LiveDataError, fetch_ohlc

ui.setup("Live Markets", "📈")
ui.header(
    "Live Markets",
    "Delayed price charts for Nifty 50, Sensex, Bank Nifty and more, for watching the market "
    "while you build a strategy. This is free Yahoo Finance data, typically 15-20 minutes "
    "delayed for Indian indices -- NOT a live tick feed -- and it never places an order.",
    mode="execution:Live Markets",
)


@st.cache_data(ttl=30, show_spinner=False)
def cached_ohlc(ticker: str, interval: str, period: str):
    return fetch_ohlc(ticker, interval, period)


c1, c2, c3 = st.columns([2, 1, 1])
market_label = c1.selectbox("Market", list(MARKETS))
interval_label = c2.selectbox("Timeframe", list(INTERVALS), index=1)
auto = c3.checkbox("Auto-refresh (30s)", value=False)

interval, period = INTERVALS[interval_label]
ticker = MARKETS[market_label]

try:
    df = cached_ohlc(ticker, interval, period)
except LiveDataError as exc:
    st.error(str(exc))
    st.stop()

last = df.iloc[-1]
day_open = float(df["close"].iloc[0])
change = float(last["close"] - day_open)
change_pct = (change / day_open * 100.0) if day_open else 0.0

m1, m2, m3, m4 = st.columns(4)
m1.metric(market_label, f"{last['close']:.2f}", f"{change:+.2f} ({change_pct:+.2f}%)")
m2.metric("Session high", f"{df['high'].max():.2f}")
m3.metric("Session low", f"{df['low'].min():.2f}")
m4.metric("As of (data time)", df.index[-1].strftime("%d %b %H:%M"))

chart = candlestick(df, height=420, max_bars=300, volume="volume" in df.columns and df["volume"].sum() > 0)
if chart is not None:
    ui.show_chart(chart)
else:
    st.info("Not enough bars yet to draw a chart.")

with st.expander("Watch more markets side by side"):
    others = st.multiselect("Add markets", [m for m in MARKETS if m != market_label])
    for name in others:
        try:
            odf = cached_ohlc(MARKETS[name], interval, period)
            olast = odf.iloc[-1]
            oopen = float(odf["close"].iloc[0])
            ochg = float(olast["close"] - oopen)
            ochg_pct = (ochg / oopen * 100.0) if oopen else 0.0
            st.metric(name, f"{olast['close']:.2f}", f"{ochg:+.2f} ({ochg_pct:+.2f}%)")
        except LiveDataError as exc:
            st.warning(f"{name}: {exc}")

st.caption(
    "Data: Yahoo Finance via `yfinance`, typically delayed 15-20 minutes for NSE/BSE indices "
    "(faster for some instruments, slower around volatile opens). For true real-time ticks you "
    "need a paid broker market-data feed -- unrelated to the Upstox Sandbox page, which only "
    "tests order placement, never prices."
)

ui.footer_note("Live Markets is read-only price watching. It never places an order or connects to a broker.")

if auto:
    time.sleep(30)
    st.rerun()
