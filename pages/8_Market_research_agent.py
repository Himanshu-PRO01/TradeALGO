"""TradeALGO Market Research Agent v2."""
import datetime as dt
import pandas as pd
import streamlit as st
from algobot import ui
from algobot.market_agent import fetch_news, fetch_yfinance, fetch_openalgo, merge_sources
from algobot.market_agent_v2 import run_v2, source_check, fetch_upstox, fetch_nse_history

ui.setup("Market Research Agent","🧠")
ui.header("Market Research Agent","Multi-source → parameter search → walk-forward → reality check. Research only; no orders.","research:Agent")
with st.expander("What the agent does",expanded=True):
    st.markdown("v2 validates available price sources, searches transparent strategy parameters, selects only inside training windows, tests the next unseen window, and reality-checks the strongest candidates. News is context only.")

c1,c2,c3,c4=st.columns(4)
with c1: symbol=st.text_input("Symbol","NIFTY",help="Examples: NIFTY, RELIANCE.NS, TCS.NS")
with c2: period=st.selectbox("History",["6mo","1y","2y","5y"],index=2)
with c3: interval=st.selectbox("Interval",["1d"],index=0)
with c4: audit_on=st.toggle("Reality check",True)

if st.button("🧠 Run Market Research Agent v2",type="primary",width="stretch"):
    with st.spinner("Collecting sources and running walk-forward research..."):
        today=dt.date.today(); years={"6mo":1,"1y":1,"2y":2,"5y":5}[period]
        start=(today-dt.timedelta(days=365*years)).isoformat(); end=today.isoformat()
        clean=symbol.replace(".NS","").replace(".BO","")
        sources=[
            fetch_yfinance(symbol,period=period,interval=interval),
            fetch_openalgo(clean,start,end,"D"),
            fetch_upstox(clean,start,end,"1day"),
            fetch_nse_history(clean,start,end)]
        prices=merge_sources(sources)
        news=fetch_news(limit=6)
        if prices is None or len(prices)<120:
            st.error("Not enough usable price history. Check the symbol and configured sources.")
            st.session_state["agent_v2"]=None
        else:
            report=run_v2(prices,symbol,period,audit=audit_on)
            report.source_validation=source_check(sources)
            st.session_state["agent_v2"]=(report,sources,news)

stored=st.session_state.get("agent_v2")
if stored:
    report,sources,news=stored
    st.success("Research completed. No live orders were sent.")
    s=report.selected
    if s:
        m=s["metrics"]; o=s.get("oos") or {}
        ui.ticker([("Full return",f"{m.get('return_pct',0):+.2f}%",ui.tone(m.get("return_pct",0))),
                   ("Net P&L",f"₹{m.get('net_pnl',0):,.0f}",ui.tone(m.get("net_pnl",0))),
                   ("Trades",m.get("trades",0),None),
                   ("Sharpe",f"{m.get('sharpe_daily'):.2f}" if m.get("sharpe_daily") is not None else "—",None),
                   ("OOS return",f"{o.get('return_pct',0):+.2f}%" if o else "—",ui.tone(o.get('return_pct',0) if o else 0)),
                   ("Max DD",f"{m.get('max_drawdown_pct',0):.2f}%","down")])
        st.markdown(f"### Best research candidate — {s['name']}")
        st.caption(f"Composite score {s['score']:.2f}. OOS evidence is weighted above simple full-history fit.")
        if s.get("audit"):
            a=s["audit"]
            (st.success if a.verdict.startswith("PASSED") else st.warning if a.verdict.startswith("PROMISING") else st.error)(a.verdict)

    st.markdown("### Candidate leaderboard")
    rows=[]
    for c in report.candidates:
        m=c["metrics"]; o=c.get("oos") or {}
        rows.append({"Strategy":c["name"],"Score":round(c["score"],2),"Full Return %":round(float(m.get("return_pct",0)),2),
                      "OOS Return %":round(float(o.get("return_pct",0)),2) if o else None,"OOS Trades":int(o.get("trades",0)) if o else 0,
                      "Win %":round(float(m.get("win_rate_pct") or 0),1),"PF":round(float(m.get("profit_factor") or 0),2),
                      "Max DD %":round(float(m.get("max_drawdown_pct") or 0),2)})
    st.dataframe(pd.DataFrame(rows),width="stretch",hide_index=True)

    st.markdown("### Walk-forward validation")
    if report.windows:
        wrows=[{"Train":f"{w.train_start[:10]} → {w.train_end[:10]}","Test":f"{w.test_start[:10]} → {w.test_end[:10]}",
                "Selected":w.selected,"Train score":round(w.train_score,2),"OOS return %":round(w.oos_return,2),
                "OOS P&L":round(w.oos_pnl,2),"OOS trades":w.oos_trades,"OOS DD %":round(w.oos_dd,2)} for w in report.windows]
        st.dataframe(pd.DataFrame(wrows),width="stretch",hide_index=True)
        good=sum(w.oos_return>0 and w.oos_trades>=5 for w in report.windows)
        msg=f"{good}/{len(report.windows)} unseen windows positive with at least 5 trades."
        (st.success if good/len(report.windows)>=.6 else st.warning)("WALK-FORWARD PROMISING / PAPER TEST ONLY — "+msg if good/len(report.windows)>=.6 else "NOT YET ROBUST — "+msg)
    else: st.warning("Not enough history to form walk-forward windows.")

    st.markdown("### Source validation")
    v=report.source_validation
    st.metric("Cross-source status",v.get("status","—"))
    if v.get("overlap"): st.caption(f"{v['overlap']:,} overlapping observations · mean close difference {v['mean_diff']:.4f}% · max {v['max_diff']:.4f}%")
    for src in sources:
        ui.check_row("PASS" if src.ok else "WARN",src.name,f"{src.rows:,} rows · {src.detail}" if src.ok else src.detail)

    st.markdown("### News context")
    if news:
        for item in news[:12]: st.markdown(f"- **{item.source}** — [{item.title}]({item.url})")
    else: st.caption("No permitted RSS headlines were available.")

    with st.expander("Methodology"):
        st.markdown("Price sources are never blindly averaged. The first usable source is the canonical backtest series and other sources validate overlapping prices. The agent searches EMA, breakout and RSI variants, chooses inside historical training windows, tests the frozen choice on unseen windows, then applies Reality Check stress tests. Upstox requires secure environment secrets; NSE public endpoints may be unavailable when NSE rate-limits automated requests.")
ui.footer_note("Research only · no live orders · backtests and walk-forward results do not guarantee future returns.")
