"""Stress lab: run a strategy through many kinds of fake market, instantly, for free."""
import os

import streamlit as st

from algobot import ui
from algobot.charts import pnl_bars
from algobot.config import ConfigError, load_config, validate_config
from algobot.lab import run_lab
from algobot.worlds import REGIMES

ui.setup("Test lab", "🧪")
ui.header("Test lab: many fake markets, instantly", "Runs your strategy through as many made-up markets as you like (trending, "
          "choppy, crashing, jumpy...) with your real costs and risk rules. It shows where the strategy earns, where it loses, "
          "and whether its safety rules held. It also runs a cheating test. The prices are made up: this shows how a strategy "
          "BEHAVES, never what will make money.", mode="research:Fake markets")

raw = st.session_state.get("last_raw")
try:
    if raw is not None:
        cfg = validate_config(raw)
        st.info("Testing the strategy from your last backtest on the Backtest page.")
    else:
        demo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "demo_rules.yaml")
        cfg = load_config(demo)
        st.info("Testing the demo strategy. Run a backtest on the Backtest page to test your own instead.")
except ConfigError as exc:
    st.error(f"The settings are not valid: {exc}")
    st.stop()

c1, c2, c3 = st.columns(3)
worlds = c1.slider("Worlds per market type", 3, 20, 6, key="lab_worlds")
days = c2.slider("Days per world", 5, 30, 12, key="lab_days")
control = c3.slider("Worlds for the cheating test (0 = skip)", 0, 60, 20, key="lab_control")
chosen = st.multiselect("Market types", list(REGIMES), default=list(REGIMES), key="lab_regimes",
                        help="; ".join(f"{r.name}: {r.description}" for r in REGIMES.values()))
if not chosen:
    st.warning("Pick at least one market type.")
    st.stop()

if st.button("Run the stress lab", type="primary", key="lab_run"):
    with st.spinner("Building fake worlds and testing..."):
        st.session_state["lab_report"] = run_lab(cfg, chosen, int(worlds), int(days), 100, int(control))

report = st.session_state.get("lab_report")
if report is not None:
    st.subheader("Where the strategy earns and where it loses")
    st.markdown("##### Average result per world, by kind of market (Rs)")
    ui.show_chart(pnl_bars(report.by_regime["mean_net"], height=240, title="average result (Rs)"))
    table = report.by_regime.rename(columns={
        "worlds": "worlds", "profitable_pct": "profitable %", "mean_net": "average result (Rs)",
        "worst_net": "worst world (Rs)", "mean_trades": "avg trades", "worst_day": "worst day (Rs)",
        "worst_drawdown": "worst drawdown (Rs)"}).round(0)
    ui.show_table(table)
    for line in report.insights:
        st.write(line)
    if report.integrity:
        st.error("Risk rules broken in some worlds: " + "; ".join(report.integrity))
    else:
        st.success("Risk rules held in every world: nothing overnight, trade limits kept, daily loss within twice the limit.")
    if report.control:
        (st.error if report.control["suspicious"] else st.success)("Cheating test: " + report.control["text"])
    st.caption("Made-up markets: tuning your strategy until it wins here would only teach it to fit noise.")
ui.footer_note()
