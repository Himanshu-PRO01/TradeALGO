"""Safe synthetic swarm lab: adaptive strategy stress testing + social market simulation."""
import os
import streamlit as st

from algobot import ui
from algobot.config import ConfigError, load_config, validate_config
from algobot.synthetic_swarm import PERSONAS, SAFE_WEB_PAGES, run_swarm, plan_journey
from algobot.mirofish_sim import agent_chat, run_mirofish
from algobot.agent_research import run_agent_research

ui.setup("Swarm Simulation Lab", "🧬")
ui.header(
    "Swarm Simulation Lab",
    "Adaptive agents, social debate, memory, knowledge graph and safe website journeys.",
    mode="research:Swarm only",
)
st.info(
    "Safety boundary: everything here is synthetic. Agents cannot place live orders, "
    "access broker credentials, or reach OpenAlgo."
)

raw = st.session_state.get("last_raw")
try:
    if raw is not None:
        cfg = validate_config(raw)
        st.success("Using the strategy from your latest Backtest.")
    else:
        demo = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "configs",
            "demo_rules.yaml",
        )
        cfg = load_config(demo)
        st.caption("Using the demo strategy. Run a Backtest first to test your own strategy.")
except ConfigError as exc:
    st.error(f"The settings are not valid: {exc}")
    st.stop()

st.markdown("## 1. Adaptive strategy swarm")
a, b, c = st.columns(3)
agent_count = a.slider("Synthetic agents", 2, 32, 8)
rounds = b.slider("Adaptive rounds", 1, 12, 4)
days = c.slider("Days per round", 2, 20, 8)

if st.button("🧬 Run adaptive strategy swarm", type="primary", width="stretch"):
    with st.spinner("Running agents through changing synthetic worlds…"):
        st.session_state["swarm_report"] = run_swarm(
            cfg, agents=agent_count, rounds=rounds, days_per_round=days, seed=700
        )

report = st.session_state.get("swarm_report")
if report:
    x, y, z, w = st.columns(4)
    x.metric("Agent episodes", report.episodes)
    y.metric("Average P&L", f"₹{report.mean_pnl:,.0f}")
    z.metric("Profitable episodes", f"{report.profitable_pct:.0f}%")
    w.metric("Risk failures", report.risk_failures)
    st.dataframe(
        [
            {
                "agent": ag.id,
                "persona": ag.persona.name,
                "score": round(ag.score, 3),
                "strategy belief": round(ag.memory.beliefs["strategy_quality"], 3),
                "risk belief": round(ag.memory.beliefs["risk_safety"], 3),
                "trend belief": round(ag.memory.beliefs["trend_preference"], 3),
                "rounds remembered": len(ag.memory.observations),
            }
            for ag in report.agents
        ],
        width="stretch",
        hide_index=True,
    )
    if report.failure_modes:
        st.warning("Swarm findings: " + "; ".join(report.failure_modes))
    else:
        st.success("No swarm-level failure mode was detected in this bounded experiment.")

st.markdown("## 2. Social market simulation")
st.caption(
    "This layer adds a synthetic event/news world, agent-to-agent debate, persistent memory, "
    "influence edges and a local knowledge graph. It is independent of live execution."
)
d, e, f = st.columns(3)
social_agents = d.slider("Social agents", 2, 24, 8, key="social_agents")
ticks = e.slider("Simulation ticks", 4, 60, 24, key="social_ticks")
strategy_score = f.slider("Strategy evidence", 0.0, 1.0, 0.50, 0.05, key="strategy_evidence")
risk_score = st.slider("Risk evidence", 0.0, 1.0, 0.50, 0.05, key="risk_evidence")

if st.button("🌐 Run social market world", type="primary", width="stretch"):
    with st.spinner("Agents are reading synthetic events, debating and updating memory…"):
        st.session_state["mirofish_result"] = run_mirofish(
            agents=social_agents,
            ticks=ticks,
            seed=700,
            strategy_score=strategy_score,
            risk_score=risk_score,
        )

mf = st.session_state.get("mirofish_result")
if mf:
    social_report, social_cohort, social_messages, social_graph, social_events = mf
    x, y, z, w = st.columns(4)
    x.metric("Events", social_report.events)
    y.metric("Agent messages", social_report.messages)
    z.metric("Graph nodes", social_report.graph_nodes)
    w.metric("Graph edges", social_report.graph_edges)

    st.markdown("### Collective belief")
    q, r, s = st.columns(3)
    q.metric("Consensus", f"{social_report.consensus:+.2f}")
    r.metric("Consensus strength", f"{social_report.consensus_strength:.2f}")
    s.metric("Mean strategy belief", f"{social_report.mean_strategy_belief:.2f}")

    st.markdown("### Agent state + memory")
    st.dataframe(
        [
            {
                "agent": ag.agent_id,
                "role": ag.persona.role,
                "stance": round(ag.stance, 2),
                "sim P&L": round(ag.pnl, 2),
                "strategy belief": round(ag.memory.beliefs["strategy_quality"], 2),
                "risk belief": round(ag.memory.beliefs["risk_safety"], 2),
                "memories": len(ag.memory.observations),
                "messages": ag.messages,
            }
            for ag in social_cohort
        ],
        width="stretch",
        hide_index=True,
    )

    with st.expander("Recent synthetic debate", expanded=False):
        st.dataframe(
            [
                {
                    "tick": m.tick,
                    "sender": m.sender,
                    "recipient": m.recipient,
                    "stance": round(m.stance, 2),
                    "message": m.text,
                }
                for m in social_messages[-30:]
            ],
            width="stretch",
            hide_index=True,
        )

    st.markdown("### Post-simulation agent chat")
    selected = st.selectbox(
        "Choose an agent",
        options=[ag.agent_id for ag in social_cohort],
        key="chat_agent",
    )
    question = st.text_input(
        "Ask the simulated agent about its evidence, risk view or disagreement",
        placeholder="Why did you become bullish?",
        key="chat_question",
    )
    if st.button("💬 Ask agent", key="ask_agent"):
        selected_agent = next(ag for ag in social_cohort if ag.agent_id == selected)
        st.write(agent_chat(selected_agent, question, social_graph))

    if social_report.failure_modes:
        st.warning("Simulation findings: " + "; ".join(social_report.failure_modes))
    st.markdown("### Research report")
    for finding in social_report.key_findings:
        st.write("• " + finding)

st.markdown("## 3. Autonomous research agents")
st.caption(
    "These agents do the actual research work: generate bounded strategy mutations, "
    "run them across synthetic Indian-market regimes, critique failures, keep survivors, "
    "and validate the finalists on an untouched holdout world. No live orders."
)
g1, g2, g3 = st.columns(3)
research_generations = g1.slider("Research generations", 1, 8, 4, key="research_generations")
research_per_agent = g2.slider("Candidates per agent", 1, 4, 2, key="research_per_agent")
research_days = g3.slider("Synthetic days / world", 2, 15, 8, key="research_days")

if st.button("🤖 Let agents do the research", type="primary", width="stretch"):
    with st.spinner("Agents are generating, testing, rejecting and mutating strategies…"):
        st.session_state["agent_research"] = run_agent_research(
            cfg,
            generations=research_generations,
            candidates_per_agent=research_per_agent,
            days=research_days,
            seed=1701,
        )

ar = st.session_state.get("agent_research")
if ar:
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Candidates tested", ar.candidates_tested)
    a2.metric("Generations", ar.generations)
    a3.metric("Winner", ar.winner_id or "None")
    a4.metric("Verdict", ar.verdict)
    st.dataframe(
        [
            {
                "candidate": s.candidate_id,
                "gen": s.generation,
                "train P&L": round(s.train_pnl, 2),
                "holdout P&L": round(s.holdout_pnl, 2),
                "train PF": round(s.train_pf, 2),
                "holdout PF": round(s.holdout_pf, 2),
                "holdout DD": round(s.holdout_dd, 2),
                "robustness": round(s.robustness, 3),
                "accepted": s.accepted,
                "reasons": "; ".join(s.reasons),
            }
            for s in sorted(ar.scores, key=lambda x: x.robustness, reverse=True)[:30]
        ],
        width="stretch",
        hide_index=True,
    )
    for finding in ar.findings:
        st.write("• " + finding)
    if ar.winner_cfg:
        st.success(
            "Agents produced a research candidate, but it is NOT cleared for live trading. "
            "Run it on real out-of-sample Indian data and the Reality Check before considering paper trading."
        )

st.markdown("## 3. Synthetic website journeys")
st.caption(
    "The planner is allow-listed. The next QA layer can execute these plans with Streamlit "
    "AppTest and record UI exceptions, visible errors and repeated failures."
)
st.dataframe(
    [
        {
            "persona": p.name.replace("_", " ").title(),
            "planned safe pages": " → ".join(plan_journey(p)),
        }
        for p in PERSONAS
    ],
    width="stretch",
    hide_index=True,
)
st.caption("Allowed journey pages: " + ", ".join(SAFE_WEB_PAGES))
ui.footer_note("Research only · synthetic agents · fake markets · no broker execution")
