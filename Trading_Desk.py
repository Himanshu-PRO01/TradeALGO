"""Front page of the trading desk. Start it with:  streamlit run Trading_Desk.py"""
import json

import streamlit as st

from algobot import charts, live_chart, ui
from algobot.appstate import is_hosted, storage_note

ui.setup("TradeALGO Trading Research Platform", "📈")
ui.header("TradeALGO Trading Research Platform", "A trading research and paper-trading platform for learning, strategy building, backtesting, risk analysis, and market practice. "
          "TradeALGO is a research and simulation tool, not a signal service or broker.")

# Public-facing introductory copy is intentionally rendered near the top of the
# homepage. Streamlit Community Cloud uses page title plus prominent header/text
# when search engines index public apps, so keep this concise and descriptive.
st.markdown(
    "### Trading strategy builder, backtesting and paper trading for Indian markets"
)
st.markdown(
    "TradeALGO helps traders turn ideas into measurable rules, backtest strategies "
    "on historical market data, test risk and robustness, save strategy results, and "
    "practise trades with virtual money. Explore Nifty-focused research, strategy "
    "building, paper trading and market analysis in one workspace."
)
st.caption(
    "Educational and research use only. Market data availability and timing can vary; "
    "backtests and paper results do not guarantee future performance."
)

ui.ticker([("Live orders", "OFF", "up"),
           ("Broker", "OpenAlgo connected (read-only)" if live_chart.openalgo_configured() else "not connected", None),
           ("Mode", "hosted" if is_hosted() else "local", None), ("Fake markets", "7 kinds", None),
           ("Journal", "in this browser tab" if is_hosted() else "on this computer", None)])

a, b, c = st.columns(3)
with a:
    st.markdown(ui.card("Before a trade", "How many lots fit your loss limit, and are today's limits still open? "
                        "Then write the trade down.", "🧮"), unsafe_allow_html=True)
    st.page_link("pages/1_Position_size.py", label="Position size", icon="🧮")
    st.page_link("pages/2_Journal_and_report.py", label="Journal and daily report", icon="📒")
with b:
    st.markdown(ui.card("Practise", "Buy and sell Nifty options with fake money in a fake market. Feel time decay "
                        "and spread without paying for the lesson.", "🎯"), unsafe_allow_html=True)
    st.page_link("pages/3_Practice_room.py", label="Practice room", icon="🎯")
    st.page_link("pages/4_Option_breakeven_and_ruin.py", label="Option breakeven and ruin", icon="⏳")
with c:
    st.markdown(ui.card("Research", "Test a rule on past prices, then try to break it before real money does.", "🔬"),
                unsafe_allow_html=True)
    st.page_link("pages/5_Backtest.py", label="Backtest", icon="📊")
    st.page_link("pages/6_Reality_check.py", label="Reality check", icon="🛡️")
    st.page_link("pages/7_Test_lab.py", label="Test lab", icon="🧪")

st.markdown("### 📈 Market Chart")
st.caption("Real market visualization for research. No live orders are placed from this page.")

use_openalgo = st.checkbox(
    "Use my OpenAlgo broker for this chart (real candles, no TradingView limits)",
    value=live_chart.openalgo_configured(),
    disabled=not live_chart.openalgo_configured(),
    help="Off by default. Needs OPENALGO_API_KEY (and OPENALGO_HOST if OpenAlgo isn't on this machine) "
         "set as a local .env value or a Streamlit secret -- the site operator's own broker connection, "
         "never requested from a visitor. When it's connected, every symbol below (including "
         "NIFTY1!/BANKNIFTY1!) charts your broker's real data instead of TradingView's widget, which "
         "can't redistribute most NSE data for free.",
    key="dashboard_use_openalgo",
)

chart_controls = st.columns([2, 2, 3])
with chart_controls[0]:
    dashboard_symbol = st.selectbox(
        "Symbol (widget-supported feed)",
        ["NSE:RELIANCE", "NSE:HDFCBANK", "NSE:ICICIBANK", "NSE:NIFTY1!", "NSE:BANKNIFTY1!"],
        index=0,
        key="dashboard_chart_symbol",
        help="Continuous futures symbols (NIFTY1!/BANKNIFTY1!) often fail with a "
             "'permission denied' error on TradingView's free anonymous embed -- that's "
             "a TradingView data-licensing restriction, not a bug here. Equity symbols "
             "load reliably. For a working NIFTY/Sensex chart with no such restriction, "
             "use the Live Markets page instead (free delayed data, no TradingView account needed).",
    )
with chart_controls[1]:
    dashboard_interval = st.selectbox(
        "Timeframe",
        ["1", "5", "15", "30", "60", "D", "W"],
        index=2,
        format_func=lambda x: {
            "1": "1 minute", "5": "5 minutes", "15": "15 minutes",
            "30": "30 minutes", "60": "1 hour", "D": "1 day", "W": "1 week"
        }[x],
        key="dashboard_chart_interval",
    )
with chart_controls[2]:
    dashboard_height = st.slider(
        "Chart height",
        min_value=500,
        max_value=1200,
        value=720,
        step=20,
        help="Drag this to make the dashboard chart smaller or larger. 720–1000 px works well on phones and desktop; increase it for detailed viewing.",
        key="dashboard_chart_height",
    )

dashboard_chart_config = {
    "autosize": False,
    "height": dashboard_height,
    "symbol": dashboard_symbol,
    "interval": dashboard_interval,
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

dashboard_chart_html = f"""
<div class="tradingview-widget-container" style="height:{dashboard_height}px;min-height:{dashboard_height}px;width:100%;overflow:hidden">
  <div class="tradingview-widget-container__widget" style="height:{dashboard_height}px;min-height:{dashboard_height}px;width:100%;overflow:hidden"></div>
  <div class="tradingview-widget-copyright"
       style="font-size:11px;text-align:center;padding-top:4px;">
    <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer">
      Charts by TradingView
    </a>
  </div>
  <script type="text/javascript"
          src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js"
          async>
    {json.dumps(dashboard_chart_config)}
  </script>
</div>
"""

candles, live_chart_error = (live_chart.fetch_candles(dashboard_symbol, dashboard_interval)
                              if use_openalgo else (None, None))
if candles is not None:
    ui.show_chart(charts.candlestick(candles, height=dashboard_height))
    st.caption(f"{len(candles):,} real candles for {dashboard_symbol} from your OpenAlgo broker connection. "
               "Research visualization only; no live orders are placed from this page.")
else:
    if use_openalgo:
        st.warning(f"Couldn't get real candles from OpenAlgo: {live_chart_error} Showing the TradingView "
                   "widget below instead.")
    st.iframe(dashboard_chart_html, height=dashboard_height + 15)
    st.caption("NIFTY1!/BANKNIFTY1! (continuous futures) sometimes get a 'permission denied' error from "
               "TradingView's free anonymous embed -- that's a TradingView data-licensing limit, not a bug "
               "here. Equity symbols above are reliable. For an always-working NIFTY/Sensex/Bank Nifty chart "
               "with no broker needed, use the **Live Markets** page (free delayed data, no TradingView "
               "restriction), or turn on the OpenAlgo option above once it's connected.")


st.markdown("### A 10-minute tour")
st.markdown("""
1. **Position size**: enter an option price and a stop. See how many lots fit your loss limit, and what a few losses in a row would do to the account.
2. **Practice room**: start a market (leave it on *random* so you cannot peek), buy an option with a stop, run the clock, sell, then press *Finish and review*. The review splits every trade into what the market move earned and what time decay, spread and charges took.
3. **Option breakeven and ruin**: for an at-the-money option with 3 days left, how far must Nifty move just to break even? And how likely is a normal losing streak to wreck a small account?
4. **Journal and report**: write one practice-style trade down and read the daily report. It flags trades without a stop and broken limits.
5. **Feedback**: write what is wrong, confusing or missing, in trading words. That is the most useful thing you can do.
""")

left, right = st.columns(2)
with left:
    st.markdown("### The most useful feedback")
    st.markdown("""
- **Trading terms that are wrong or unclear** (a label, a formula, a rule)
- **Numbers that do not match Upstox or TradingView**
- **Screens you would check every day** and what is missing from them
- **Your exact rules**: which levels, what triggers an entry, where the stop goes, when you skip a trade
""")
with right:
    st.markdown("### What this tool will never do")
    st.markdown("""
- Place an order or connect to your broker account
- Ask for a password, OTP or API key (if anything ever does, close it)
- Promise a profit. It can test ideas and enforce your own limits. That is all.
""")
st.info(storage_note())
ui.footer_note()
