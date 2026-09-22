"""Trade journal, daily P&L report and review."""
import datetime as dt

import pandas as pd
import streamlit as st

from algobot import ui
from algobot.appstate import journal_scope, storage_note
from algobot.charts import pnl_bars
from algobot.journal import (JournalError, behavior_flags, build_daily_report, format_daily_report_html,
                             format_daily_report_text, format_review, journal_rows_from_csv, journal_to_csv,
                             review_stats)


def none_if_zero(x):
    return None if not x else x


ui.setup("Journal and report", "📒")
ui.header("Trade journal", "Write every trade down with a stop and a reason. The notes become the material for "
          "your weekly review together. " + storage_note(), mode="journal:Your record")

with journal_scope() as journal:
    closed_all = journal.closed_between(None, None)
    total = sum(t.net_pnl for t in closed_all)
    today = dt.date.today()
    todays = [t for t in closed_all if t.closed_date == today]
    ui.ticker([("Closed trades", len(closed_all), None), ("Net since start", ui.inr(total, sign=True), ui.tone(total)),
               ("Today", ui.inr(sum(t.net_pnl for t in todays), sign=True), ui.tone(sum(t.net_pnl for t in todays))),
               ("Open positions", len(journal.open_trades()), None)])

    tab_new, tab_close, tab_report, tab_review, tab_backup = st.tabs(
        ["New trade", "Close a trade", "Daily report", "Review", "Backup"])

    with tab_new:
        with st.form("add_trade", clear_on_submit=True):
            instrument = st.text_input("Instrument", placeholder="NIFTY 24500 CE 25-Sep", key="j_instrument")
            c1, c2 = st.columns(2)
            side = c1.selectbox("Side", ["BUY", "SELL"], key="j_side")
            qty = c2.number_input("Quantity (units = lots x lot size)", min_value=1, value=65, step=1, key="j_qty")
            c3, c4, c5 = st.columns(3)
            entry = c3.number_input("Entry price", min_value=0.0, value=0.0, step=0.5, key="j_entry")
            stop = c4.number_input("Stop-loss (0 = none)", min_value=0.0, value=0.0, step=0.5, key="j_stop")
            target = c5.number_input("Target (0 = none)", min_value=0.0, value=0.0, step=0.5, key="j_target")
            setup = st.text_input("Setup (why, in a few words)", placeholder="resistance breakout", key="j_setup")
            notes = st.text_area("Notes", key="j_notes", height=70)
            opened = st.text_input("Opened at (blank = now)", placeholder="2026-09-21 10:15", key="j_opened")
            add_clicked = st.form_submit_button("Save trade", key="j_add")
        if add_clicked:
            try:
                new_id = journal.add_trade(instrument, side, int(qty), float(entry), opened_at=opened.strip() or None,
                                           stop_price=none_if_zero(float(stop)), target_price=none_if_zero(float(target)),
                                           setup=setup, notes=notes)
                st.success(f"Trade #{new_id} recorded.")
                if not none_if_zero(float(stop)):
                    st.warning("No stop-loss was recorded. Trades without a stop are flagged in the daily report.")
            except JournalError as exc:
                st.error(str(exc))

    with tab_close:
        open_trades = journal.open_trades()
        if not open_trades:
            st.info("There are no open trades.")
        else:
            labels = {f"#{t.id}  {t.side} {t.qty}  {t.instrument} @ {t.entry_price:g}": t.id for t in open_trades}
            with st.form("close_trade", clear_on_submit=True):
                which = st.selectbox("Which trade", list(labels), key="j_close_which")
                d1, d2 = st.columns(2)
                exit_price = d1.number_input("Exit price", min_value=0.0, value=0.0, step=0.5, key="j_exit")
                charges = d2.number_input("Total charges for the trade (Rs)", min_value=0.0, value=0.0, step=10.0, key="j_charges")
                lessons = st.text_area("What did you learn?", key="j_lessons", height=70)
                closed = st.text_input("Closed at (blank = now)", placeholder="2026-09-21 14:40", key="j_closed")
                close_clicked = st.form_submit_button("Close trade", key="j_close")
            if close_clicked:
                try:
                    t = journal.close_trade(labels[which], float(exit_price), closed_at=closed.strip() or None,
                                            charges=float(charges), lessons=lessons)
                    r = "" if t.r_multiple is None else f", {t.r_multiple:+.2f}R"
                    st.success(f"Trade #{t.id} closed. Net Rs {t.net_pnl:,.2f}{r}.")
                except JournalError as exc:
                    st.error(str(exc))

    with tab_report:
        day = st.date_input("Day", value=today, key="r_day")
        with st.expander("Your own limits (used to flag broken rules)"):
            k1, k2, k3, k4 = st.columns(4)
            cap = k1.number_input("Capital (Rs)", min_value=0, value=10000, step=1000, key="r_capital")
            mlt = k2.number_input("Max loss per trade (Rs, 0 = none)", min_value=0, value=1000, step=100, key="r_mlt")
            mdl = k3.number_input("Max loss per day (Rs, 0 = none)", min_value=0, value=0, step=100, key="r_mdl")
            mtd = k4.number_input("Max trades per day (0 = none)", min_value=0, value=2, step=1, key="r_mtd")
        report = build_daily_report(journal, day, capital=none_if_zero(cap), max_loss_per_trade=none_if_zero(mlt),
                                    max_daily_loss=none_if_zero(mdl), max_trades_per_day=none_if_zero(mtd))
        st.text(format_daily_report_text(report))
        st.download_button("Download this report (HTML)", format_daily_report_html(report),
                           f"daily_report_{day}.html", "text/html", key="r_download")
        by_day = pd.Series({str(t.closed_date): 0.0 for t in closed_all}, dtype=float)
        for t in closed_all:
            by_day[str(t.closed_date)] += t.net_pnl
        if len(by_day):
            st.markdown("##### Net result by day")
            ui.show_chart(pnl_bars(by_day.sort_index().tail(30), height=200, title="net P&L (Rs)"))

    with tab_review:
        limit_trade, limit_day, limit_trades = st.columns(3)
        rl = limit_trade.number_input("Max loss per trade (Rs, 0 = skip checks)", min_value=0, value=0, step=100, key="rv_mlt")
        rd = limit_day.number_input("Max loss per day (Rs, 0 = skip checks)", min_value=0, value=0, step=100, key="rv_mdl")
        rt = limit_trades.number_input("Max trades per day (0 = skip checks)", min_value=0, value=0, step=1, key="rv_mtd")
        flags = None
        if rl or rd or rt:
            flags = behavior_flags(closed_all, max_loss_per_trade=none_if_zero(rl), max_trades_per_day=none_if_zero(rt),
                                   max_daily_loss=none_if_zero(rd))
        st.text(format_review(review_stats(closed_all), flags))

    with tab_backup:
        st.write("Your journal is " + storage_note().lower() + " Download a copy to keep it safe, or to send to "
                 "someone. You can load a copy back in.")
        st.download_button("Download journal (CSV)", journal_to_csv(journal), "journal.csv", "text/csv", key="j_backup")
        upload = st.file_uploader("Load a journal CSV", type=["csv"], key="j_restore")
        if upload is not None and st.button("Add these trades to the journal", key="j_restore_btn"):
            try:
                added = journal.import_rows(journal_rows_from_csv(upload.getvalue().decode("utf-8")))
                st.success(f"Added {added} trade(s).")
            except (JournalError, UnicodeDecodeError) as exc:
                st.error(f"Could not load that file: {exc}")
ui.footer_note()
