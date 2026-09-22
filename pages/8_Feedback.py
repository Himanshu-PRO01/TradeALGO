"""Suggestions: what to change, in trading words. Saved on this computer, or in this tab when hosted."""
import os

import streamlit as st

from algobot import ui
from algobot.appstate import is_hosted
from algobot.feedback import AREAS, KINDS, PRIORITIES, FeedbackError, FeedbackStore

ui.setup("Feedback", "💬")
ui.header("Feedback", "You know trading better than the developer does. Tell him what is wrong, confusing or missing, in "
          "trading words. Then send him the text or the file.", mode="journal:Your suggestions")

if "feedback_store" not in st.session_state:
    st.session_state["feedback_store"] = FeedbackStore(None if is_hosted() else os.environ.get("ALGOBOT_FEEDBACK", "feedback.csv"))
store = st.session_state["feedback_store"]

left, right = st.columns([1.1, 1], gap="large")
with left:
    st.markdown("#### Add a suggestion")
    with st.form("fb_form", clear_on_submit=True):
        name = st.text_input("Your name (optional)", key="fb_name")
        a, b, c = st.columns(3)
        area = a.selectbox("Which page?", AREAS, key="fb_area")
        kind = b.selectbox("What kind?", KINDS, key="fb_kind")
        priority = c.selectbox("How important?", PRIORITIES, key="fb_priority")
        message = st.text_area("What should change?", height=120, key="fb_message",
                               placeholder="For example: the option chain should show open interest, like on Upstox.")
        example = st.text_area("An example (optional)", height=80, key="fb_example",
                               placeholder="A real trade, a number that does not match your broker, a screenshot description...")
        submitted = st.form_submit_button("Save suggestion", key="fb_submit")
    if submitted:
        try:
            store.add(name, area, kind, priority, message, example)
            st.success("Saved. Thank you.")
        except FeedbackError as exc:
            st.error(str(exc))
with right:
    st.markdown(f"#### Your suggestions ({len(store.items)})")
    if not store.items:
        st.info("Nothing yet.")
    else:
        for item in reversed(store.items[-6:]):
            st.markdown(f"**[{item.priority}] {item.area}**: {item.kind}")
            st.caption(item.message)
        st.markdown("##### Send them to the developer")
        st.text_area("Copy this into WhatsApp", store.to_text(), height=180, key="fb_share")
        st.download_button("Download as a file (CSV)", store.to_csv(), "algobot_feedback.csv", "text/csv", key="fb_download")
        if not is_hosted():
            st.caption("Also saved on this computer in feedback.csv.")
        else:
            st.caption("Hosted mode: suggestions live only in this tab. Copy the text or download the file before closing it.")
ui.footer_note()
