"""Auto Tester: deterministic parameter-sweep research on fake market worlds."""
import os
import streamlit as st

from algobot import ui
from algobot.learning import learning_summary, research_shortlist, summarize_auto_test
from algobot.auto_tester import build_candidate_grid, build_period_values, estimate_candidate_count, make_candidate
from algobot.config import ConfigError, load_config, validate_config
from algobot.lab import run_lab
from algobot.worlds import REGIMES

ui.setup("Auto Tester", "🤖")
ui.header(
    "Auto Tester",
    "Automatically generate and stress-test deterministic strategy variants. "
    "This stage uses the existing fake-market lab; real-history validation still belongs in Backtest and Reality Check.",
    mode="research:Auto Tester",
)

raw = st.session_state.get("last_raw")
try:
    if raw is not None:
        base_cfg = validate_config(raw)
        st.info("Using the strategy from your last Backtest.")
    else:
        demo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "demo_rules.yaml")
        base_cfg = load_config(demo)
        st.info("Using the demo strategy. Run a Backtest first to search your own strategy.")
except ConfigError as exc:
    st.error(f"The settings are not valid: {exc}")
    st.stop()

indicators = base_cfg.get("strategy", {}).get("params", {}).get("indicators", [])
period_targets = [
    indicator["name"] for indicator in indicators
    if isinstance(indicator, dict) and isinstance(indicator.get("period"), int)
]

st.subheader("1. Build the search space")
st.caption("The tester changes indicator periods and risk settings while keeping entry/exit logic deterministic.")

if period_targets:
    selected = st.multiselect(
        "Indicators to vary", period_targets, default=period_targets[:2], key="auto_indicator_targets"
    )
else:
    selected = []
    st.warning("No period-based indicators were found. You can still sweep stop-loss and target settings.")

c1, c2, c3, c4 = st.columns(4)
period_min = c1.number_input("Period minimum", min_value=2, max_value=200, value=5, step=1)
period_max = c2.number_input("Period maximum", min_value=2, max_value=200, value=30, step=1)
period_step = c3.number_input("Period step", min_value=1, max_value=50, value=5, step=1)
max_candidates = c4.slider("Max candidates", 5, 100, 30, 5)

s1, s2, s3 = st.columns(3)
stop_values = s1.multiselect("Stop-loss %", [0.25, 0.5, 0.75, 1.0, 1.5, 2.0], default=[0.5, 1.0])
target_values = s2.multiselect("Target %", [0.5, 1.0, 1.5, 2.0, 3.0], default=[1.0, 2.0])
worlds = s3.slider("Worlds per regime", 1, 10, 3, key="auto_worlds")

regime_names = st.multiselect("Market regimes", list(REGIMES), default=list(REGIMES), key="auto_regimes")
if not regime_names:
    st.warning("Select at least one market regime.")
    st.stop()

try:
    period_values = build_period_values(int(period_min), int(period_max), int(period_step))
except ValueError as exc:
    st.error(str(exc))
    st.stop()

estimated = estimate_candidate_count(period_values, len(selected), len(stop_values), len(target_values))
st.metric("Candidate combinations before cap", estimated)

if st.button("🤖 Run Auto Tester", type="primary", key="auto_run"):
    candidates = build_candidate_grid(
        period_values, selected, stop_values, target_values, int(max_candidates),
        base_cfg["strategy"]["stop_loss_pct"], base_cfg["strategy"]["target_pct"],
    )

    # The list is registered in session_state before the loop starts (not after it finishes),
    # and every candidate is appended to that same object, so switching pages mid-run keeps
    # whatever was already tested instead of losing the whole run.
    rows = []
    st.session_state["auto_report"] = rows
    progress = st.progress(0, text="Testing candidates...")
    for i, (combo, stop_loss, target) in enumerate(candidates, start=1):
        cfg = make_candidate(base_cfg, selected, combo, stop_loss, target, i)
        report = run_lab(cfg, regime_names, int(worlds), 10, 100, 0)
        by_regime = report.by_regime
        rows.append({
            "candidate": i,
            "periods": ", ".join(str(x) for x in combo) if selected else "unchanged",
            "stop_loss_%": float(stop_loss),
            "target_%": float(target),
            "avg_result_Rs": round(float(by_regime["mean_net"].mean()), 2),
            "profitable_worlds_%": round(float(by_regime["profitable_pct"].mean()), 1),
            "worst_drawdown_Rs": round(float(by_regime["worst_drawdown"].min()), 2),
            "risk_rules_ok": not bool(report.integrity),
        })
        st.session_state["auto_lessons"] = summarize_auto_test(rows)
        progress.progress(i / len(candidates), text=f"Testing candidate {i}/{len(candidates)}")
    progress.empty()

rows = st.session_state.get("auto_report")
if rows:
    import pandas as pd
    result = pd.DataFrame(rows)
    st.subheader("2. Candidate results")
    st.caption("Results are saved as each candidate finishes -- it's safe to switch pages and come back.")
    ui.show_table(result.sort_values(["risk_rules_ok", "avg_result_Rs"], ascending=[False, False]).head(25))
    shortlist = research_shortlist(rows)
    if shortlist:
        st.subheader("Research suggestion")
        suggested = shortlist[0]
        st.info(
            f"Current research candidate to investigate first: candidate {suggested['candidate']}. "
            "This is a test-result shortlist, not a guarantee and not an automatic strategy change."
        )
    lessons = learning_summary()
    if lessons:
        st.subheader("🧠 Learned research warnings")
        ui.show_table(pd.DataFrame(lessons))
    st.info(
        "This is a research shortlist, not a profit guarantee. "
        "A candidate that does well on fake worlds can still fail on real historical data."
    )
    st.subheader("3. Next gate")
    st.markdown(
        "1. Take candidates to **Backtest** on real historical data.\n"
        "2. Use **Reality Check** and out-of-sample periods to test robustness.\n"
        "3. Then use **Test Lab** for additional stress testing.\n"
        "4. Paper trade before considering live execution."
    )

ui.footer_note("Auto Tester uses fake-market stress testing. It never places orders or connects to a broker.")