"""TradeALGO Market Research Agent."""
import datetime as dt
import pandas as pd
import streamlit as st
from algobot import ui
from algobot.market_agent import fetch_news, fetch_yfinance, fetch_openalgo, merge_sources, run_agent, summarize

ui.setup("Market Research Agent", "🧠")
ui.header("Market Research Agent",
          "Collect → compare → test → stress-test. Research only; this agent cannot place orders.",
          mode="research:Agent")

with st.expander("What this agent actually does", expanded=True):
    st.markdown("The agent collects supported market history and permitted RSS headlines, generates transparent rule-based candidates, backtests them with TradeALGO, then runs the existing Reality Check. It does **not** train on future prices and it cannot place orders.")

c1,c2,c3,c4=st.columns(4)
with c1: symbol=st.text_input("Symbol", "NIFTY", help="Examples: NIFTY, RELIANCE.NS, TCS.NS")
with c2: period=st.selectbox("History", ["6mo","1y","2y","5y"], index=2)
with c3: interval=st.selectbox("Interval", ["1d"], index=0)
with c4: audit_on=st.toggle("Reality-check candidates", True)

if st.button("🧠 Run research agent", type="primary", width="stretch"):
    with st.spinner("Collecting sources and testing strategy candidates..."):
        yf_source=fetch_yfinance(symbol, period=period, interval=interval)
        sources=[yf_source]
        today=dt.date.today()
        years={"6mo":1,"1y":1,"2y":2,"5y":5}[period]
        oa=fetch_openalgo(symbol.replace(".NS","").replace(".BO",""), (today-dt.timedelta(days=365*years)).isoformat(), today.isoformat(), "D")
        sources.append(oa)
        prices=merge_sources(sources)
        news=fetch_news(limit=6)
        if prices is None or len(prices)<120:
            st.error("Not enough usable price history. Check the symbol and data-source configuration.")
            st.session_state["agent_report"]=None
        else:
            report=run_agent(prices, symbol, period, audit_candidates=audit_on)
            report.sources=sources
            report.news=news
            st.session_state["agent_report"]=report

report=st.session_state.get("agent_report")
if report:
    st.success("Research run completed. No orders were sent.")
    s=report.selected
    if s:
        m=s.metrics
        ui.ticker([("Return",f"{m.get('return_pct',0):+.2f}%",ui.tone(m.get('return_pct',0))),
                   ("Net P&L",f"₹{m.get('net_pnl',0):,.0f}",ui.tone(m.get('net_pnl',0))),
                   ("Trades",m.get('trades',0),None),("Win rate",f"{m.get('win_rate_pct') or 0:.1f}%",None),
                   ("Profit factor",f"{m.get('profit_factor'):.2f}" if m.get('profit_factor') not in (None,float('inf')) else "—",None),
                   ("Max DD",f"{m.get('max_drawdown_pct',0):.2f}%","down")])
        st.markdown("### Best research candidate")
        st.markdown(f"**{s.name}** — {summarize(report)}")
        if s.audit:
            if s.audit.verdict.startswith("PASSED"): st.success(s.audit.verdict)
            elif s.audit.verdict.startswith("PROMISING"): st.warning(s.audit.verdict)
            else: st.error(s.audit.verdict)
        for note in s.notes: st.warning(note)
    st.markdown("### Candidate leaderboard")
    rows=[]
    for c in report.candidates:
        rows.append({"Strategy":c.name,"Score":round(c.score,2),"Return %":round(float(c.metrics.get("return_pct",0)),2),
                     "Net P&L":round(float(c.metrics.get("net_pnl",0)),2),"Trades":int(c.metrics.get("trades",0)),
                     "Win %":round(float(c.metrics.get("win_rate_pct") or 0),1),
                     "Profit factor":round(float(c.metrics.get("profit_factor") or 0),2),
                     "Max DD %":round(float(c.metrics.get("max_drawdown_pct") or 0),2)})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.markdown("### Data sources")
    for src in report.sources:
        ui.check_row("PASS" if src.ok else "WARN",src.name,f"{src.rows:,} rows · {src.detail}" if src.ok else src.detail)
    st.markdown("### Market/news context")
    if report.news:
        for item in report.news[:12]: st.markdown(f"- **{item.source}** — [{item.title}]({item.url})")
    else: st.caption("No permitted RSS headlines were available on this run.")
    with st.expander("Agent methodology"):
        st.markdown("1. Fetch price history. 2. Keep provenance and skip unavailable sources. 3. Test EMA trend, breakout and RSI mean-reversion candidates. 4. Score by return, drawdown, profit factor, trade count and Reality Check. 5. Treat the winner as a hypothesis; freeze it, test unseen data, then paper trade.")

ui.footer_note("Research agent only · no live orders · backtest results do not guarantee future returns.")
