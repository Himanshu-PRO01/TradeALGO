"""TradeALGO Market Research Agent v2."""
import datetime as dt
import pandas as pd
import streamlit as st
from algobot import ui
from algobot.market_agent import fetch_news, fetch_yfinance, fetch_openalgo, merge_sources
from algobot.market_agent_v2 import run_v2, source_check

ui.setup("Market Research Agent","🧠")
ui.header("Market Research Agent","Multi-source → parameter search → walk-forward → reality check. Research only; no orders.","research:Agent")

with st.expander("What the agent now does",expanded=True):
    st.markdown("**v2** validates available price sources, searches a bounded set of transparent strategy parameters, selects parameters only inside training windows, evaluates the next unseen window, and reality-checks the strongest candidates. News is context/provenance only; it is never used as a future-price label.")

c1,c2,c3,c4=st.columns(4)
with c1: symbol=st.text_input("Symbol","NIFTY",help="Examples: NIFTY, RELIANCE.NS, TCS.NS")
with c2: period=st.selectbox("History",["6mo","1y","2y","5y"],index=2)
with c3: interval=st.selectbox("Interval",["1d"],index=0)
with c4: audit_on=st.toggle("Reality check",True)

if st.button("🧠 Run Market Research Agent v2",type="primary",width="stretch"):
    with st.spinner("Collecting sources, searching parameters and running walk-forward tests..."):
        today=dt.date.today()
        years={"6mo":1,"1y":1,"2y":2,"5y":5}[period]
        sources=[fetch_yfinance(symbol,period=period,interval=interval)]
        sources.append(fetch_openalgo(symbol.replace(".NS","").replace(".BO",""),
                                      (today-dt.timedelta(days=365*years)).isoformat(),
                                      today.isoformat(),"D"))
        prices=merge_sources(sources)
        news=fetch_news(limit=6)
        if prices is None or len(prices)<120:
            st.error("Not enough usable price history. Check the symbol and configured data sources.")
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
        ui.ticker([
            ("Full return",f"{m.get('return_pct',0):+.2f}%",ui.tone(m.get("return_pct",0))),
            ("Net P&L",f"₹{m.get('net_pnl',0):,.0f}",ui.tone(m.get("net_pnl",0))),
            ("Trades",m.get("trades",0),None),
            ("Sharpe",f"{m.get('sharpe_daily'):.2f}" if m.get("sharpe_daily") is not None else "—",None),
            ("OOS return",f"{o.get('return_pct',0):+.2f}%" if o else "—",ui.tone(o.get("return_pct",0) if o else 0)),
            ("Max DD",f"{m.get('max_drawdown_pct',0):.2f}%","down")])
        st.markdown("### Best research candidate")
        st.markdown(f"**{s['name']}**")
        st.caption(f"Composite research score: {s['score']:.2f}. Full-history metrics are descriptive; walk-forward OOS results carry more weight.")
        if s.get("audit"):
            a=s["audit"]
            if a.verdict.startswith("PASSED"): st.success(a.verdict)
            elif a.verdict.startswith("PROMISING"): st.warning(a.verdict)
            else: st.error(a.verdict)

    st.markdown("### Candidate leaderboard")
    rows=[]
    for c in report.candidates:
        m=c["metrics"]; o=c.get("oos") or {}
        rows.append({"Strategy":c["name"],"Score":round(c["score"],2),"Full Return %":round(float(m.get("return_pct",0)),2),
                      "OOS Return %":round(float(o.get("return_pct",0)),2) if o else None,
                      "OOS Trades":int(o.get("trades",0)) if o else 0,
                      "Win %":round(float(m.get("win_rate_pct") or 0),1),
                      "PF":round(float(m.get("profit_factor") or 0),2),
                      "Max DD %":round(float(m.get("max_drawdown_pct") or 0),2)})
    st.dataframe(pd.DataFrame(rows),width="stretch",hide_index=True)

    st.markdown("### Walk-forward validation")
    if report.windows:
        wf_rows=[{"Train":f"{w.train_start[:10]} → {w.train_end[:10]}","Test":f"{w.test_start[:10]} → {w.test_end[:10]}",
                  "Selected":w.selected,"Train score":round(w.train_score,2),"OOS return %":round(w.oos_return,2),
                  "OOS P&L":round(w.oos_pnl,2),"OOS trades":w.oos_trades,"OOS DD %":round(w.oos_dd,2)} for w in report.windows]
        st.dataframe(pd.DataFrame(wf_rows),width="stretch",hide_index=True)
        positive=sum(w.oos_return>0 and w.oos_trades>=5 for w in report.windows)
        verdict="WALK-FORWARD PROMISING / PAPER TEST ONLY" if positive/len(report.windows)>=.6 else "NOT YET ROBUST"
        (st.success if "PROMISING" in verdict else st.warning)(f"{verdict} — {positive}/{len(report.windows)} unseen windows were positive with at least 5 trades.")
    else:
        st.warning("Walk-forward could not form enough train/test windows for this history.")

    st.markdown("### Source validation")
    v=report.source_validation
    st.metric("Source status",v.get("status","—"))
    if v.get("overlap"): st.caption(f"{v['overlap']:,} overlapping observations · mean close difference {v['mean_diff']:.4f}% · max {v['max_diff']:.4f}%")
    for src in sources:
        ui.check_row("PASS" if src.ok else "WARN",src.name,f"{src.rows:,} rows · {src.detail}" if src.ok else src.detail)

    st.markdown("### News context")
    if news:
        for item in news[:12]:
            st.markdown(f"- **{item.source}** — [{item.title}]({item.url})")
    else: st.caption("No permitted RSS headlines were available.")

    with st.expander("Research methodology"):
        st.markdown("1. Fetch price history from available providers. 2. Compare overlapping close prices rather than blindly merging feeds. 3. Search a bounded EMA, breakout and RSI parameter space. 4. For each walk-forward window, choose only from the training segment. 5. Test that frozen choice on the next unseen segment. 6. Reality-check only the strongest full-history candidates for costs, random-entry comparison, stability, parameter fragility, concentration and Monte Carlo ruin risk. 7. Treat the output as a hypothesis and paper-trade before any live integration.")

ui.footer_note("Research agent only · no live orders · backtest and walk-forward results do not guarantee future returns.")
