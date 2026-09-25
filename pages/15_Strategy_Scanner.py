"""Strategy Scanner: run a whole library of strategy templates against real
(or sample) price data and rank them -- a wider version of Auto Tester that
searches across strategy FAMILIES, not just one strategy's parameters.
"""
import io

import pandas as pd
import streamlit as st

from algobot import ui
from algobot.auto_tester import build_scanner_candidates, estimate_scanner_count, rank_scanner_rows, score_result
from algobot.config import validate_config
from algobot.data import generate_sample_data, load_csv, DataError
from algobot.engine import run_backtest
from algobot.strategy import build_strategy
from algobot.strategy_library import TEMPLATES

ui.setup("Strategy Scanner", "🔬")
ui.header(
    "Strategy Scanner",
    "Systematically test a whole library of strategy templates -- crossovers, mean-reversion, "
    "breakouts -- against real price data, and rank what actually held up. No search is truly "
    "infinite; this one is wide and bounded so it finishes in a reasonable time.",
    mode="research:Strategy Scanner",
)

st.subheader("1. Data to test on")
prices = st.session_state.get("last_prices")
source = st.radio(
    "Price data",
    ["Use data from my last Backtest", "Upload a CSV", "Generate sample data"],
    index=0 if prices is not None else 2,
    horizontal=True,
)
if source == "Use data from my last Backtest":
    if prices is None:
        st.warning("No data from a previous Backtest run yet. Run **Backtest** once first, or pick another source.")
        st.stop()
    df = prices
elif source == "Upload a CSV":
    uploaded = st.file_uploader("OHLCV CSV (needs a time column plus open, high, low, close)", type="csv")
    if uploaded is None:
        st.stop()
    try:
        df = load_csv(io.BytesIO(uploaded.getvalue()))
    except DataError as exc:
        st.error(str(exc))
        st.stop()
else:
    days = st.slider("Sample days", 10, 120, 40)
    df = generate_sample_data(days=days, seed=42)
    st.caption("Synthetic random-walk data. Useful for checking the scanner mechanics, not for judging any strategy.")

st.caption(f"Testing on {len(df):,} bars, {df.index.date.min()} to {df.index.date.max()}.")

st.subheader("2. Strategy families to test")
template_keys = st.multiselect(
    "Templates",
    list(TEMPLATES),
    default=list(TEMPLATES),
    format_func=lambda k: TEMPLATES[k].label,
)
if not template_keys:
    st.warning("Select at least one strategy family.")
    st.stop()
with st.expander("What each template does"):
    for k in template_keys:
        st.markdown(f"**{TEMPLATES[k].label}** — {TEMPLATES[k].description}")

c1, c2, c3 = st.columns(3)
max_per_template = c1.slider("Max parameter combos per family", 1, 40, 8)
stop_values = c2.multiselect("Stop-loss %", [0.25, 0.5, 0.75, 1.0, 1.5, 2.0], default=[0.5, 1.0])
target_values = c3.multiselect("Target %", [0.5, 1.0, 1.5, 2.0, 3.0], default=[1.0, 2.0])
min_trades = st.slider(
    "Minimum trades to be considered (fewer = noise, not edge)", 3, 50, 10,
)

capital = st.number_input("Capital (Rs)", min_value=1000, value=100000, step=10000)
quantity = st.number_input("Quantity per trade", min_value=1, value=10, step=1)
allow_short = st.checkbox("Allow short selling", value=True)

base_cfg = validate_config({
    "name": "scanner_base",
    "capital": float(capital),
    "strategy": {"name": "rules", "params": {}, "quantity": int(quantity), "allow_short": bool(allow_short)},
})

estimated = estimate_scanner_count(template_keys, max_per_template, len(stop_values) or 1, len(target_values) or 1)
st.metric("Candidates to test", estimated)
if estimated > 2000:
    st.warning("That's a lot of candidates and may take a while in this environment. Consider lowering the combo limit.")

if st.button("🔬 Run Strategy Scanner", type="primary"):
    candidates = build_scanner_candidates(
        base_cfg, template_keys, int(max_per_template), stop_values or [0.5], target_values or [1.0],
    )
    rows = []
    progress = st.progress(0, text="Testing strategies...")
    for i, cfg in enumerate(candidates, start=1):
        try:
            strategy = build_strategy(cfg)
            result = run_backtest(df, cfg, strategy)
            m = result.metrics
            rows.append({
                "family": cfg["_template_label"],
                "template_key": cfg["_template_key"],
                "params": ", ".join(f"{k}={v}" for k, v in cfg["_params"].items()),
                "trades": m["trades"],
                "net_pnl_Rs": round(m["net_pnl"], 2),
                "return_pct": round(m["return_pct"], 2),
                "win_rate_pct": round(m["win_rate_pct"], 1) if m["win_rate_pct"] is not None else None,
                "profit_factor": round(m["profit_factor"], 2) if m["profit_factor"] not in (None, float("inf")) else m["profit_factor"],
                "max_drawdown_pct": round(m["max_drawdown_pct"], 2),
                "sharpe_daily": round(m["sharpe_daily"], 2) if m["sharpe_daily"] is not None else None,
                "score": round(score_result(m, min_trades=int(min_trades)), 2),
                "_cfg": cfg,
            })
        except Exception as exc:  # a bad param combo should not kill the whole scan
            rows.append({
                "family": cfg.get("_template_label", "?"), "template_key": cfg.get("_template_key", "?"),
                "params": str(cfg.get("_params", {})), "trades": 0, "net_pnl_Rs": None,
                "return_pct": None, "win_rate_pct": None, "profit_factor": None,
                "max_drawdown_pct": None, "sharpe_daily": None, "score": float("-inf"), "_cfg": None,
                "error": str(exc),
            })
        if i % max(1, len(candidates) // 50) == 0 or i == len(candidates):
            progress.progress(i / len(candidates), text=f"Testing candidate {i}/{len(candidates)}")
    progress.empty()
    st.session_state["scanner_rows"] = rows

rows = st.session_state.get("scanner_rows")
if rows:
    ranked = rank_scanner_rows(rows)
    valid = [r for r in ranked if r["score"] != float("-inf")]

    st.subheader("3. Leaderboard")
    if not valid:
        st.error(
            f"No candidate cleared the minimum-trades bar ({min_trades}) with a usable score. "
            "Try more data, a lower minimum-trades bar, or a wider parameter search."
        )
    else:
        table = pd.DataFrame([{k: v for k, v in r.items() if k not in ("_cfg", "error")} for r in ranked])
        ui.show_table(table.head(30))

        best = valid[0]
        st.subheader("🏆 Best candidate for this data")
        st.info(
            f"**{best['family']}** ({best['params']}) — {best['trades']} trades, "
            f"{best['return_pct']}% return, {best['win_rate_pct']}% win rate, "
            f"max drawdown {best['max_drawdown_pct']}%, score {best['score']}.\n\n"
            "This is the top of a leaderboard on THIS data set, not a proven edge. "
            "A strategy that tops a scan can still be overfit to this exact period."
        )
        if best.get("_cfg") is not None:
            with st.expander("Show this candidate's rules"):
                st.json(best["_cfg"]["strategy"]["params"])

    st.subheader("4. Take it further")
    st.markdown(
        "1. Send the top candidates to **Backtest** and re-check the trade log by eye.\n"
        "2. Use **Reality Check** with an out-of-sample period the scanner never saw.\n"
        "3. Run **Test Lab** / **Auto Tester** for additional stress testing across fake-market regimes.\n"
        "4. Paper trade (or Upstox Sandbox) before ever considering live execution."
    )

ui.footer_note(
    "Strategy Scanner tests a bounded library of strategy templates on price data you provide. "
    "It never places orders or connects to a broker, and a leaderboard win is not a promise."
)
