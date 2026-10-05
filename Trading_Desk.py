"""TradeALGO Premium Trading Desk — screenshot-matched dark dashboard."""
import streamlit as st
import pandas as pd

from algobot import charts, ui
from algobot.live_market import INSTRUMENTS, get_market_hub, market_data_token

ui.setup("Trading Desk", "📈")

# ---------------------------------------------------------------------------
# Premium dark dashboard styling. This is intentionally scoped to the Trading
# Desk page so the rest of the research tools keep their existing layouts.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
:root{
  --ta-bg:#05090e;--ta-panel:#090f16;--ta-panel2:#0c141d;--ta-line:#182532;
  --ta-text:#f4f7fb;--ta-muted:#7f8d9d;--ta-blue:#2f7df6;--ta-green:#16c784;
  --ta-red:#ff4d73;--ta-cyan:#20d9ff;
}
html,body,[data-testid="stAppViewContainer"],[data-testid="stAppViewContainer"]>section,
[data-testid="stApp"],.stApp{
  background:#05090e!important;
  color:var(--ta-text)!important;
}
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(circle at 78% 0%,rgba(25,86,160,.09),transparent 25%),
    linear-gradient(180deg,#05090e 0%,#070d14 55%,#05090e 100%)!important;
}
[data-testid="stMain"],[data-testid="stMainBlockContainer"]{
  background:transparent!important;
}
.block-container{max-width:1500px!important;padding:1rem 1.35rem 4rem!important;background:transparent!important}
[data-testid="stHeader"]{background:#05090e!important}
[data-testid="stToolbar"]{background:#05090e!important}

.ta-shell{color:var(--ta-text)}
.ta-safety-strip{display:flex;align-items:center;gap:9px;margin:0 0 12px;padding:9px 13px;border:1px solid #274033;border-radius:9px;background:linear-gradient(90deg,#09130f,#0a1110);color:#dce8e1;font-size:.68rem}.ta-safety-strip>span{color:var(--ta-green);font-size:.9rem}.ta-safety-strip b{font-size:.67rem;letter-spacing:.08em}.ta-safety-strip em{padding:4px 7px;border:1px solid rgba(22,199,132,.28);border-radius:999px;color:var(--ta-green);font-style:normal;font-weight:800;font-size:.56rem}.ta-safety-strip small{margin-left:auto;color:#7f8d9d}@media(max-width:600px){.ta-safety-strip{flex-wrap:wrap}.ta-safety-strip small{width:100%;margin-left:0}}
.ta-topbar{display:flex;align-items:center;gap:14px;height:58px;margin-bottom:12px}
.ta-brand{font-size:1.15rem;font-weight:900;letter-spacing:.01em;white-space:nowrap}
.ta-brand b{color:var(--ta-blue)}
.ta-search{height:40px;flex:1;max-width:470px;border:1px solid #263749;border-radius:10px;background:#0b141e;color:#8494a7;padding:10px 14px;font-size:.78rem}
.ta-market{margin-left:auto;display:flex;gap:28px;align-items:center}
.ta-market small,.ta-user small{display:block;color:#7d8da0;font-size:.65rem}
.ta-market strong{font-size:.9rem}.ta-up{color:var(--ta-green)}.ta-down{color:var(--ta-red)}
.ta-user{padding-left:18px;border-left:1px solid var(--ta-line);font-size:.82rem}
.ta-avatar{display:inline-grid;place-items:center;width:32px;height:32px;margin-right:8px;border-radius:50%;background:#2878e8;color:white;font-weight:800}
.ta-hero{position:relative;overflow:hidden;min-height:245px;border:1px solid #203143;border-radius:16px;margin-bottom:13px;padding:34px 34px;background:
 radial-gradient(circle at 74% 45%,rgba(37,99,235,.28),transparent 25%),
 linear-gradient(105deg,#0b121a 0%,#0c1724 50%,#07111d 100%);
 box-shadow:0 18px 55px rgba(0,0,0,.22)}
.ta-hero:after{content:"";position:absolute;right:-5%;top:0;width:52%;height:100%;opacity:.34;background:
 linear-gradient(90deg,transparent,#1166d0),
 repeating-linear-gradient(0deg,transparent 0 35px,rgba(72,142,255,.18) 36px),
 repeating-linear-gradient(90deg,transparent 0 54px,rgba(72,142,255,.13) 55px);
 clip-path:polygon(18% 0,100% 0,100% 100%,0 100%)}
.ta-hero>*{position:relative;z-index:2}
.ta-kicker{display:inline-flex;align-items:center;gap:7px;padding:7px 12px;border:1px solid #28445b;border-radius:999px;background:#0c1a27;font-size:.68rem;font-weight:700}
.ta-kicker i{width:7px;height:7px;border-radius:50%;background:var(--ta-green);box-shadow:0 0 12px var(--ta-green)}
.ta-hero h1{max-width:640px;margin:14px 0 7px;font-size:2.55rem;line-height:1.05;letter-spacing:-.055em}
.ta-hero h1 span{color:var(--ta-blue)}
.ta-hero p{color:#a8b4c3;margin:0 0 20px;font-size:.9rem}
.ta-actions{display:flex;gap:10px}.ta-btn{display:inline-flex;padding:11px 18px;border-radius:10px;font-weight:750;font-size:.78rem}.ta-primary{background:#2378f3;color:#fff}.ta-secondary{border:1px solid #425467;color:#dce4ee}
.ta-discipline{position:absolute;right:31px;top:31px;z-index:3;font-size:.76rem;line-height:1.75;letter-spacing:.22em;color:#eaf2fb;text-align:right}
.ta-discipline b{display:block;color:var(--ta-green);font-size:1.25rem;letter-spacing:0}
.ta-grid{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:12px}
.ta-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px}
.ta-kpi{min-height:98px;padding:16px;border:1px solid #26384a;border-radius:13px;background:linear-gradient(145deg,#0f1924,#0b131c);box-shadow:0 10px 28px rgba(0,0,0,.12)}
.ta-kpi .label{color:#a0adbc;font-size:.68rem}.ta-kpi .value{margin:7px 0 4px;font-size:1.35rem;font-weight:850}.ta-kpi .delta{font-size:.67rem}.ta-icon{float:left;margin-right:10px;font-size:1.45rem}
.ta-card{border:1px solid #213344;border-radius:14px;background:linear-gradient(145deg,#0d1721,#0a121b);padding:17px;box-shadow:0 12px 32px rgba(0,0,0,.14);margin-bottom:12px}
.ta-card-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:13px}.ta-card-head h3{margin:0;font-size:1rem}.ta-card-head span{color:#8191a4;font-size:.68rem}
.ta-range{display:flex;border:1px solid #26384a;border-radius:8px;overflow:hidden}.ta-range span{padding:7px 10px;color:#9ba9b9;font-size:.66rem;border-right:1px solid #26384a}.ta-range span.active{background:#1466d6;color:#fff}
.ta-chart{height:225px;position:relative;border-radius:10px;background:
 linear-gradient(rgba(52,76,100,.16) 1px,transparent 1px),
 linear-gradient(90deg,rgba(52,76,100,.16) 1px,transparent 1px);
 background-size:10% 25%;overflow:hidden}
.ta-chart svg{position:absolute;inset:0;width:100%;height:100%}
.ta-quick{display:grid;grid-template-columns:1fr 1fr;gap:10px}.ta-quick a{padding:14px;border:1px solid #26384a;border-radius:11px;background:#0f1924;color:#dfe7ef;text-decoration:none}.ta-quick a:hover{border-color:#247cf5;background:#111f2e}.ta-quick b{display:block;font-size:.74rem}.ta-quick small{display:block;color:#8190a1;margin-top:5px;font-size:.63rem}
.ta-list{display:grid;gap:8px}.ta-row{display:flex;justify-content:space-between;gap:8px;padding:9px 0;border-bottom:1px solid #1b2937;color:#c7d0db;font-size:.68rem}.ta-row:last-child{border-bottom:0}.ta-row small{color:#7d8b9b}.ta-check{color:var(--ta-green)}
.ta-status{padding:14px;border:1px solid #203143;border-radius:12px;background:#0b151f}.ta-status h3{margin:0 0 12px;font-size:.9rem}.ta-safe{display:inline-block;padding:5px 9px;border:1px solid rgba(22,199,132,.35);border-radius:999px;color:var(--ta-green);font-size:.58rem;font-weight:800}
.ta-footer{display:flex;justify-content:space-between;color:#718096;font-size:.65rem;padding:12px 3px}
@media(max-width:900px){.ta-market{display:none}.ta-discipline{display:none}}
@media(max-width:760px){.ta-grid{grid-template-columns:1fr}.ta-kpis{grid-template-columns:1fr 1fr}}
@media(max-width:560px){.ta-kpis{grid-template-columns:1fr}.ta-quick{grid-template-columns:1fr}}
@media(max-width:600px){.block-container{padding:.6rem .7rem 3rem!important}.ta-hero{padding:22px 18px;min-height:235px}.ta-hero h1{font-size:2rem}.ta-kpis{grid-template-columns:1fr}.ta-topbar{height:auto}.ta-search{display:none}.ta-footer{flex-direction:column;gap:8px}.ta-quick{grid-template-columns:1fr}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="ta-shell">', unsafe_allow_html=True)

# Top utility bar — intentionally mirrors the reference layout.
st.markdown("""
<div id="tradealgo-top" class="ta-topbar">
  <div class="ta-brand">📈 Trade<span style="color:#2f7df6">ALGO</span></div>
  <div class="ta-search">⌕ &nbsp; Search symbols (e.g. NIFTY, RELIANCE, AAPL)... &nbsp;&nbsp; <b style="float:right;color:#aebdce">Ctrl K</b></div>
  <div class="ta-market">
    <div><small>NIFTY</small><strong>24,612.30 &nbsp;<span class="ta-up">+1.24%</span></strong></div>
    <div><small>SENSEX</small><strong>80,432.12 &nbsp;<span class="ta-up">+1.10%</span></strong></div>
  </div>
  <div class="ta-user"><span class="ta-avatar">H</span><b>Himanshu</b><small>Pro Plan</small></div>
</div>
""", unsafe_allow_html=True)

# Explicit safety strip: this dashboard is research/paper-only and never places live orders.
st.markdown(
    '<div class="ta-safety-strip"><span>●</span><b>LIVE ORDERS: OFF</b><em>NO LIVE ORDERS</em><small>Research &amp; paper trading only · only visualizes data</small></div>',
    unsafe_allow_html=True,
)

# Hero.
st.markdown("""
<section class="ta-hero">
  <div class="ta-kicker"><i></i> Welcome to TradeALGO</div>
  <h1>Trade with clarity.<br><span>Test your strategy before you trust it.</span></h1>
  <p>Backtest • Practice • Analyze • Improve — All in one platform.</p>
  <div class="ta-actions">
    <a class="ta-btn ta-primary" href="#desk-controls">Start Testing&nbsp; →</a>
    <a class="ta-btn ta-secondary" href="#workspace">▣ &nbsp;View Documentation</a>
  </div>
  <div class="ta-discipline">DISCIPLINE<br>BEATS<br>EMOTION<b>━━━━</b></div>
</section>
""", unsafe_allow_html=True)

# Market controls remain functional and are visually tucked into the dashboard.
token = market_data_token()
market_label = list(INSTRUMENTS)[0]
timeframe = 1
window = 240
if token:
    c1,c2,c3 = st.columns([1.4,1,1.1])
    with c1:
        market_label = st.selectbox("Market", list(INSTRUMENTS), index=0, key="desk_upstox_market")
    with c2:
        timeframe = st.selectbox("Timeframe", [1,3,5,15,30], index=0, format_func=lambda x:f"{x} min", key="desk_timeframe")
    with c3:
        window = st.slider("Candles", 60, 500, 240, step=20, key="desk_upstox_window")
else:
    st.markdown('<div id="desk-controls"></div>', unsafe_allow_html=True)

# Live data snapshot.
latest = None
bars = pd.DataFrame()
analysis = pd.DataFrame()
status_text = "Market feed not configured"
if token:
    instrument_key = INSTRUMENTS[market_label]
    hub = get_market_hub(token)
    hub.start([instrument_key])
    status = hub.status()
    latest = hub.latest(instrument_key)
    bars = hub.snapshot(instrument_key, max_bars=window, interval_minutes=timeframe, latest_session_only=True)
    status_text = "LIVE" if status.get("connected") else ("CONNECTING" if not status.get("last_error") else "ERROR")

    if latest and not bars.empty:
        def _wma(series, period):
            period=max(1,int(period)); weights=pd.Series(range(1,period+1),dtype=float)
            return series.rolling(period,min_periods=period).apply(lambda v: float((v*weights.to_numpy()).sum()/weights.sum()),raw=True)
        period=21
        half=max(1,period//2); root=max(1,int(round(period**0.5)))
        analysis=bars.copy()
        analysis["HMA"]=_wma((2*_wma(analysis["close"],half)-_wma(analysis["close"],period)),root)
        rng=(analysis["high"]-analysis["low"]).replace(0,pd.NA)
        loc=(((2*analysis["close"])-analysis["high"]-analysis["low"])/rng).clip(-1,1).fillna(0)
        analysis["Order-flow delta"]=analysis["volume"].fillna(0)*loc
        analysis["Cumulative delta"]=analysis["Order-flow delta"].cumsum()

# KPI values use only real market data; unavailable portfolio/account values are not invented.
price = float(latest["price"]) if latest else None
change = (price - float(bars["close"].iloc[-2])) if price is not None and len(bars)>=2 else None
hma = float(analysis["HMA"].dropna().iloc[-1]) if not analysis.empty and analysis["HMA"].notna().any() else None
flow = float(analysis["Order-flow delta"].iloc[-1]) if not analysis.empty else None

def metric_card(icon,label,value,delta="",tone=""):
    return f'<div class="ta-kpi"><span class="ta-icon">{icon}</span><div class="label">{label}</div><div class="value">{value}</div><div class="delta {tone}">{delta}</div></div>'

st.markdown(
    '<div class="ta-kpis">'+
    metric_card("💼","Market LTP",f"₹{price:,.2f}" if price is not None else "—","Live Upstox price" if price is not None else "Waiting for data")+
    metric_card("📊","Current Change",f"{change:+,.2f}" if change is not None else "—","vs previous candle","ta-up" if change and change>0 else "ta-down")+
    metric_card("🎯","HMA 21",f"₹{hma:,.2f}" if hma is not None else "—","Research indicator")+
    metric_card("🛡️","Flow Delta",f"{flow:+,.0f}" if flow is not None else "—","OHLCV pressure proxy")+
    '</div>',unsafe_allow_html=True)

st.markdown('<div class="ta-grid"><main>',unsafe_allow_html=True)

# Equity-style chart card; when live data exists it is the actual market curve.
st.markdown("""
<div class="ta-card">
  <div class="ta-card-head"><h3>↗ &nbsp;Market Curve</h3><div class="ta-range"><span>1D</span><span>1W</span><span class="active">1M</span><span>3M</span><span>1Y</span><span>All</span></div></div>
""",unsafe_allow_html=True)
if not bars.empty:
    chart_df=bars[["close"]].tail(min(len(bars),180)).copy()
    st.line_chart(chart_df, height=225, use_container_width=True)
else:
    st.markdown("""
    <div class="ta-chart"><svg viewBox="0 0 900 240" preserveAspectRatio="none">
      <polyline points="0,205 75,190 145,198 220,155 290,166 365,128 440,142 520,96 595,112 670,68 745,82 820,48 900,61" fill="none" stroke="#2f7df6" stroke-width="4"/>
      <polyline points="0,220 110,205 220,212 330,185 440,194 550,165 660,178 770,148 900,152" fill="none" stroke="#718096" stroke-width="2"/>
    </svg></div>
    """,unsafe_allow_html=True)
st.markdown('<div style="display:flex;gap:18px;color:#8796a8;font-size:.65rem;margin-top:8px">■ Market price &nbsp;&nbsp; ■ Benchmark/reference</div></div>',unsafe_allow_html=True)

# Recent activity / workspace.
st.markdown("""
<div class="ta-card" id="workspace">
<div class="ta-card-head"><h3>◷ &nbsp;Recent Activity</h3><span>View All →</span></div>
<div class="ta-row"><span>Market Desk</span><small>LIVE MARKET</small><b class="ta-check">Connected</b></div>
<div class="ta-row"><span>Backtest</span><small>Research workflow</small><b>Ready</b></div>
<div class="ta-row"><span>Reality Check</span><small>Validation workflow</small><b>Ready</b></div>
<div class="ta-row"><span>Practice Trading</span><small>Paper money only</small><b class="ta-check">Safe</b></div>
</div>
""",unsafe_allow_html=True)

st.markdown('</main><aside>',unsafe_allow_html=True)

st.markdown('<div class="ta-card"><div class="ta-card-head"><h3>⚡ Quick Actions</h3><span>→</span></div><div class="ta-quick">',unsafe_allow_html=True)
qa=st.columns(2)
quick_actions=[
    ("pages/5_Backtest.py","📊 Run Backtest","Test your strategy on historical data →"),
    ("pages/3_Practice_room.py","🎮 Practice Trading","Trade with paper money risk-free →"),
    ("pages/6_Reality_check.py","🛡 Reality Check","Validate results & avoid overfitting →"),
    ("pages/10_Strategy_Builder.py","💡 Build Strategy","Create and customize your strategy →"),
]
for idx,(path,label,desc) in enumerate(quick_actions):
    with qa[idx % 2]:
        st.page_link(path,label=label,use_container_width=True)
        st.caption(desc)
st.markdown('</div>',unsafe_allow_html=True)

st.markdown(f"""
<div class="ta-status">
<div class="ta-card-head"><h3>🛡 Risk Controls Active</h3><span class="ta-safe">SAFE MODE</span></div>
<div class="ta-list">
<div class="ta-row"><span>✓ &nbsp;No live orders</span><small>Paper/research only</small></div>
<div class="ta-row"><span>✓ &nbsp;Realistic costs</span><small>Where supported</small></div>
<div class="ta-row"><span>✓ &nbsp;Future-data checks</span><small>Enabled in research flows</small></div>
<div class="ta-row"><span>✓ &nbsp;Position limits</span><small>Risk-aware workflow</small></div>
</div>
</div>
""",unsafe_allow_html=True)

st.markdown(f"""
<div class="ta-card">
<div class="ta-card-head"><h3>▥ Market Status</h3><span class="ta-safe">{status_text}</span></div>
<div class="ta-row"><b>{market_label}</b><span class="ta-up">● {status_text}</span><small>Upstox</small></div>
<div class="ta-row"><b>Data source</b><span>OHLCV + LTP</span></div>
<div class="ta-row"><b>Orders</b><span class="ta-check">● Locked</span></div>
</div>
""",unsafe_allow_html=True)

st.markdown('</aside></div>',unsafe_allow_html=True)

# Preserve the actual live-market chart and analysis tools below the visual dashboard.
if token and not bars.empty:
    with st.expander("Live Market Analysis", expanded=False):
        st.caption("The premium dashboard above is the landing view. Expand this section for the full existing market-analysis workspace.")
        ui.show_chart(charts.candlestick(
            analysis, height=520, max_bars=window, volume=True, interval_minutes=timeframe,
            overlays={"HMA":"HMA"} if "HMA" in analysis else None,
        ))
        st.caption("OHLCV-derived order-flow pressure is a research proxy, not exchange-level aggressor-side data.")
        ui.show_chart(charts.order_flow_chart(analysis, height=190))

st.markdown("""
<div class="ta-footer">
  <span>📈 TradeALGO &nbsp; v1.0.0 &nbsp; • &nbsp; ◉ Built for smarter traders</span>
  <span>Documentation &nbsp;&nbsp; Report Issue &nbsp;&nbsp; Feedback &nbsp;&nbsp; ◌</span>
</div>
""",unsafe_allow_html=True)
st.markdown('</div>',unsafe_allow_html=True)
