"""What a bought option is up against, and how likely a losing streak is to wreck a small account."""
import streamlit as st

from algobot import ui
from algobot.charts import payoff_chart
from algobot.options import breakeven_analysis, format_breakeven, payoff_curve
from algobot.ruin import format_ruin, simulate_ruin
from algobot.sizing import NIFTY_LOT_SIZE

ui.setup("Option breakeven and ruin", "⏳")
ui.header("Option breakeven and risk of ruin", "Two questions to answer before trading: how far must the market move just for an "
          "option to break even, and how likely is a normal losing streak to wreck the account? Estimates only. Nothing is "
          "sent to any broker.", mode="research:Estimates")

tab_be, tab_ruin = st.tabs(["1. Option breakeven", "2. Risk of ruin"])

with tab_be:
    st.write("Take the strike, days to expiry, implied volatility (IV) and the ask from your broker's option chain.")
    a, b, c = st.columns(3)
    spot = a.number_input("Index level now", min_value=1.0, value=24500.0, step=50.0, key="be_spot")
    strike = b.number_input("Strike", min_value=1.0, value=24500.0, step=50.0, key="be_strike")
    kind = c.selectbox("Type", ["CE", "PE"], key="be_kind")
    d, e, f = st.columns(3)
    days = d.number_input("Calendar days to expiry", min_value=0.1, value=3.0, step=0.5, key="be_days")
    iv = e.number_input("Implied volatility (%)", min_value=0.5, value=14.0, step=0.5, key="be_iv")
    hold = f.number_input("Days you plan to hold", min_value=0.0, value=1.0, step=0.5, key="be_hold")
    g, h, i = st.columns(3)
    entry_premium = g.number_input("Actual ask you would pay (0 = use model estimate)", min_value=0.0, value=0.0,
                                   step=0.05, key="be_entry")
    spread = h.number_input("Bid-ask gap (premium points)", min_value=0.0, value=0.5, step=0.05, key="be_spread")
    charges = i.number_input("Round-trip charges for one lot (Rs)", min_value=0.0, value=100.0, step=10.0, key="be_charges")
    iv_change = st.number_input("IV change while you hold (points, negative = crush)", value=0.0, step=0.5, key="be_ivchg")
    try:
        res = breakeven_analysis(spot=spot, strike=strike, days_to_expiry=days, iv_pct=iv, kind=kind,
                                 holding_days=hold, lot_size=NIFTY_LOT_SIZE, spread_per_unit=spread,
                                 charges_round_trip=charges, iv_change_pct=iv_change,
                                 entry_premium=entry_premium or None)
    except ValueError as exc:
        st.error(str(exc))
    else:
        be = res["breakeven_points"]
        m1, m2, m3 = st.columns(3)
        m1.metric("Entry premium used", f"{res['premium']:,.2f}")
        if entry_premium == 0:
            st.warning("No actual ask was entered. The entry premium is a model estimate, not a tradable quote.")
        m2.metric("Time decay per day (one lot, Rs)", f"{res['theta_per_day_per_lot']:,.0f}")
        m3.metric("Points to break even", "not reachable" if be == float("inf") else f"{be:,.1f}")
        if res["one_sigma_move"]:
            st.caption(f"A typical move over your {hold:g}-day hold is about {res['one_sigma_move']:,.0f} index points.")
        st.markdown("##### Profit or loss per lot if Nifty has moved by X points when you sell")
        curve = payoff_curve(spot, strike, days, iv, kind, hold, NIFTY_LOT_SIZE, entry_premium or None, spread, charges, iv_change)
        ui.show_chart(payoff_chart(curve, None if be == float("inf") else be if kind == "CE" else -be))
        st.caption("Green above zero is profit, red below is loss. The flat stretch on the left of a call is the most you can lose.")
        st.code(format_breakeven(res, kind, NIFTY_LOT_SIZE), language="text")

with tab_ruin:
    st.write("Even a strategy with a real edge has losing streaks. Whether the account survives depends on how "
             "much is risked per trade.")
    a, b, c = st.columns(3)
    win_rate = a.number_input("Win rate (%)", min_value=1, max_value=99, value=45, key="ru_win")
    reward = b.number_input("Average win as a multiple of the amount risked (R)", min_value=0.1, value=1.5, step=0.1, key="ru_reward")
    cost_r = c.number_input("Charges per trade, in R (Rs 100 on Rs 1,000 risked = 0.1)", min_value=0.0, value=0.1, step=0.05, key="ru_cost")
    d, e, f = st.columns(3)
    risk_pct = d.number_input("Risk per trade (% of starting capital)", min_value=0.1, max_value=99.0, value=10.0, step=0.5, key="ru_risk")
    trades = e.number_input("Number of trades", min_value=10, max_value=1000, value=100, step=10, key="ru_trades")
    ruin_pct = f.number_input("Count this loss of the account as ruin (%)", min_value=5, max_value=95, value=50, key="ru_ruin")
    try:
        out = simulate_ruin(win_rate / 100.0, reward, risk_pct, int(trades), float(ruin_pct), cost_r, n_paths=4000)
    except ValueError as exc:
        st.error(str(exc))
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Average result per trade (R)", f"{out['expected_value_r']:+.2f}")
        m2.metric(f"Chance of losing {ruin_pct}% at some point", f"{out['p_ruin']:.0%}")
        m3.metric("Chance of finishing with a loss", f"{out['p_loss']:.0%}")
        st.code(format_ruin(out, win_rate / 100.0, reward, risk_pct, int(trades), float(ruin_pct)), language="text")
ui.footer_note()
