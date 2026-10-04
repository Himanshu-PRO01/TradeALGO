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
from .kill_switch import KillSwitch
from .paper_trading import PaperLog
from .sandbox_rehearsal import RehearsalLog
from .signal_alerts import AlertLog
from .saved_strategies import SavedStrategyLibrary


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
    """Render the branded TradeALGO login when a hosted secret is configured."""
    secret = configured_password()
    if not secret or st.session_state.get("_ab_authed"):
        return

    with st.container(key="auth_card"):
        left, right = st.columns([1.05, .95], gap="small", vertical_alignment="center")
        with left:
            st.markdown("""
            <div class="ta-auth-brand">
              <div class="ta-auth-logo">TRADE<span>ALGO</span></div>
              <div class="ta-auth-kicker">Systematic trading research</div>
              <div class="ta-auth-title">Build ideas.<br>Test them.<br>Trust the evidence.</div>
              <div class="ta-auth-copy">A focused workspace for strategy research, backtesting, robustness checks and paper-to-sandbox rehearsal.</div>
              <div class="ta-auth-features">
                <div class="ta-auth-feature"><span class="ta-auth-check">✓</span> Research before execution</div>
                <div class="ta-auth-feature"><span class="ta-auth-check">✓</span> Backtest with transparent assumptions</div>
                <div class="ta-auth-feature"><span class="ta-auth-check">✓</span> Connect execution through OpenAlgo</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        with right:
            st.markdown("""
            <div class="ta-auth-form-head">
              <h2>Welcome back</h2>
              <div class="ta-auth-sub">Sign in to continue to your TradeALGO workspace.</div>
            </div>
            """, unsafe_allow_html=True)

            attempts = st.session_state.get("_ab_attempts", 0)
            if attempts >= max_attempts:
                st.error("Too many incorrect attempts in this session. Close the tab and try again.")
                st.stop()
            with st.form("ab_login"):
                entered = st.text_input("Workspace access", type="password", key="ab_pw", placeholder="Enter your access key")
                submitted = st.form_submit_button("Continue to TradeALGO", key="ab_login_btn", use_container_width=True)

            from .dom_fixups import fix_password_autocomplete
            fix_password_autocomplete()
            if submitted:
                if hmac.compare_digest(entered.encode("utf-8"), str(secret).encode("utf-8")):
                    st.session_state["_ab_authed"] = True
                    st.session_state["_ab_attempts"] = 0
                    st.rerun()
                st.session_state["_ab_attempts"] = attempts + 1
                time.sleep(1.0)
                st.error("That access key is not correct. Please try again.")

            st.markdown('<div class="ta-auth-note">🔒 Your TradeALGO workspace is protected.</div><div class="ta-auth-footer">TRADEALGO · Research, validation and paper trading</div>', unsafe_allow_html=True)
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


@contextmanager
def kill_switch_scope():
    """The kill switch is intentionally global and persistent, not scoped per visitor like the
    journal or paper log -- it is meant to be the one shared 'stop everything' control."""
    switch = KillSwitch(os.environ.get("ALGOBOT_KILL_SWITCH", "kill_switch.db"))
    try:
        yield switch
    finally:
        switch.close_db()


@contextmanager
def rehearsal_scope():
    """Also global and persistent, like the kill switch: if this state were scoped per browser
    session instead, two people opening two tabs on the same deployment could each think the
    position is flat and both fire a real (sandbox) entry order -- exactly the duplicate-order
    bug this module exists to prevent."""
    log = RehearsalLog(os.environ.get("ALGOBOT_REHEARSAL_LOG", "sandbox_rehearsal.db"))
    try:
        yield log
    finally:
        log.close_db()


@contextmanager
def alert_scope():
    """Also global and persistent, like the kill switch and rehearsal log: two
    browser tabs must agree on whether an entry alert was already sent for the
    current position, or the brother gets duplicate WhatsApp pings for one signal."""
    log = AlertLog(os.environ.get("ALGOBOT_ALERT_LOG", "signal_alerts.db"))
    try:
        yield log
    finally:
        log.close_db()


@contextmanager
def paper_scope():
    """The paper-trading log for this visitor: a file locally, or an in-session store when hosted."""
    if is_hosted():
        log = st.session_state.get("_ab_paper_log")
        if log is None:
            log = PaperLog(":memory:", check_same_thread=False)
            st.session_state["_ab_paper_log"] = log
        yield log
    else:
        log = PaperLog(os.environ.get("ALGOBOT_PAPER_LOG", "paper_trades.db"))
        try:
            yield log
        finally:
            log.close_db()



@contextmanager
def strategies_scope():
    """Saved strategy/backtest library: per-user in hosted mode, local file otherwise."""
    if is_hosted():
        library = st.session_state.get("_ab_strategy_library")
        if library is None:
            library = SavedStrategyLibrary(":memory:", check_same_thread=False)
            st.session_state["_ab_strategy_library"] = library
        yield library
    else:
        library = SavedStrategyLibrary(os.environ.get("ALGOBOT_STRATEGIES", "strategies.db"))
        try:
            yield library
        finally:
            library.close_db()

def storage_note() -> str:
    if is_hosted():
        return "Kept only while this browser tab is open. Download your journal to keep it."
    return f"Saved on this computer in {os.environ.get('ALGOBOT_JOURNAL', 'journal.db')}."
