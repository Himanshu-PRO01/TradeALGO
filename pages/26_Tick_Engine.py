"""Tick Engine: tick-by-tick dynamic CE/PE research and paper rehearsal."""
import io

import pandas as pd
import streamlit as st

from algobot import ui
from algobot.config import ConfigError
from algobot.data import generate_sample_data
from algobot.dynamic_options import generate_synthetic_option_chain
from algobot.tick_engine import load_tick_csv, run_tick_strategy

ui.setup("Tick Engine", "⚡")
ui.header(
    "Tick Engine",
    "Evaluate dynamic CE/PE triggers on every underlying price tick instead of waiting for candle closes.",
    mode="research:Tick",
)

st.warning(
    "⚠️ Research / paper-rehearsal only. A tick engine can improve execution modelling, "
    "but it does not guarantee higher profits. This page does not place broker orders."
)

with st.expander("Why tick logic?", expanded=True):
    st.markdown(
        """
**Candle engine:** waits for a completed candle → checks the close → acts later.

**Tick engine:** receives each timestamped price update → checks the trigger immediately → "
        "schedules the simulated roll for the next available tick.

This is closer to the live strategy architecture in the screenshots you supplied, while keeping
broker execution separate from research.
"""
    )

source = st.radio(
    "Tick-data source",
    ["Practice synthetic ticks", "Upload tick CSV"],
    horizontal=True,
    key="tick_source",
)

if source == "Practice synthetic ticks":
    days = st.slider("Practice days", 1, 5, 1, key="tick_days")
    start = st.number_input("Underlying start", min_value=100.0, value=24500.0, step=50.0, key="tick_start")
    bars = generate_sample_data(days=days, bars_per_day=75, minutes_per_bar=5, start_price=start, seed=42)
    # Expand each 5-minute bar into deterministic intra-bar ticks so the UI exercises
    # tick transitions without pretending that these are real exchange ticks.
    rows = []
    for ts, row in bars.iterrows():
        points = [float(row["open"]), float((row["high"] + row["low"]) / 2), float(row["close"])]
        for offset, spot in enumerate(points):
            rows.append({"datetime": ts + pd.Timedelta(seconds=offset * 20), "last_price": spot})
    ticks = pd.DataFrame(rows).set_index("datetime")
    chain = generate_synthetic_option_chain(
        bars,
        strike_step=50,
        strikes_each_side=8,
        iv=0.18,
        days_to_expiry=max(days + 2, 3),
    )
    option_cols = [c for c in chain.columns if str(c).startswith(("CE_", "PE_")) and str(c).endswith("_close")]
    for col in option_cols:
        ticks[col.replace("_close", "_last_price")] = chain[col].reindex(bars.index).ffill().repeat(3).to_numpy()[:len(ticks)]
    st.info("Synthetic ticks are for engine testing only, not market data.")
    csv = ticks.reset_index().to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download practice tick template", csv, "tradealgo_tick_template.csv", "text/csv")
else:
    uploaded = st.file_uploader(
        "Upload tick CSV",
        type=["csv"],
        help="Required: datetime + last_price/tick_price/ltp. Option columns: CE_24500_last_price and PE_24500_last_price.",
        key="tick_upload",
    )
    ticks = None
    if uploaded:
        try:
            ticks = load_tick_csv(io.BytesIO(uploaded.getvalue()))
            st.success(f"Loaded {len(ticks):,} ticks.")
        except ConfigError as exc:
            st.error(str(exc))

if ticks is not None:
    from algobot.tick_engine import _find_option_columns
    contracts = _find_option_columns(ticks)
    ce = sorted(c.strike for c in contracts if c.kind == "CE")
    pe = sorted(c.strike for c in contracts if c.kind == "PE")
    st.caption(f"Detected {len(ce)} CE and {len(pe)} PE tick-price contracts.")

    c1, c2 = st.columns(2)
    side = c1.selectbox("Contract side", ["CE", "PE"], key="tick_side")
    mode = c2.selectbox("Initial strike", ["ATM", "FIXED"], key="tick_mode")
    available = ce if side == "CE" else pe
    default = available[len(available)//2] if available else 24500
    c1, c2, c3 = st.columns(3)
    fixed = c1.selectbox("Fixed strike", available or [default], disabled=mode != "FIXED", key="tick_fixed")
    qty = c2.number_input("Quantity", min_value=1, value=1, step=1, key="tick_qty")
    dynamic = c3.toggle("Dynamic strike rolling", value=True, key="tick_dynamic")
    c1, c2, c3 = st.columns(3)
    step = c1.number_input("Strike step", min_value=1.0, value=50.0, step=50.0, key="tick_step")
    up = c2.number_input("Upper trigger", min_value=0.0, value=50.0, step=5.0, key="tick_up")
    down = c3.number_input("Lower trigger", min_value=0.0, value=45.0, step=5.0, key="tick_down")
    c1, c2 = st.columns(2)
    entry = c1.time_input("Entry time", value=pd.Timestamp("09:30").time(), key="tick_entry")
    exit_ = c2.time_input("Exit time", value=pd.Timestamp("15:15").time(), key="tick_exit")

    if entry >= exit_:
        st.error("Entry time must be before exit time.")
        run = False
    else:
        run = st.button("⚡ Run Tick Engine", type="primary", width="stretch", key="tick_run")

    if run:
        try:
            trades, events = run_tick_strategy(
                ticks,
                contract_type=side,
                quantity=int(qty),
                strike_mode=mode,
                initial_strike=float(fixed) if mode == "FIXED" else None,
                strike_step=float(step),
                upper_trigger=float(up),
                lower_trigger=float(down),
                entry_time=entry.strftime("%H:%M"),
                exit_time=exit_.strftime("%H:%M"),
                dynamic_strike=bool(dynamic),
            )
            st.session_state["tick_trades"] = trades
            st.session_state["tick_events"] = events
        except ConfigError as exc:
            st.error(str(exc))

    trades = st.session_state.get("tick_trades")
    if trades is not None:
        gross = float(trades["gross_pnl"].sum()) if not trades.empty else 0.0
        c1, c2, c3 = st.columns(3)
        c1.metric("Closed legs", len(trades))
        c2.metric("Gross P&L", f"₹{gross:,.0f}")
        c3.metric("Tick rolls", int(trades["rolls"].sum()) if not trades.empty else 0)
        if trades.empty:
            st.info("No position was opened in the supplied tick window.")
        else:
            st.dataframe(trades, width="stretch", hide_index=True)
        events = st.session_state.get("tick_events", [])
        if events:
            with st.expander(f"Tick trigger events ({len(events)})"):
                st.code("\n".join(events), language="text")

ui.footer_note(
    "Tick Engine is research/paper-only. It models tick-triggered decisions but sends no broker orders."
)
