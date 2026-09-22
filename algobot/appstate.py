"""Where the app keeps its data, and who may look at it.

Two ways to run it:

  LOCAL   (default): your journal and experiment log are files on your own computer.
  HOSTED  (ALGOBOT_HOSTED=1): the app runs on a server shared by visitors, so nothing is
          written to shared files. Each visitor's journal lives only in their own browser
          session, with download/upload buttons to keep it. This stops one visitor from ever
          seeing another's trades.

Set ALGOBOT_PASSWORD (or a "password" secret) to put a password screen in front of every
page. Do this for anything reachable from the internet. The app never asks for broker
passwords or API keys, in either mode.
"""
from __future__ import annotations

import hmac
import os
import time
from contextlib import contextmanager

import streamlit as st

from .experiments import ExperimentLog
from .journal import Journal


def _secret(name: str):
    try:
        return st.secrets.get(name)
    except Exception:            # no secrets file: perfectly normal
        return None


def is_hosted() -> bool:
    flag = os.environ.get("ALGOBOT_HOSTED") or _secret("hosted")
    return str(flag).strip().lower() in ("1", "true", "yes")


def configured_password():
    return os.environ.get("ALGOBOT_PASSWORD") or _secret("password")


def password_gate(max_attempts: int = 5) -> None:
    """Stop the page with a password screen unless a password is set and has been entered."""
    password = configured_password()
    if not password or st.session_state.get("_ab_authed"):
        return
    st.markdown("<div style='max-width:420px;margin:12vh auto 0 auto'>"
                "<h2 style='margin-bottom:0'>ALGOBOT</h2><p style='color:#8B98A9'>Private trading desk. "
                "Enter the password you were given.</p></div>", unsafe_allow_html=True)
    attempts = st.session_state.get("_ab_attempts", 0)
    left, mid, right = st.columns([1, 1.2, 1])
    with mid:
        if attempts >= max_attempts:
            st.error("Too many wrong tries in this session. Close the tab and open the link again later.")
            st.stop()
        with st.form("ab_login"):
            entered = st.text_input("Password", type="password", key="ab_pw")
            submitted = st.form_submit_button("Enter", key="ab_login_btn")
        if submitted:
            if hmac.compare_digest(entered.encode("utf-8"), str(password).encode("utf-8")):
                st.session_state["_ab_authed"] = True
                st.session_state["_ab_attempts"] = 0
                st.rerun()
            st.session_state["_ab_attempts"] = attempts + 1
            time.sleep(1.0)                                   # slows down guessing
            st.error("That password is not right.")
    st.stop()


@contextmanager
def journal_scope():
    """The journal for this visitor: a file locally, or an in-session store when hosted."""
    if is_hosted():
        journal = st.session_state.get("_ab_journal")
        if journal is None:
            journal = Journal(":memory:", check_same_thread=False)
            st.session_state["_ab_journal"] = journal
        yield journal
    else:
        journal = Journal(os.environ.get("ALGOBOT_JOURNAL", "journal.db"))
        try:
            yield journal
        finally:
            journal.close_db()


@contextmanager
def experiments_scope():
    if is_hosted():
        log = st.session_state.get("_ab_experiments")
        if log is None:
            log = ExperimentLog(":memory:", check_same_thread=False)
            st.session_state["_ab_experiments"] = log
        yield log
    else:
        log = ExperimentLog(os.environ.get("ALGOBOT_EXPERIMENTS", "experiments.db"))
        try:
            yield log
        finally:
            log.close_db()


def storage_note() -> str:
    if is_hosted():
        return "Kept only while this browser tab is open. Download your journal to keep it."
    return f"Saved on this computer in {os.environ.get('ALGOBOT_JOURNAL', 'journal.db')}."
