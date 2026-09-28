"""Dynamic CE/PE option strategy: select a contract and roll strikes from the underlying."""
import io

import pandas as pd
import streamlit as st

from algobot import ui
from algobot.config import ConfigError
from algobot.data import generate_sample_data
from algobot.dynamic_options import (
    generate_synthetic_option_chain,
    load_option_chain_csv,
    run_dynamic_strike_option_backtest,
    validate_option_chain,
)

ui.setup("Dynamic Options", "🎯")
ui.header(
    "Dynamic CE / PE Strategy",
    "Select a real CE/PE contract from an option-chain file and optionally roll the strike as the underlying moves.",
    mode="research:Options",
)

st.info(
    "🧪 Research only · This page does not place broker orders. "
    "Real option-chain CSVs are supported; the built-in practice chain is synthetic and "
    "must not be used to judge real profitability."
)

with st.expander("How the strategy works", expanded=True):
    st.markdown(
        """
**Entry → contract selection → dynamic strike → time exit**

1. At the configured entry time, TradeALGO selects the requested CE or PE.
2. ATM selects the available strike closest to the underlying price; Fixed selects the closest available contract to your requested strike.
3. While the position is open, if the underlying closes above active strike + upper trigger, the strategy schedules a roll up one strike step.
4. If it closes below active strike - lower trigger, it schedules a roll down one strike step.
5. The roll executes on the next bar's option open, so the current bar's close is never used as an executable fill.
6. The position exits at the configured exit time.
"""
    )
    st.caption(
        "This is a new deterministic strategy based on the dynamic-strike behavior visible in the "
        "screenshots you supplied. It is not a claim that the screenshots contained the missing entry logic."
    )

source = st.radio(
    "Option-chain source",
    ["Practice synthetic chain", "Upload real option-chain CSV"],
    horizontal=True,
    key="dynamic_options_source",
)

if source == "Practice synthetic chain":
    c1, c2, c3 = st.columns(3)
    days = c1.slider("Practice days", 1, 20, 5, key="opt_days")
    start_price = c2.number_input("Underlying start", min_value=100.0, value=24500.0, step=50.0, key="opt_start")
    iv = c3.number_input("Synthetic IV (%)", min_value=1.0, max_value=100.0, value=18.0, step=1.0, key="opt_iv")
    c1, c2 = st.columns(2)
    strike_step_data = c1.number_input("Chain strike step", min_value=1.0, value=50.0, step=50.0, key="opt_chain_step")
    strikes_each_side = c2.slider("Strikes on each side", 2, 12, 6, key="opt_strikes")
    underlying = generate_sample_data(
        days=days,
        bars_per_day=75,
        minutes_per_bar=5,
        start_price=start_price,
        seed=42,
    )
    prices = generate_synthetic_option_chain(
        underlying,
        strike_step=int(strike_step_data),
        strikes_each_side=int(strikes_each_side),
        iv=iv / 100.0,
        days_to_expiry=max(days + 2, 3),
    )
    st.warning(
        "Synthetic option premiums are generated only to exercise the CE/PE selector and rolling engine. "
        "They are not market prices and should not be used to evaluate a trading edge."
    )
    download = prices.reset_index().to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download this chain as CSV",
        download,
        file_name="tradealgo_option_chain_template.csv",
        mime="text/csv",
        use_container_width=True,
    )
else:
    uploaded = st.file_uploader(
        "Upload an option-chain CSV",
        type=["csv"],
        help=(
            "Wide format: datetime + underlying open/high/low/close plus CE_24500_open/high/low/close "
            "and PE equivalents. Long historical format: datetime, strike, option_type, option open/high/low/close, "
            "plus underlying_open/high/low/close; one expiry per file."
        ),
        key="dynamic_options_upload",
    )
    if uploaded is None:
        st.info("Upload a CSV to enable the real option-chain backtest.")
        prices = None
    else:
        try:
            prices = load_option_chain_csv(io.BytesIO(uploaded.getvalue()))
            st.success("Option-chain CSV loaded.")
        except ConfigError as exc:
            st.error(str(exc))
            prices = None

if prices is not None:
    contracts = validate_option_chain(prices)
    ce_strikes = sorted({c.strike for c in contracts if c.kind == "CE"})
    pe_strikes = sorted({c.strike for c in contracts if c.kind == "PE"})
    st.caption(
        f"Detected {len(ce_strikes)} CE strikes and {len(pe_strikes)} PE strikes "
        f"across {len(prices):,} underlying bars."
    )

    st.markdown("### Strategy settings")
    c1, c2 = st.columns(2)
    contract_type = c1.selectbox(
        "Contract side",
        ["CE", "PE"],
        format_func=lambda x: "🟢 CE · Call" if x == "CE" else "🔴 PE · Put",
        key="dynamic_contract_type",
    )
    strike_mode = c2.selectbox(
        "Initial strike selection",
        ["ATM", "FIXED"],
        format_func=lambda x: "ATM · closest available strike" if x == "ATM" else "Fixed · closest available contract",
        key="dynamic_strike_mode",
    )

    available_selected = ce_strikes if contract_type == "CE" else pe_strikes
    default_strike = available_selected[len(available_selected) // 2] if available_selected else float(prices["close"].iloc[0])
    c1, c2, c3 = st.columns(3)
    initial_strike = c1.selectbox(
        "Initial fixed strike",
        available_selected or [default_strike],
        index=(available_selected.index(default_strike) if default_strike in available_selected else 0),
        disabled=strike_mode != "FIXED",
        key="dynamic_initial_strike",
    )
    quantity = c2.number_input("Quantity", min_value=1, value=1, step=1, key="dynamic_qty")
    dynamic_strike = c3.toggle("Enable dynamic strike rolling", value=True, key="dynamic_roll")

    c1, c2, c3 = st.columns(3)
    strike_step = c1.number_input(
        "Strike step", min_value=1.0, value=50.0, step=50.0, key="dynamic_step",
        help="The target strike changes by this amount when a trigger fires.",
    )
    upper_trigger = c2.number_input(
        "Roll up trigger", min_value=0.0, value=50.0, step=5.0, key="dynamic_upper",
        help="Underlying close must reach active strike + this many points.",
    )
    lower_trigger = c3.number_input(
        "Roll down trigger", min_value=0.0, value=45.0, step=5.0, key="dynamic_lower",
        help="Underlying close must reach active strike - this many points.",
    )

    c1, c2 = st.columns(2)
    entry_time = c1.time_input("Entry time", value=pd.Timestamp("09:30").time(), key="dynamic_entry")
    exit_time = c2.time_input("Exit time", value=pd.Timestamp("15:15").time(), key="dynamic_exit")

    if entry_time >= exit_time:
        st.error("Entry time must be before exit time.")
        run = False
    else:
        run = st.button("▶ Run Dynamic CE/PE Backtest", type="primary", width="stretch", key="dynamic_run")

    if run:
        try:
            trades, events = run_dynamic_strike_option_backtest(
                prices,
                contract_type=contract_type,
                quantity=int(quantity),
                strike_mode=strike_mode,
                initial_strike=float(initial_strike) if strike_mode == "FIXED" else None,
                strike_step=float(strike_step),
                upper_trigger=float(upper_trigger),
                lower_trigger=float(lower_trigger),
                entry_time=entry_time.strftime("%H:%M"),
                exit_time=exit_time.strftime("%H:%M"),
                dynamic_strike=bool(dynamic_strike),
            )
            st.session_state["dynamic_option_trades"] = trades
            st.session_state["dynamic_option_events"] = events
            st.session_state["dynamic_option_config"] = {
                "contract_type": contract_type,
                "quantity": int(quantity),
                "strike_mode": strike_mode,
                "initial_strike": float(initial_strike) if strike_mode == "FIXED" else None,
                "strike_step": float(strike_step),
                "upper_trigger": float(upper_trigger),
                "lower_trigger": float(lower_trigger),
                "entry_time": entry_time.strftime("%H:%M"),
                "exit_time": exit_time.strftime("%H:%M"),
                "dynamic_strike": bool(dynamic_strike),
            }
        except ConfigError as exc:
            st.error(f"Could not run the option strategy: {exc}")

    trades = st.session_state.get("dynamic_option_trades")
    if trades is not None:
        st.markdown("### Results")
        gross = float(trades["gross_pnl"].sum()) if not trades.empty else 0.0
        rolls = int(trades["rolls"].sum()) if not trades.empty else 0
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Closed legs", len(trades))
        c2.metric("Gross P&L", f"Rs {gross:,.0f}")
        c3.metric("Strike rolls", rolls)
        c4.metric("Contracts used", int(trades["contract"].nunique()) if not trades.empty else 0)

        if trades.empty:
            st.info("No entry occurred in the supplied window. Try an earlier entry time or a longer dataset.")
        else:
            st.dataframe(trades, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Download trade log",
                trades.to_csv(index=False).encode("utf-8"),
                file_name="tradealgo_dynamic_option_trades.csv",
                mime="text/csv",
                use_container_width=True,
            )

        events = st.session_state.get("dynamic_option_events", [])
        if events:
            with st.expander(f"Strike-roll events ({len(events)})"):
                st.code("\n".join(events), language="text")

        with st.expander("Exact strategy configuration"):
            st.json(st.session_state.get("dynamic_option_config", {}))

ui.footer_note(
    "Dynamic option backtest only. Real option-chain prices are required for meaningful research; "
    "no broker order is sent from this page."
)
