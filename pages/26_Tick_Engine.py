"""Tick Engine: tick-by-tick dynamic CE/PE research and paper rehearsal."""
import io
import os

import pandas as pd
import streamlit as st

from algobot import ui
from algobot.config import ConfigError
from algobot.data import generate_sample_data
from algobot.dynamic_options import generate_synthetic_option_chain
from algobot.tick_engine import load_tick_csv, run_tick_strategy
from algobot.upstox_market_data import UpstoxMarketData
from algobot.upstox_option_contracts import UpstoxOptionContracts

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
    ["Practice synthetic ticks", "Upload tick CSV", "Upstox Live V3"],
    horizontal=True,
    key="tick_source",
)

if source == "Upstox Live V3":
    st.info(
        "Live Upstox mode is read-only market data. It does not place orders. "
        "Use an Upstox Analytics Token or another read-only market-data token."
    )
    st.markdown(
        "Configure UPSTOX_ACCESS_TOKEN in Streamlit Secrets/environment variables. "
        "Never commit the token to GitHub."
    )

    token = (os.getenv("UPSTOX_ANALYTICS_TOKEN") or os.getenv("UPSTOX_ACCESS_TOKEN") or "").strip()
    try:
        if not token and hasattr(st, "secrets"):
            token = str(st.secrets.get("UPSTOX_ANALYTICS_TOKEN") or st.secrets.get("UPSTOX_ACCESS_TOKEN") or "").strip()
    except Exception:
        token = token

    if not token:
        st.warning(
            "No Upstox token is configured. Add UPSTOX_ANALYTICS_TOKEN (preferred) or UPSTOX_ACCESS_TOKEN to Streamlit Secrets "
            "and reload this page."
        )

    c1, c2 = st.columns(2)
    underlying_key = c1.text_input(
        "Underlying instrument key",
        value="NSE_INDEX|Nifty 50",
        help="Example: NSE_INDEX|Nifty 50. Use the exact instrument key from Upstox.",
        key="upstox_underlying_key",
    )
    feed_mode = c2.selectbox(
        "Feed mode",
        ["full", "ltpc", "option_greeks"],
        help="Use full for LTP + best bid/ask + option Greeks.",
        key="upstox_feed_mode",
    )
    expiry = st.selectbox(
        "Option expiry",
        ["current_week", "next_week", "current_month", "next_month"],
        help="Upstox resolves these relative expiry keywords automatically.",
        key="upstox_option_expiry",
    )
    refresh_contracts = st.button("🔄 Find current CE/PE contracts", key="refresh_option_contracts")

    stored_expiry = st.session_state.get("upstox_option_contract_expiry")
    if "upstox_option_contracts" not in st.session_state or refresh_contracts or stored_expiry != expiry:
        if token and underlying_key.strip():
            try:
                resolver = UpstoxOptionContracts(token, underlying_key.strip())
                st.session_state["upstox_option_contracts"] = resolver.fetch(expiry)
                st.session_state["upstox_option_contract_expiry"] = expiry
            except ConfigError as exc:
                st.session_state["upstox_option_contracts_error"] = str(exc)
        else:
            st.session_state["upstox_option_contracts_error"] = "Configure an Upstox token and underlying instrument key first."

    contracts = st.session_state.get("upstox_option_contracts", [])
    if st.session_state.get("upstox_option_contracts_error"):
        st.warning(st.session_state["upstox_option_contracts_error"])
    if contracts:
        st.success(f"Found {len(contracts)} current {st.session_state.get('upstox_option_contract_expiry', expiry)} CE/PE contracts automatically.")
        option_type = st.selectbox("Option side", ["CE", "PE"], key="upstox_option_side")
        available_strikes = sorted({c.strike_price for c in contracts if c.instrument_type == option_type})
        target_strike = st.number_input(
            "Target strike",
            min_value=float(min(available_strikes)) if available_strikes else 0.0,
            max_value=float(max(available_strikes)) if available_strikes else 999999.0,
            value=float(available_strikes[len(available_strikes)//2]) if available_strikes else 0.0,
            step=50.0,
            key="upstox_target_strike",
        )
        resolver = UpstoxOptionContracts(token, underlying_key.strip())
        mapping = resolver.by_strike(contracts, option_type)
        if mapping:
            selected_strike = resolver.nearest_strike(list(mapping), target_strike)
            selected = mapping[selected_strike]
            st.session_state["upstox_option_map"] = {
                f"{c.instrument_type} {c.strike_price:g}": c.instrument_key for c in contracts
            }
            st.dataframe(
                pd.DataFrame([{
                    "Side": selected.instrument_type,
                    "Strike": selected.strike_price,
                    "Expiry": selected.expiry,
                    "Trading symbol": selected.trading_symbol,
                    "Instrument key": selected.instrument_key,
                    "Lot size": selected.lot_size,
                }]),
                width="stretch",
                hide_index=True,
            )
            st.caption("The Tick Engine can now use the returned instrument key instead of a manually entered token.")
    option_map = st.session_state.get("upstox_option_map", {})
    all_keys = [underlying_key.strip()] + list(option_map.values())

    if token and underlying_key.strip() and option_map:
        resource_key = token + "|" + feed_mode + "|" + "|".join(all_keys)

        @st.cache_resource(show_spinner=False)
        def get_upstox_feed(cache_key, access_token, instrument_keys, mode):
            feed = UpstoxMarketData(access_token, instrument_keys, mode=mode)
            feed.start()
            return feed

        try:
            feed = get_upstox_feed(resource_key, token, all_keys, feed_mode)
            st.session_state["upstox_feed"] = feed
            status = "🟢 Connected" if feed.connected else "🟡 Connecting"
            st.metric("Upstox feed", status)
            if feed.last_error:
                st.error(f"Upstox feed error: {feed.last_error}")

            snapshot = feed.snapshot()
            if snapshot:
                rows = []
                for label, key in [("Underlying", underlying_key.strip()), *option_map.items()]:
                    tick = snapshot.get(key)
                    if tick:
                        rows.append({
                            "Instrument": label,
                            "LTP": tick.ltp,
                            "Bid": tick.bid_price,
                            "Ask": tick.ask_price,
                            "Volume": tick.volume,
                            "OI": tick.oi,
                            "Tick time": tick.ltt,
                        })
                if rows:
                    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

                underlying_tick = snapshot.get(underlying_key.strip())
                if underlying_tick and underlying_tick.ltp is not None:
                    st.metric("Live underlying", f"{underlying_tick.ltp:,.2f}")

                drained = feed.drain(500)
                if drained:
                    chart_rows = [
                        {"time": pd.to_datetime(t.received_ts, unit="ms"), "ltp": t.ltp}
                        for t in drained
                        if t.instrument_key == underlying_key.strip() and t.ltp is not None
                    ]
                    if chart_rows:
                        chart_df = pd.DataFrame(chart_rows).drop_duplicates("time").set_index("time")
                        st.line_chart(chart_df[["ltp"]], height=280)
                        st.caption("Live Upstox LTP stream. Refresh the page to continue rendering new ticks.")

            if st.button("⏹️ Disconnect Upstox feed", key="disconnect_upstox"):
                feed.stop()
                st.cache_resource.clear()
                st.rerun()
        except ConfigError as exc:
            st.error(str(exc))
    else:
        st.caption("Enter at least one option instrument key and configure the token to start the feed.")

    ui.footer_note(
        "Upstox Live V3 is read-only in this page. TradeALGO does not send orders from the Tick Engine."
    )
    st.stop()

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
