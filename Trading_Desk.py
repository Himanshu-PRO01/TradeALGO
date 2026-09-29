"""TradeALGO Market Desk: live Upstox market data with a TradingView-style research view."""
import json

import streamlit as st

from algobot import charts, ui
from algobot.appstate import is_hosted, storage_note
from algobot.live_market import INSTRUMENTS, get_market_hub, market_data_token

ui.setup("Market Desk", "📈")
ui.header(
    "Market Desk",
    "Live market data from Upstox V3, with a TradingView chart option. Research and paper-trading only.",
    mode="research:Market",
)

st.info(
    "🟢 MARKET DATA · Upstox Market Data Feed V3 is the live price source. "
    "The TradingView tab is a separate embedded chart and is not fed by Upstox."
)

market_tab, tradingview_tab = st.tabs(["⚡ Upstox Live", "📊 TradingView"])

with market_tab:
    token = market_data_token()
    if not token:
        st.warning(
            "Upstox live data is not configured. Add UPSTOX_ANALYTICS_TOKEN to Streamlit Secrets "
            "(preferred for read-only market data) or UPSTOX_ACCESS_TOKEN. Never put the token in GitHub."
        )
    else:
        market_label = st.selectbox(
            "Market",
            list(INSTRUMENTS),
            index=0,
            key="desk_upstox_market",
        )
        instrument_key = INSTRUMENTS[market_label]
        window = st.slider(
            "Candles",
            min_value=60,
            max_value=600,
            value=240,
            step=30,
            key="desk_upstox_window",
        )

        hub = get_market_hub(token)
        hub.start([instrument_key])
        status_box = st.empty()

        @st.fragment(run_every="2s")
        def market_panel():
            status = hub.status()
            latest = hub.latest(instrument_key)
            bars = hub.snapshot(instrument_key, max_bars=window)

            if status["connected"]:
                mode = status.get("mode")
                mode_note = " · REST fallback (~3s)" if mode == "rest-polling" else " · WebSocket"
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

            ui.show_chart(charts.candlestick(bars, height=560, max_bars=window, volume=True))
            st.caption(
                "Candles are built from observed Upstox V3 ticks in this TradeALGO server process. "
                "No AI-generated prices and no broker orders are used."
            )

        market_panel()

with tradingview_tab:
    tv_symbol = st.selectbox(
        "TradingView symbol",
        ["NSE:RELIANCE", "NSE:HDFCBANK", "NSE:ICICIBANK", "NSE:NIFTY1!", "NSE:BANKNIFTY1!"],
        index=0,
        key="desk_tv_symbol",
    )
    tv_interval = st.selectbox(
        "Timeframe",
        ["1", "5", "15", "30", "60", "D", "W"],
        index=2,
        format_func=lambda value: {
            "1": "1 minute",
            "5": "5 minutes",
            "15": "15 minutes",
            "30": "30 minutes",
            "60": "1 hour",
            "D": "1 day",
            "W": "1 week",
        }[value],
        key="desk_tv_interval",
    )
    tv_height = st.slider(
        "Chart height",
        min_value=500,
        max_value=1100,
        value=700,
        step=20,
        key="desk_tv_height",
    )

    tv_config = {
        "autosize": False,
        "height": tv_height,
        "symbol": tv_symbol,
        "interval": tv_interval,
        "timezone": "exchange",
        "theme": "dark",
        "style": "1",
        "withdateranges": True,
        "hide_side_toolbar": False,
        "allow_symbol_change": False,
        "save_image": True,
        "hide_volume": False,
        "details": True,
        "calendar": False,
        "support_host": "https://www.tradingview.com",
        "studies": ["MASimple@tv-basicstudies", "RSI@tv-basicstudies"],
    }
    tv_html = f"""
    <div class="tradingview-widget-container"
         style="height:{tv_height}px;min-height:{tv_height}px;width:100%;overflow:hidden">
      <div class="tradingview-widget-container__widget"
           style="height:{tv_height}px;min-height:{tv_height}px;width:100%;overflow:hidden"></div>
      <div class="tradingview-widget-copyright"
           style="font-size:11px;text-align:center;padding-top:4px;">
        <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer">
          Charts by TradingView
        </a>
      </div>
      <script type="text/javascript"
              src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js"
              async>
        {json.dumps(tv_config)}
      </script>
    </div>
    """
    st.html(tv_html, height=tv_height + 20)

    st.caption(
        "TradingView is an independent embedded chart. Its feed is supplied by TradingView, "
        "not by the Upstox V3 connection."
    )

st.divider()

st.subheader("TradeALGO workspace")
a, b, c = st.columns(3)
with a:
    st.markdown(
        ui.card(
            "Before a trade",
            "Size the position, check your loss limit, and record the idea before taking risk.",
            "🧮",
        ),
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Position_size.py", label="Position size", icon="🧮")
    st.page_link("pages/2_Journal_and_report.py", label="Journal and daily report", icon="📒")
with b:
    st.markdown(
        ui.card(
            "Practise",
            "Use fake money to rehearse option trades and understand time decay and spread.",
            "🎯",
        ),
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_Practice_room.py", label="Practice room", icon="🎯")
    st.page_link("pages/4_Option_breakeven_and_ruin.py", label="Option breakeven and ruin", icon="⏳")
with c:
    st.markdown(
        ui.card(
            "Research",
            "Backtest rules, stress-test them, and inspect whether the evidence survives.",
            "🔬",
        ),
        unsafe_allow_html=True,
    )
    st.page_link("pages/5_Backtest.py", label="Backtest", icon="📊")
    st.page_link("pages/6_Reality_check.py", label="Reality check", icon="🛡️")
    st.page_link("pages/7_Test_lab.py", label="Test lab", icon="🧪")

st.markdown("### What this market page uses")
ui.check_row(
    "PASS",
    "Upstox V3 market feed",
    "Live ticks are supplied by Upstox. V3 supports LTPC, option Greeks, full market data and deeper full-D30 feeds depending on subscription mode.",
)
ui.check_row(
    "PASS",
    "REST fallback",
    "If the Upstox WebSocket is refused with 403, TradeALGO can fall back to REST LTP polling so the market view can continue updating.",
)
ui.check_row(
    "PASS",
    "TradingView option",
    "The embedded TradingView chart remains available separately; it is not mixed with the Upstox data stream.",
)
ui.check_row(
    "PASS",
    "No live orders",
    "This Market Desk is for visualization and research. It does not place broker orders.",
)

st.info(storage_note())
st.markdown(
    "V3 note: Upstox sends market status first, then a market-data snapshot, followed by live updates. "
    "The feed uses instrument keys and supports subscription modes such as LTPC, option Greeks, full and full D30. "
    "The current TradeALGO market hub consumes the live price stream and builds one-minute research candles."
)
ui.footer_note("Market data + research only. No live orders.")
