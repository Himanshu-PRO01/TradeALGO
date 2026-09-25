"""Reality check: try to break the strategy from the Backtest page before real money does."""
import streamlit as st

from algobot import ui
from algobot.appstate import experiments_scope
from algobot.audit import format_audit, run_audit
from algobot.config import ConfigError, validate_config

ui.setup("Reality check", "🛡️")
ui.header("Reality check", "A second opinion on the Backtest page's result, before you ever risk real money on it.",
          mode="research:Stress test")

with st.expander("New here? Read this first", expanded=True):
    st.markdown(
        "A backtest can look good by accident — a lucky run of trades, or a rule that was quietly "
        "tweaked until it fit the past. This page runs **8 tests** that try to catch that, the same "
        "problems that quietly ruin real strategies: too few trades, luck, rising costs, no real edge over "
        "guessing, falling apart later, working only at one exact setting, one lucky trade doing all the "
        "work, and the chance of a big loss.\n\n"
        "For each test you'll see one of three results:\n"
        "- 🟢 **PASS** — good sign\n"
        "- 🟡 **WARN** — be careful, keep testing\n"
        "- 🔴 **FAIL** — a real reason not to trade this with real money yet\n\n"
        "**Surviving all 8 does not prove the strategy will make money.** It just means this particular "
        "way of looking for problems didn't find any."
    )

raw = st.session_state.get("last_raw")
prices = st.session_state.get("last_prices")
if raw is None or prices is None:
    st.info("Run a backtest on the Backtest page first. This page checks the strategy and prices used in your last run.")
    ui.footer_note()
    st.stop()

try:
    cfg = validate_config(raw)
except ConfigError as exc:
    st.error(f"The last settings are not valid: {exc}")
    st.stop()

with experiments_scope() as log:
    logged = max(log.count_trials(prices), 1)

st.caption("The defaults below work for most cases — you can just press the button.")
with st.expander("Advanced settings"):
    c1, c2, c3, c4 = st.columns(4)
    trials = c1.number_input("Variants tried on this data", min_value=1, value=int(logged), step=1, key="au_trials",
                             help="Counted automatically from your earlier runs. Raise it if you also tried ideas elsewhere.")
    n_random = c2.slider("Random-entry runs", 20, 200, 60, key="au_random",
                         help="How many pretend 'monkey' strategies (entering at random) to compare yours against. More = a slower but steadier test.")
    paths = c3.slider("Simulated futures", 200, 3000, 1000, step=100, key="au_paths",
                      help="How many possible futures to imagine by reshuffling your trades, to estimate the odds of a big loss. More = a slower but steadier estimate.")
    ruin_pct = c4.number_input("Count this account loss as ruin (%)", min_value=5, max_value=90, value=30, key="au_ruin",
                               help="How much of the account balance would have to be lost before you'd call it a disaster.")

if st.button("Run the reality check", type="primary", key="au_run", width="stretch"):
    with st.spinner("Trying to break it. This can take a minute..."):
        st.session_state["audit_report"] = run_audit(prices, cfg, trials=int(trials), n_random=int(n_random),
                                                     n_mc=int(paths), ruin_pct=float(ruin_pct))

report = st.session_state.get("audit_report")
if report is not None:
    counts = {s: sum(1 for c in report.checks if c.status == s) for s in ("PASS", "WARN", "FAIL", "SKIP")}
    ui.ticker([("Passed", counts["PASS"], "up"), ("Warnings", counts["WARN"], "warn" if counts["WARN"] else None),
               ("Failed", counts["FAIL"], "down" if counts["FAIL"] else None), ("Skipped", counts["SKIP"], None)])
    if report.failed:
        st.error(report.verdict)
    elif report.verdict.startswith("PROMISING"):
        st.warning(report.verdict)
    else:
        st.success(report.verdict)
    st.caption("The 8 tests behind that verdict, one by one:")
    for c in report.checks:
        ui.check_row(c.status, c.name, c.detail)
    with st.expander("Plain-text version (to copy)"):
        st.code(format_audit(report), language="text")
ui.footer_note()
