"""Full synthetic swarm lab: adaptive agents + website journey planning."""
import os
import streamlit as st

from algobot import ui
from algobot.config import ConfigError, load_config, validate_config
from algobot.synthetic_swarm import PERSONAS, SAFE_WEB_PAGES, run_swarm, plan_journey

ui.setup("Swarm Simulation Lab", "🧬")
ui.header("Swarm Simulation Lab",
          "Adaptive MiroFish-style agents stress-testing strategies and safe product journeys.",
          mode="research:Swarm only")
st.info("Safety boundary: agents use fake markets and an allow-list of research pages. They cannot place live orders, access broker credentials, or reach OpenAlgo.")

raw=st.session_state.get("last_raw")
try:
    if raw is not None:
        cfg=validate_config(raw)
        st.success("Using the strategy from your latest Backtest.")
    else:
        demo=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"configs","demo_rules.yaml")
        cfg=load_config(demo)
        st.caption("Using the demo strategy. Run a Backtest first to test your own strategy.")
except ConfigError as exc:
    st.error(f"The settings are not valid: {exc}")
    st.stop()

a,b,c=st.columns(3)
agent_count=a.slider("Synthetic agents",2,32,8)
rounds=b.slider("Adaptive rounds",1,12,4)
days=c.slider("Days per round",2,20,8)

st.markdown("### Agent population")
st.dataframe([{
    "persona":p.name.replace("_"," ").title(),
    "goal":p.goal,
    "risk tolerance":p.risk_tolerance,
    "patience":p.patience,
    "exploration":p.exploration,
} for p in PERSONAS], width="stretch", hide_index=True)

if st.button("🧬 Run adaptive swarm",type="primary",width="stretch"):
    with st.spinner("Running agents through changing synthetic worlds…"):
        st.session_state["swarm_report"]=run_swarm(cfg,agents=agent_count,rounds=rounds,days_per_round=days,seed=700)

report=st.session_state.get("swarm_report")
if report:
    x,y,z,w=st.columns(4)
    x.metric("Agent episodes",report.episodes)
    y.metric("Average P&L",f"₹{report.mean_pnl:,.0f}")
    z.metric("Profitable episodes",f"{report.profitable_pct:.0f}%")
    w.metric("Risk failures",report.risk_failures)

    st.markdown("### Collective belief")
    st.dataframe([{
        "belief":k.replace("_"," ").title(),
        "swarm confidence":round(v*100,1)
    } for k,v in report.consensus.items()],width="stretch",hide_index=True)

    st.markdown("### Agent memory and adaptation")
    rows=[]
    for agent in report.agents:
        rows.append({
            "agent":agent.id,
            "persona":agent.persona.name,
            "score":round(agent.score,3),
            "strategy belief":round(agent.memory.beliefs["strategy_quality"],3),
            "risk belief":round(agent.memory.beliefs["risk_safety"],3),
            "trend belief":round(agent.memory.beliefs["trend_preference"],3),
            "rounds remembered":len(agent.memory.observations),
            "failures":len(agent.memory.failures),
        })
    ui.show_table(rows)

    if report.failure_modes:
        st.warning("Swarm findings: "+"; ".join(report.failure_modes))
    else:
        st.success("No swarm-level failure mode was detected in this bounded experiment.")

st.markdown("### Synthetic website journeys")
st.caption("The journey planner is intentionally allow-listed. The next QA layer can execute these journeys with Streamlit AppTest and record UI failures.")
st.dataframe([{
    "persona":p.name.replace("_"," ").title(),
    "planned safe pages":" → ".join(plan_journey(p)),
} for p in PERSONAS],width="stretch",hide_index=True)
st.caption("Allowed journey pages: "+", ".join(SAFE_WEB_PAGES))
ui.footer_note("Research only · adaptive synthetic agents · fake markets · no broker execution")
