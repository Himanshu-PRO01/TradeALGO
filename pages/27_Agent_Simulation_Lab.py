"""Synthetic-user Agent Simulation Lab.

MiroFish-inspired bounded simulation for TradeALGO research. It never connects
to brokers, OpenAlgo, live feeds, or browser sessions.
"""
import os

import streamlit as st

from algobot import ui
from algobot.agent_simulation import PROFILES, simulate_agents
from algobot.config import ConfigError, load_config, validate_config

ui.setup("Agent Simulation Lab", "🧬")
ui.header(
    "Agent Simulation Lab",
    "MiroFish-inspired synthetic traders running only against TradeALGO's fake markets.",
    mode="research:Synthetic agents",
)

st.info(
    "Safe research mode: synthetic agents cannot place orders, access broker credentials, "
    "or reach OpenAlgo. Results are stress-test evidence, not trading advice."
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
        st.caption("Using the demo strategy. Run a Backtest first to simulate your own strategy.")
except ConfigError as exc:
    st.error(f"The settings are not valid: {exc}")
    st.stop()

c1, c2 = st.columns(2)
worlds = c1.slider("Fake worlds per agent", 1, 10, 3, key="agent_worlds")
days = c2.slider("Days per world", 2, 20, 8, key="agent_days")

st.markdown("### Synthetic trader profiles")
st.dataframe(
    [
        {
            "profile": p.name.replace("_", " ").title(),
            "risk tolerance": p.risk_tolerance,
            "quantity multiplier": p.quantity_multiplier,
            "target multiplier": p.target_multiplier,
        }
        for p in PROFILES
    ],
    width="stretch",
    hide_index=True,
)

if st.button("🧬 Run agent simulation", type="primary", width="stretch"):
    with st.spinner("Running bounded synthetic traders through fake markets…"):
        st.session_state["agent_report"] = simulate_agents(
            cfg, worlds=worlds, days=days, seed=100
        )

report = st.session_state.get("agent_report")
if report:
    a, b, c, d = st.columns(4)
    a.metric("Synthetic runs", len(report.agents))
    b.metric("Average P&L", f"₹{report.mean_pnl:,.0f}")
    c.metric("Profitable runs", f"{report.profitable_pct:.0f}%")
    d.metric("Risk failures", report.risk_failures)

    rows = [
        {
            "agent": r.profile.replace("_", " ").title(),
            "P&L": round(r.pnl, 2),
            "trades": r.trades,
            "max drawdown": round(r.drawdown, 2),
            "risk": "PASS" if r.risk_ok else "FAIL",
        }
        for r in report.agents
    ]
    ui.show_table(rows)

    if report.risk_failures:
        st.warning("Some synthetic runs violated a configured risk rule. Investigate before paper testing.")
    else:
        st.success("No configured risk-rule violations were found in these synthetic runs.")

    st.caption(
        "Synthetic personas are bounded test profiles. They do not learn from real users, "
        "predict markets, or grant themselves execution access."
    )

ui.footer_note("Research only · synthetic users · fake markets · no broker execution")
