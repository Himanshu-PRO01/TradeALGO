"""Deployment status page: make it obvious whether this copy is running on Streamlit."""

import os

import streamlit as st

from algobot import ui
from algobot.appstate import is_hosted

ui.setup("Deployment Status", "🚀")
ui.header(
    "Deployment Status",
    "A simple check showing whether you are viewing the hosted Streamlit copy or running the app locally.",
    mode="system:Deployment",
)

configured_hosted = is_hosted()
try:
    app_url = st.context.url
except Exception:
    app_url = ""

# Streamlit Community Cloud apps normally use a *.streamlit.app URL.
# Keep ALGOBOT_HOSTED as a fallback for custom domains and other hosted setups.
hosted_by_url = ".streamlit.app" in app_url.lower()
hosted = configured_hosted or hosted_by_url

if hosted:
    st.success("🟢 DEPLOYED — this page is running in hosted mode (Streamlit).")
else:
    st.info("🔵 LOCAL — this copy is running on a computer, not in hosted mode.")

left, right = st.columns(2)

with left:
    st.markdown("### Current app")
    st.metric("Environment", "DEPLOYED / STREAMLIT" if hosted else "LOCAL")
    st.caption(
        "Deployment is detected from the Streamlit app URL or ALGOBOT_HOSTED. "
        "This page does not connect to a broker or place orders."
    )

with right:
    st.markdown("### Build information")
    commit = (
        os.environ.get("GIT_COMMIT_SHA")
        or os.environ.get("GIT_COMMIT")
        or os.environ.get("COMMIT_SHA")
    )
    if commit:
        st.code(commit[:12], language="text")
        st.caption("Build commit reported by the hosting environment.")
    else:
        st.code("Not reported by hosting environment", language="text")
        st.caption("The hosting environment did not expose a Git commit variable to this app.")

if app_url:
    st.caption(f"App URL: {app_url}")

st.divider()

st.markdown("### What this tells you")
ui.check_row(
    "PASS" if hosted else "WARN",
    "Hosted copy detected" if hosted else "Local copy detected",
    "The app URL is used as a deployment signal; an explicit hosted setting is also accepted.",
)
ui.check_row(
    "PASS",
    "Live orders remain OFF",
    "Deployment status does not enable broker access or real order placement.",
)

st.caption(
    "Tip: after pushing a new GitHub commit, refresh this page. If the app still shows the old build information, "
    "Streamlit may still be restarting/updating the app."
)

ui.footer_note()
