"""Real-market chart page using TradingView's official embeddable Advanced Chart widget.

This page is market-data/visualization only. It does not connect to a broker account
and does not place orders.
"""
import json

import streamlit as st
import streamlit.components.v1 as components

from algobot import ui

ui.setup("Market Charts", "📈")
ui.header(
    "Market Charts",
    "Real market charts for research and visual analysis. This page does not place orders.",
    mode="research:market charts",
)

st.info(
    "LIVE MARKET DATA · NO LIVE ORDERS. "
    "The chart is supplied by TradingView's embeddable widget; no broker API key is required for this chart."
)

left, right = st.columns([1, 2])
with left:
    symbol = st.selectbox(
        "Starting symbol",
        [
            "NSE:NIFTY",
            "NSE:BANKNIFTY",
            "NSE:FINNIFTY",
            "NSE:RELIANCE",
            "NSE:HDFCBANK",
            "NSE:ICICIBANK",
        ],
        index=0,
    )
with right:
    interval = st.selectbox(
        "Timeframe",
        ["1", "5", "15", "30", "60", "D", "W"],
        index=2,
        format_func=lambda x: {"1": "1 minute", "5": "5 minutes", "15": "15 minutes",
                               "30": "30 minutes", "60": "1 hour", "D": "1 day", "W": "1 week"}[x],
    )

chart_config = {
    "autosize": True,
    "symbol": symbol,
    "interval": interval,
    "timezone": "exchange",
    "theme": "dark",
    "style": "1",
    "withdateranges": True,
    "hide_side_toolbar": False,
    "allow_symbol_change": True,
    "save_image": True,
    "hide_volume": False,
    "details": True,
    "calendar": False,
    "support_host": "https://www.tradingview.com",
    "studies": [
        "MASimple@tv-basicstudies",
        "RSI@tv-basicstudies",
    ],
}

config_json = json.dumps(chart_config)
chart_html = f"""
<div class="tradingview-widget-container" style="height:720px;width:100%">
  <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
  <div class="tradingview-widget-copyright"
       style="font-size:11px;text-align:center;padding-top:4px;">
    <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer">
      Charts by TradingView
    </a>
  </div>
  <script type="text/javascript"
          src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js"
          async>
    {config_json}
  </script>
</div>
"""

components.html(chart_html, height=735, scrolling=False)

st.markdown("### How this fits the tester")
st.markdown(
    """
- **Market Charts:** real market visualization and technical analysis.
- **Backtest:** historical rule testing using the project's research engine.
- **Strategy Lab:** generate and compare deterministic rule sets.
- **Paper Trading:** validate execution behavior with fake money.
- **Live Trading:** remains locked until explicitly approved and separately reviewed.
"""
)

st.caption(
    "TradingView's embeddable widget supplies its own market data. "
    "A broker API connection is a separate integration and should remain server-side."
)
ui.footer_note("Real-market chart for research. No broker connection and no live order execution.")
