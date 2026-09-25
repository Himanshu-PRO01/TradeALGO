"""Front page of the trading desk. Start it with:  streamlit run Trading_Desk.py"""
import json

import streamlit as st
import streamlit.components.v1 as components

from algobot import ui
from algobot.appstate import is_hosted, storage_note

ui.setup("Trading Desk", "🏠")
ui.header("Trading Desk", "Size it, log it, practise it, test it. A workshop for learning and testing, "
          "not a signal service and not a broker.")

ui.ticker([("Live orders", "OFF", "up"), ("Broker", "not connected", None),
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
st.caption("Real market visualization for research. No broker connection and no live orders.")

chart_controls = st.columns([2, 2, 3])
with chart_controls[0]:
    dashboard_symbol = st.selectbox(
        "Symbol",
        ["NSE:NIFTY", "NSE:BANKNIFTY", "NSE:FINNIFTY", "NSE:RELIANCE", "NSE:HDFCBANK", "NSE:ICICIBANK"],
        index=0,
        key="dashboard_chart_symbol",
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
        min_value=600,
        max_value=1400,
        value=1000,
        step=20,
        help="Drag this to make the dashboard chart smaller or larger. 1000–1400 px is recommended for detailed viewing.",
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
    "allow_symbol_change": True,
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

components.html(dashboard_chart_html, height=dashboard_height + 15, scrolling=False)
st.caption("Chart size is controlled by the height slider above. Use Market Charts for the full research chart page.")


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
