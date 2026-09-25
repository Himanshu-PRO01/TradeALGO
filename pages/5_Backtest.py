"""Backtest: test a rule on past prices with your real costs and risk limits."""
import io

import pandas as pd
import streamlit as st
import yaml

from algobot import ui
from algobot.appstate import experiments_scope
from algobot.charts import candlestick, equity_drawdown
from algobot.config import ConfigError, validate_config
from algobot.data import DataError, generate_sample_data, load_csv
from algobot.explain import explain_config
from algobot.lookahead import run_lookahead_checks
from algobot.prompt import AI_STRATEGY_PROMPT
from algobot.report import summary_text
from algobot.runner import check_strategy, run_from_dict

DEFAULT_RULES = """\
indicators:
  - {name: ema_fast, type: ema, period: 9}
  - {name: ema_slow, type: ema, period: 21}
  - {name: rsi_14,   type: rsi, period: 14}
entry_long:  "ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev and rsi_14 > 50"
exit_long:   "ema_fast < ema_slow"
entry_short: "ema_fast < ema_slow and ema_fast_prev >= ema_slow_prev and rsi_14 < 50"
exit_short:  "ema_fast > ema_slow"
"""

ui.setup("Backtest", "📊")
ui.header("Backtest", "Test a rule on past prices with your real costs and risk limits. A backtest is a filter, not a promise: "
          "the Reality check page tries to break it.", mode="backtest:Backtest · past prices")


@st.cache_data(show_spinner=False)
def sample_data(days: int):
    return generate_sample_data(days=days, seed=42)


def none_if_zero(value):
    return None if value in (0, 0.0) else value


def colour_pnl(value):
    if isinstance(value, (int, float)) and value == value:
        return "color: #16C784" if value > 0 else ("color: #EA3943" if value < 0 else "")
    return ""


# --------------------------------------------------------------------- strategy
# ------------------------------------------------------------------ backtest settings
st.markdown("### Backtest settings")
st.caption("Set the test inputs here. The sidebar is reserved for navigation.")
with st.expander("1. Price data", expanded=True):
    source = st.radio("Where do the prices come from?", ["Sample data (random, for testing)", "Upload a CSV file"], key="data_source")
    days = st.slider("Days of sample data", 10, 120, 60, key="sample_days")
    uploaded = st.file_uploader("CSV with datetime, open, high, low, close (volume optional)", type=["csv"], key="csv")
with st.expander("2. Trade size and safety", expanded=True):
    c1, c2, c3 = st.columns(3)
    capital = c1.number_input("Account size (Rs)", min_value=1000, value=100000, step=1000, key="capital")
    quantity = c2.number_input("Shares per trade", min_value=1, value=10, step=1, key="quantity")
    allow_short = c3.checkbox("Allow short selling", value=False, key="allow_short")
    c1, c2, c3 = st.columns(3)
    stop_pct = c1.number_input("Stop-loss % (0 = none)", min_value=0.0, value=0.5, step=0.1, key="stop_pct")
    target_pct = c2.number_input("Profit target % (0 = none)", min_value=0.0, value=1.0, step=0.1, key="target_pct")
    max_loss = c3.number_input("Stop trading for the day after losing (Rs, 0 = no limit)", min_value=0, value=2000, step=100, key="max_loss")
    c1, c2, c3 = st.columns(3)
    max_trades = c1.number_input("Max trades per day (0 = no limit)", min_value=0, value=6, step=1, key="max_trades")
    max_position = c2.number_input("Largest single position (Rs, 0 = no limit)", min_value=0, value=50000, step=1000, key="max_position")
    t_start = c3.text_input("No trades before (HH:MM)", "09:20", key="t_start")
    c1, c2 = st.columns(2)
    t_last = c1.text_input("No new trades after (HH:MM)", "14:45", key="t_last")
    t_off = c2.text_input("Close everything at (HH:MM)", "15:15", key="t_off")
with st.expander("3. Costs (example values: check your broker's charge calculator)"):
    c1, c2, c3 = st.columns(3)
    brokerage_pct = c1.number_input("Brokerage % of order value", min_value=0.0, value=0.03, step=0.01, format="%.4f", key="c_brokerage")
    brokerage_cap = c2.number_input("Brokerage cap per order (Rs, 0 = no cap)", min_value=0.0, value=20.0, key="c_cap")
    stt_sell = c3.number_input("STT % on sells", min_value=0.0, value=0.025, format="%.4f", key="c_stt_sell")
    c1, c2, c3 = st.columns(3)
    stt_buy = c1.number_input("STT % on buys", min_value=0.0, value=0.0, format="%.4f", key="c_stt_buy")
    exch = c2.number_input("Exchange charges %", min_value=0.0, value=0.003, format="%.5f", key="c_exch")
    sebi = c3.number_input("SEBI fee %", min_value=0.0, value=0.0001, format="%.5f", key="c_sebi")
    c1, c2, c3 = st.columns(3)
    stamp = c1.number_input("Stamp duty % on buys", min_value=0.0, value=0.003, format="%.4f", key="c_stamp")
    gst = c2.number_input("GST % (on brokerage and fees)", min_value=0.0, value=18.0, key="c_gst")
    slippage = c3.number_input("Slippage (bps, 1 bps = 0.01%)", min_value=0.0, value=2.0, key="c_slip")

st.markdown("#### 1. Strategy")
kind = st.radio("Type", ["Rules (write conditions)", "SMA crossover (demo)"], horizontal=True, key="strategy_kind")
if kind.startswith("Rules"):
    strategy_name = "rules"
    rules_text = st.text_area("Strategy rules (edit, or paste what an AI wrote)", DEFAULT_RULES, height=230, key="rules_text")
    with st.expander("Want an AI to write the rules for you? Copy this prompt into any AI chat"):
        st.code(AI_STRATEGY_PROMPT, language="text")
        st.caption("Paste the yaml block it gives you into the box above. Never paste broker keys or passwords into an AI chat. "
                   "The plain-English section below is produced by this program, not by the AI: use it to check the AI understood you.")
else:
    strategy_name = "sma_crossover"
    c1, c2 = st.columns(2)
    fast = c1.number_input("Fast average (bars)", min_value=1, value=10, step=1, key="sma_fast")
    slow = c2.number_input("Slow average (bars)", min_value=2, value=30, step=1, key="sma_slow")

try:
    if strategy_name == "rules":
        params = yaml.safe_load(rules_text)
        if not isinstance(params, dict):
            raise ConfigError("The rules box must contain settings like entry_long: \"...\".")
    else:
        params = {"fast": int(fast), "slow": int(slow)}
    raw = {
        "name": "dashboard_run", "capital": capital,
        "strategy": {"name": strategy_name, "params": params, "quantity": int(quantity), "allow_short": allow_short,
                     "stop_loss_pct": none_if_zero(stop_pct), "target_pct": none_if_zero(target_pct)},
        "risk": {"max_daily_loss": none_if_zero(max_loss), "max_trades_per_day": none_if_zero(int(max_trades)),
                 "max_position_value": none_if_zero(max_position), "trading_start": t_start.strip(),
                 "no_new_entries_after": t_last.strip(), "square_off_time": t_off.strip()},
        "costs": {"brokerage_pct": brokerage_pct, "brokerage_cap": none_if_zero(brokerage_cap), "stt_buy_pct": stt_buy,
                  "stt_sell_pct": stt_sell, "exchange_txn_pct": exch, "sebi_fee_pct": sebi, "stamp_buy_pct": stamp,
                  "gst_pct": gst, "slippage_bps": slippage},
    }
    cfg = validate_config(raw)
    check_strategy(cfg)
except (ConfigError, yaml.YAMLError) as exc:
    st.error(f"Please fix this first: {exc}")
    st.stop()

st.markdown("#### 2. Check it says what you mean")
st.text(explain_config(cfg))
confirmed = st.checkbox("Yes, this is exactly what I meant", key="confirm")


def load_prices():
    if source.startswith("Sample"):
        return sample_data(days)
    if uploaded is None:
        st.info("Upload a CSV file above, or switch to the sample data.")
        return None
    return load_csv(io.BytesIO(uploaded.getvalue()))


st.markdown("#### 3. Run")
col_a, col_b = st.columns(2)
check_clicked = col_a.button("Check the rules for look-ahead", key="btn_lookahead", disabled=not confirmed, width="stretch")
run_clicked = col_b.button("Run backtest", type="primary", key="btn_run", disabled=not confirmed, width="stretch")
if not confirmed:
    st.caption("Tick the box above to enable the buttons.")

if check_clicked or run_clicked:
    try:
        prices = load_prices()
    except DataError as exc:
        st.error(f"Problem with the price data: {exc}")
        prices = None
    if prices is not None and check_clicked:
        try:
            st.session_state["lookahead"] = run_lookahead_checks(cfg, prices)
        except ConfigError as exc:
            st.error(f"The check could not run: {exc}")
    if prices is not None and run_clicked:
        try:
            st.session_state["result"] = run_from_dict(raw, prices)
            st.session_state["result_yaml"] = yaml.safe_dump(raw, sort_keys=False)
            st.session_state["used_sample"] = source.startswith("Sample")
            st.session_state["last_raw"] = raw            # used by the Reality check and Test lab pages
            st.session_state["last_prices"] = prices
            with experiments_scope() as log:
                log.record(prices, cfg, st.session_state["result"])
                st.session_state["variants_tried"] = log.count_trials(prices)
        except (ConfigError, DataError) as exc:
            st.error(f"The backtest could not run: {exc}")

checks = st.session_state.get("lookahead")
if checks:
    st.subheader("Look-ahead check")
    st.caption("Proves the rules cannot secretly use information from the future, the classic reason a backtest looks better than reality.")
    for c in checks:
        (st.success if c.passed else st.error)(f"{c.name}: {c.detail}")

result = st.session_state.get("result")
if result is not None:
    st.subheader("Results")
    if st.session_state.get("used_sample"):
        st.warning("This used random sample data. The numbers say nothing about real markets.")
    m = result.metrics
    a, b, c, d, e = st.columns(5)
    a.metric("Net profit / loss (Rs)", f"{m['net_pnl']:,.0f}", f"{m['return_pct']:+.2f}%")
    b.metric("Return", f"{m['return_pct']:.2f}%")
    c.metric("Trades", m["trades"])
    d.metric("Win rate", "n/a" if m["win_rate_pct"] is None else f"{m['win_rate_pct']:.0f}%")
    e.metric("Worst drop (Rs)", f"{m['max_drawdown']:,.0f}")
    f, g, h = st.columns(3)
    f.metric("Before costs (Rs)", f"{m['gross_pnl']:,.0f}")
    g.metric("Costs paid (Rs)", f"{m['total_costs']:,.0f}")
    pf = m["profit_factor"]
    h.metric("Profit factor", "n/a" if pf is None else ("infinite" if pf == float("inf") else f"{pf:.2f}"))
    tried = st.session_state.get("variants_tried")
    if tried:
        st.caption(f"Variants tried on this data so far: {tried}. The more you try, the more a good-looking result can be luck. "
                   "Open the 'Reality check' page before believing any result.")

    tab_price, tab_equity, tab_trades, tab_notes = st.tabs(["Price and trades", "Equity and drawdown", "Trades", "Notes"])
    with tab_price:
        prices_now = st.session_state.get("last_prices")
        if prices_now is not None:
            window = st.slider("Bars shown (latest)", 100, 1000, 300, step=50, key="bt_window")
            ui.show_chart(candlestick(prices_now, trades=result.trades, height=360, max_bars=int(window)))
            st.caption("Blue triangle: entry (up = long, down = short). Green cross: winning exit. Red cross: losing exit.")
    with tab_equity:
        ui.show_chart(equity_drawdown(result.equity))
    with tab_trades:
        if len(result.trades):
            blotter = result.trades.copy()
            blotter["entry_time"] = pd.to_datetime(blotter["entry_time"]).dt.strftime("%d %b %H:%M")
            blotter["exit_time"] = pd.to_datetime(blotter["exit_time"]).dt.strftime("%d %b %H:%M")
            money = ["gross_pnl", "costs", "net_pnl"]
            styler = blotter.style.format({c: "{:,.2f}" for c in money})
            styler = styler.map(colour_pnl, subset=["net_pnl", "gross_pnl"]) if hasattr(styler, "map") else styler.applymap(colour_pnl, subset=["net_pnl", "gross_pnl"])
            ui.show_table(styler, hide_index=True)
        else:
            st.info("No trades were taken.")
        st.download_button("Download trades (CSV)", result.trades.to_csv(index=False), "trades.csv", "text/csv", key="dl_trades")
        st.download_button("Download these settings (YAML)", st.session_state["result_yaml"], "my_strategy.yaml", "text/yaml",
                           key="dl_settings")
    with tab_notes:
        if result.events or result.rejections:
            st.markdown("**Risk rules that kicked in**")
            for ev in result.events:
                st.write(ev)
            for reason, count in result.rejections.items():
                st.write(f"Entries blocked ({reason}): {count}")
        st.text(summary_text(result))
ui.footer_note()
