"""Auto Tester: parameter-sweep candidates through the existing stress-test engine.

This is a research tool. It searches deterministic parameter combinations and scores
them on made-up market worlds. It does not claim that a candidate will be profitable
on real market history.
"""
import copy
import itertools
import os

import streamlit as st

from algobot import ui
from algobot.config import ConfigError, load_config, validate_config
from algobot.lab import run_lab
from algobot.worlds import REGIMES

ui.setup("Auto Tester", "🤖")
ui.header(
    "Auto Tester",
    "Automatically generate and stress-test many deterministic strategy variants. "
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

params = base_cfg.get("strategy", {}).get("params", {})
indicators = params.get("indicators", [])

period_targets = []
for indicator in indicators:
    if isinstance(indicator, dict) and isinstance(indicator.get("period"), int):
        period_targets.append(indicator["name"])

st.subheader("1. Build the search space")
st.caption("The tester changes indicator periods and risk settings while keeping the entry/exit logic deterministic.")

if period_targets:
    selected = st.multiselect(
        "Indicators to vary",
        period_targets,
        default=period_targets[:2],
        key="auto_indicator_targets",
    )
else:
    selected = []
    st.warning("No period-based indicators were found in this strategy. You can still sweep stop-loss and target settings.")

c1, c2, c3, c4 = st.columns(4)
period_min = c1.number_input("Period minimum", min_value=2, max_value=200, value=5, step=1)
period_max = c2.number_input("Period maximum", min_value=2, max_value=200, value=30, step=1)
period_step = c3.number_input("Period step", min_value=1, max_value=50, value=5, step=1)
max_candidates = c4.slider("Max candidates", 5, 100, 30, 5)

s1, s2, s3 = st.columns(3)
stop_values = s1.multiselect("Stop-loss %", [0.25, 0.5, 0.75, 1.0, 1.5, 2.0], default=[0.5, 1.0])
target_values = s2.multiselect("Target %", [0.5, 1.0, 1.5, 2.0, 3.0], default=[1.0, 2.0])
worlds = s3.slider("Worlds per regime", 1, 10, 3, key="auto_worlds")

regime_names = st.multiselect(
    "Market regimes",
    list(REGIMES),
    default=list(REGIMES),
    key="auto_regimes",
)

if not regime_names:
    st.warning("Select at least one market regime.")
    st.stop()

if period_min > period_max:
    st.error("Period minimum must be less than or equal to period maximum.")
    st.stop()

period_values = list(range(int(period_min), int(period_max) + 1, int(period_step)))
if not period_values:
    st.error("The period range produced no values.")
    st.stop()

estimated = max(1, len(period_values) ** max(1, len(selected))) * max(1, len(stop_values)) * max(1, len(target_values))
st.metric("Candidate combinations before cap", estimated)

def make_candidate(period_combo, stop_loss, target):
    cfg = copy.deepcopy(base_cfg)
    cfg["name"] = f"auto_{len(period_combo)}_{stop_loss}_{target}"
    cfg["strategy"]["stop_loss_pct"] = float(stop_loss)
    cfg["strategy"]["target_pct"] = float(target)
    lookup = dict(zip(selected, period_combo))
    for indicator in cfg["strategy"]["params"].get("indicators", []):
        if indicator.get("name") in lookup:
            indicator["period"] = int(lookup[indicator["name"]])
    return validate_config(cfg)

if st.button("🤖 Run Auto Tester", type="primary", key="auto_run"):
    candidates = []
    combos = itertools.product(period_values, repeat=max(1, len(selected)))
    for combo in combos:
        for stop_loss in (stop_values or [base_cfg["strategy"]["stop_loss_pct"] or 0.5]):
            for target in (target_values or [base_cfg["strategy"]["target_pct"] or 1.0]):
                candidates.append((combo, stop_loss, target))
                if len(candidates) >= int(max_candidates):
                    break
            if len(candidates) >= int(max_candidates):
                break
        if len(candidates) >= int(max_candidates):
            break

    rows = []
    progress = st.progress(0, text="Testing candidates...")
    for i, (combo, stop_loss, target) in enumerate(candidates, start=1):
        cfg = make_candidate(combo, stop_loss, target)
        report = run_lab(cfg, regime_names, int(worlds), 10, 100, 0)
        by_regime = report.by_regime
        mean_net = float(by_regime["mean_net"].mean())
        profitable_pct = float(by_regime["profitable_pct"].mean())
        worst_drawdown = float(by_regime["worst_drawdown"].min())
        integrity_ok = not bool(report.integrity)
        rows.append({
            "candidate": i,
            "periods": ", ".join(str(x) for x in combo) if selected else "unchanged",
            "stop_loss_%": float(stop_loss),
            "target_%": float(target),
            "avg_result_Rs": round(mean_net, 2),
            "profitable_worlds_%": round(profitable_pct, 1),
            "worst_drawdown_Rs": round(worst_drawdown, 2),
            "risk_rules_ok": integrity_ok,
        })
        progress.progress(i / len(candidates), text=f"Testing candidate {i}/{len(candidates)}")
    progress.empty()
    st.session_state["auto_report"] = rows

rows = st.session_state.get("auto_report")
if rows:
    import pandas as pd

    result = pd.DataFrame(rows)
    st.subheader("2. Candidate results")
    ui.show_table(result.sort_values(["risk_rules_ok", "avg_result_Rs"], ascending=[False, False]).head(25))

    st.info(
        "This table is a research shortlist, not a profit ranking. "
        "A candidate that does well on fake worlds can still fail on real historical data."
    )
    st.subheader("3. Next gate")
    st.markdown(
        "1. Take candidates back to **Backtest** on real historical data.\n"
        "2. Use **Reality Check** and out-of-sample periods to test robustness.\n"
        "3. Then use **Test Lab** for additional stress testing.\n"
        "4. Paper trade before considering any live execution."
    )

ui.footer_note("Auto Tester uses fake-market stress testing. It never places orders or connects to a broker.")
