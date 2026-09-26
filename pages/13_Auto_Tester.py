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
        ui.banner("Using the strategy from your last Backtest.", "info")
    else:
        demo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "demo_rules.yaml")
        base_cfg = load_config(demo)
        ui.banner("Using the demo strategy. Run a Backtest first to search your own strategy.", "warning", "⚠️")
except ConfigError as exc:
    ui.banner(f"The settings are not valid: {exc}", tone="red", icon="🚨")
    st.stop()

indicators = base_cfg.get("strategy", {}).get("params", {}).get("indicators", [])
period_targets = [
    indicator["name"] for indicator in indicators
    if isinstance(indicator, dict) and isinstance(indicator.get("period"), int)
]

st.markdown("### 1. Select indicators")
st.caption("The tester changes indicator periods and risk settings while keeping entry/exit logic deterministic.")

if period_targets:
    selected = st.multiselect(
        "Indicators to vary", period_targets, default=period_targets[:2], key="auto_indicator_targets"
    )
else:
    selected = []
    ui.banner("No period-based indicators were found. You can still sweep stop-loss and target settings.", "warning", "⚠️")

st.markdown("### 2. Define parameter ranges")
c1, c2, c3, c4 = st.columns(4)
period_min = c1.number_input("Period minimum", min_value=2, max_value=200, value=5, step=1)
period_max = c2.number_input("Period maximum", min_value=2, max_value=200, value=30, step=1)
period_step = c3.number_input("Period step", min_value=1, max_value=50, value=5, step=1)
max_candidates = c4.slider("Max candidates", 5, 100, 30, 5)

st.markdown("### 3. Define stop/target ranges")
s1, s2, s3 = st.columns(3)
stop_values = s1.multiselect("Stop-loss %", [0.25, 0.5, 0.75, 1.0, 1.5, 2.0], default=[0.5, 1.0])
target_values = s2.multiselect("Target %", [0.5, 1.0, 1.5, 2.0, 3.0], default=[1.0, 2.0])
worlds = s3.slider("Worlds per regime", 1, 10, 3, key="auto_worlds")

regime_names = st.multiselect("Market regimes", list(REGIMES), default=list(REGIMES), key="auto_regimes")
if not regime_names:
    ui.banner("Select at least one market regime.", tone="warn", icon="⚠️")
    st.stop()

try:
    period_values = build_period_values(int(period_min), int(period_max), int(period_step))
except ValueError as exc:
    ui.banner(str(exc), tone="red", icon="🚨")
    st.stop()

st.markdown("### 4. Generate candidates")
estimated = estimate_candidate_count(period_values, len(selected), len(stop_values), len(target_values))
ui.ticker([("Estimated Candidates", str(estimated), "blue")])

st.markdown("### 5. Test candidates")
if st.button("🤖 Run Auto Tester", type="primary", key="auto_run"):
    candidates = build_candidate_grid(
        period_values, selected, stop_values, target_values, int(max_candidates),
        base_cfg["strategy"]["stop_loss_pct"], base_cfg["strategy"]["target_pct"],
    )

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
    st.markdown("### 6. Review evidence")
    st.caption("Results are saved as each candidate finishes -- it's safe to switch pages and come back.")
    
    # Custom HTML table rendering with badges
    html_table = "<table style='width:100%; border-collapse:collapse; font-size:0.85rem;'>"
    html_table += "<tr style='border-bottom:1px solid #1E293B; text-align:left; color:#94A3B8;'>"
    html_table += "<th style='padding:8px;'>ID</th><th style='padding:8px;'>Parameters</th><th style='padding:8px;'>Avg Result</th><th style='padding:8px;'>Win %</th><th style='padding:8px;'>Max DD</th><th style='padding:8px;'>Risk Status</th><th style='padding:8px;'>Research Status</th></tr>"
    
    # Sort for best candidates first
    sorted_rows = sorted(rows, key=lambda x: (x["risk_rules_ok"], x["avg_result_Rs"]), reverse=True)[:25]
    
    for r in sorted_rows:
        id_str = f"#{r['candidate']}"
        params = f"{r['periods']} (SL: {r['stop_loss_%']}%, TGT: {r['target_%']}%)"
        avg_res = f"₹{r['avg_result_Rs']}"
        prof_pct = f"{r['profitable_worlds_%']}%"
        worst_dd = f"₹{r['worst_drawdown_Rs']}"
        
        if r["risk_rules_ok"]:
            risk_badge = ui.badge("PASS", "green")
            if r["avg_result_Rs"] > 0 and r["profitable_worlds_%"] > 50:
                res_badge = ui.badge("Needs Validation", "blue")
            else:
                res_badge = ui.badge("Robustness Review", "amber")
        else:
            risk_badge = ui.badge("FAIL", "red")
            res_badge = ui.badge("Risk Check Failed", "red")
            
        html_table += f"<tr style='border-bottom:1px solid #1E293B;'><td style='padding:8px; font-weight:600;'>{id_str}</td><td style='padding:8px;'>{params}</td><td style='padding:8px;'>{avg_res}</td><td style='padding:8px;'>{prof_pct}</td><td style='padding:8px;'>{worst_dd}</td><td style='padding:8px;'>{risk_badge}</td><td style='padding:8px;'>{res_badge}</td></tr>"
    html_table += "</table>"
    
    st.markdown(html_table, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    shortlist = research_shortlist(rows)
    if shortlist:
        suggested = shortlist[0]
        ui.banner(f"Current research candidate to investigate first: candidate {suggested['candidate']}. This is a test-result shortlist, not a guarantee and not an automatic strategy change.", "info", "🔍")
        
    lessons = learning_summary()
    if lessons:
        st.markdown("### Learning Memory")
        for less in lessons:
            obs = {
                "Evidence": less.get("evidence", ""),
                "Occurrences": f"{less.get('occurrences', 1)}×"
            }
            ui.learning_memory(obs, confidence=less.get("confidence", "low").title(), action=less.get("action", "observe"))

    ui.banner("This is a research shortlist, not a profit guarantee. A candidate that does well on fake worlds can still fail on real historical data.", "warning", "⚠️")

    st.markdown("### 7. Send candidate to Backtest / Reality Check")
    a, b = st.columns(2)
    with a:
        st.markdown(ui.card("Backtest", "Test your top candidates against real historical data.", "📊"), unsafe_allow_html=True)
        st.page_link("pages/5_Backtest.py", label="Run Backtest", icon="📊")
    with b:
        st.markdown(ui.card("Reality Check", "Use out-of-sample periods to test robustness.", "🛡️"), unsafe_allow_html=True)
        st.page_link("pages/6_Reality_check.py", label="Run Reality Check", icon="🛡️")

ui.footer_note("Auto Tester uses fake-market stress testing. It never places orders or connects to a broker.")
