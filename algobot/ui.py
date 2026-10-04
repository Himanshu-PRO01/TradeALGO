"""The look and feel of every page: a dark trading desk.

Each page starts with `ui.setup(...)` (which must be the first Streamlit call) and then `ui.header(...)`.
Colours come from palette.py so the CSS and the charts always agree: green is up, profit and buy; red is
down, loss and sell; amber means caution or practice.
"""
from __future__ import annotations

import pathlib
import sys
from html import escape
from typing import Iterable, Optional

import streamlit as st

try:
    import streamlit.components.v2 as _components_v2
except ImportError:  # Older Streamlit versions simply skip the gesture.
    _components_v2 = None

from . import __version__
from .appstate import is_hosted, password_gate
from .palette import BG, BLUE, BORDER, DOWN, MUTED, PANEL, TEXT, UP, WARN


_SWIPE_MENU_COMPONENT = None


def is_dark_mode() -> bool:
    """Return the current TradeALGO appearance preference."""
    return st.session_state.get("tradealgo_theme", "light") == "dark"



def _swipe_menu_component():
    """Install a tiny mobile edge-swipe listener without changing trading logic."""
    global _SWIPE_MENU_COMPONENT
    if _components_v2 is None:
        return None
    if _SWIPE_MENU_COMPONENT is None:
        _SWIPE_MENU_COMPONENT = _components_v2.component(
            name="algobot_mobile_swipe_menu",
            html="",
            css="",
            js="""
            export default function() {
                let startX = 0;
                let startY = 0;

                const onStart = (event) => {
                    if (window.matchMedia("(min-width: 769px)").matches) return;
                    if (!event.touches || event.touches.length !== 1) return;
                    startX = event.touches[0].clientX;
                    startY = event.touches[0].clientY;
                };

                const onEnd = (event) => {
                    if (window.matchMedia("(min-width: 769px)").matches) return;
                    if (!event.changedTouches || event.changedTouches.length !== 1) return;

                    const endX = event.changedTouches[0].clientX;
                    const endY = event.changedTouches[0].clientY;
                    const deltaX = endX - startX;
                    const deltaY = Math.abs(endY - startY);

                    // Only a deliberate right-swipe from the left screen edge opens the menu.
                    if (startX > 28 || deltaX < 60 || deltaY > 70) return;

                    const sidebar =
                        document.querySelector('[data-testid="stSidebar"]') ||
                        document.querySelector("section.stSidebar");

                    const isOpen = sidebar?.getAttribute("aria-expanded") === "true";
                    if (isOpen) return;

                    const button =
                        document.querySelector('[data-testid="stSidebarCollapseButton"] button') ||
                        document.querySelector('button[aria-label*="sidebar" i]');

                    if (button) button.click();
                };

                document.addEventListener("touchstart", onStart, {passive: true});
                document.addEventListener("touchend", onEnd, {passive: true});

                return () => {
                    document.removeEventListener("touchstart", onStart);
                    document.removeEventListener("touchend", onEnd);
                };
            }
            """,
        )
    return _SWIPE_MENU_COMPONENT


CSS = """
<style>
:root{--ta-green:#318616;--ta-ink:#171717;--ta-muted:#4d5761;--ta-surface:#fff;--ta-raised:#f7f8f6;--ta-border:#e5e7eb}
body,.stApp{font-family:Lexend,sans-serif}
.block-container,
[data-testid="stMainBlockContainer"],
.stMainBlockContainer {
    padding-top: 1rem !important;
    padding-bottom: 3rem !important;
}
[data-testid="stToolbar"] { display:none !important; }
header[data-testid="stHeader"] {
    height: 0 !important;
    min-height: 0 !important;
    background: transparent !important;
}
.ta-auth-shell{min-height:0;display:block;padding:18px 16px 28px}
.st-key-auth_card{width:min(980px,100%);margin:0 auto;background:var(--ta-surface);border:1px solid var(--ta-border);border-radius:24px;overflow:hidden;box-shadow:0 18px 55px rgba(20,30,20,.1);padding:0}
.st-key-auth_card [data-testid="stHorizontalBlock"]{gap:0!important}
.ta-auth-brand{height:100%;padding:46px 48px;background:linear-gradient(145deg,#f2f8ed 0%,#fff 72%);border-right:1px solid var(--ta-border)}
.ta-auth-logo{font-size:1.55rem;font-weight:900;letter-spacing:-.04em;color:var(--ta-ink)}.ta-auth-logo span{color:var(--ta-green)}
.ta-auth-kicker{margin-top:58px;color:var(--ta-green);font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:.12em}
.ta-auth-title{margin:12px 0 14px;color:var(--ta-ink);font-size:clamp(2rem,4vw,3.35rem);line-height:1.04;font-weight:850;letter-spacing:-.055em}
.ta-auth-copy{max-width:470px;color:var(--ta-muted);font-size:1rem;line-height:1.7}.ta-auth-features{margin-top:28px;display:grid;gap:10px}
.ta-auth-feature{display:flex;gap:10px;align-items:center;color:var(--ta-ink);font-size:.9rem;font-weight:600}
.ta-auth-check{width:24px;height:24px;border-radius:999px;display:grid;place-items:center;background:#eaf5e5;color:var(--ta-green);font-weight:900}
.ta-auth-form{padding:54px}.st-key-ab_login{padding:0 54px 54px;max-width:470px;margin:0 auto}.st-key-ab_login_btn button{background:#318616!important;color:#fff!important;border-color:#318616!important;font-weight:800!important;border-radius:12px!important;min-height:48px!important}.st-key-ab_login_btn button:hover{background:#24630f!important;border-color:#24630f!important}.st-key-ab_pw input{border-radius:12px!important;min-height:48px!important}.ta-auth-form h2,.ta-auth-form-head h2{margin:0 0 7px;color:var(--ta-ink);font-size:1.65rem;letter-spacing:-.035em}
.ta-auth-form .ta-auth-sub,.ta-auth-form-head .ta-auth-sub{color:var(--ta-muted);margin-bottom:24px;font-size:.9rem;line-height:1.5}.ta-auth-note{margin-top:16px;padding:12px 14px;border-radius:12px;background:var(--ta-raised);color:var(--ta-muted);font-size:.78rem;line-height:1.5}
.ta-auth-footer{margin-top:24px;text-align:center;color:#6b7280;font-size:.72rem}
@media(max-width:760px){.st-key-auth_card [data-testid="stHorizontalBlock"]{flex-direction:column!important}.ta-auth-brand{padding:30px 24px;border-right:0;border-bottom:1px solid var(--ta-border)}.ta-auth-kicker{margin-top:30px}.ta-auth-title{font-size:2.15rem}.ta-auth-form-head{padding:30px 24px 6px}.st-key-ab_login{padding:10px 24px 0}
}
.block-container { padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1500px; }
h1, h2, h3 { letter-spacing: -0.01em; }

/* Premium TradeALGO utility-bar logo */
.st-key-utility_bar .ta-utility-brand {
    display:flex;
    align-items:center;
    gap:10px;
    min-width:220px;
    margin-right:auto !important;
    margin-left:0 !important;
    color:#F4F7FB;
}
.st-key-utility_bar .ta-logo-svg {
    width:38px;
    height:38px;
    flex:0 0 38px;
    filter:drop-shadow(0 5px 12px rgba(37,99,235,.22));
}
.st-key-utility_bar .ta-utility-wordmark {
    display:flex;
    flex-direction:column;
    justify-content:center;
    line-height:1;
}
.st-key-utility_bar .ta-utility-name {
    color:#F4F7FB;
    font-size:1rem;
    font-weight:900;
    letter-spacing:.025em;
}
.st-key-utility_bar .ta-utility-name span {
    color:#20D9A0;
}
.st-key-utility_bar .ta-utility-tag {
    margin-top:4px;
    color:#7F8DA0;
    font-size:.5rem;
    font-weight:800;
    letter-spacing:.22em;
}
.st-key-utility_bar .st-key-utility_actions {
    margin-left:auto;
    flex:0 0 auto;
}
[data-testid="stSidebar"] {
    background: #121923;
    border-right: 1px solid #1F2A37;
    box-shadow: 10px 0 34px rgba(0,0,0,.12);
}
[data-testid="stSidebar"] > div:first-child {
    height: 100vh;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-width: thin;
    scrollbar-color: #344255 transparent;
}
[data-testid="stSidebar"] > div:first-child::-webkit-scrollbar { width: 5px; }
[data-testid="stSidebar"] > div:first-child::-webkit-scrollbar-track { background: transparent; }
[data-testid="stSidebar"] > div:first-child::-webkit-scrollbar-thumb { background: #344255; border-radius: 999px; }
[data-testid="stSidebarNav"] { display:none; }
.ab-menu-head {
    position: sticky;
    top: 0;
    z-index: 50;
    padding: 14px 8px 16px;
    margin: 0 2px 12px;
    border-bottom: 1px solid #263242;
    background: linear-gradient(180deg,#121923 88%,rgba(18,25,35,.92) 100%);
    backdrop-filter: blur(10px);
}
.ab-menu-brand {
    display:flex;
    align-items:center;
    gap:6px;
    font-weight:900;
    letter-spacing:.08em;
    font-size:1.08rem;
    color:#F4F7FB;
}
.ab-menu-brand::before {
    content:"";
    width:9px;
    height:9px;
    border-radius:50%;
    background:#16C784;
    box-shadow:0 0 0 4px rgba(22,199,132,.10), 0 0 14px rgba(22,199,132,.28);
}
.ab-menu-brand span { color:#16C784; }
.ab-menu-status {
    margin-top:7px;
    padding-left:15px;
    color:#7F8DA0;
    font-size:.68rem;
    font-weight:600;
    letter-spacing:.05em;
}
.ab-menu-section {
    display:flex;
    align-items:center;
    gap:8px;
    color:#718096;
    font-size:.62rem;
    font-weight:800;
    letter-spacing:.14em;
    text-transform:uppercase;
    margin:18px 8px 6px;
}
.ab-menu-section::after {
    content:"";
    height:1px;
    flex:1;
    background:#202B39;
}

/* Premium sidebar navigation */
[data-testid="stSidebar"] [data-testid="stPageLink"] {
    margin:2px 0;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    position:relative;
    display:flex;
    align-items:center;
    min-height:42px;
    padding:9px 12px !important;
    border:1px solid transparent;
    border-radius:10px;
    background:transparent;
    color:#AAB6C5 !important;
    font-size:.88rem;
    font-weight:600;
    letter-spacing:0;
    transition:background .16s ease, color .16s ease, border-color .16s ease, transform .16s ease;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background:rgba(255,255,255,.045);
    border-color:#273444;
    color:#F4F7FB !important;
    transform:translateX(2px);
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
    background:linear-gradient(90deg,rgba(59,130,246,.14),rgba(59,130,246,.045));
    border-color:rgba(59,130,246,.20);
    color:#F4F7FB !important;
    box-shadow:inset 3px 0 0 #3B82F6;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"]::after {
    content:"";
    width:5px;
    height:5px;
    margin-left:auto;
    border-radius:50%;
    background:#3B82F6;
    box-shadow:0 0 9px rgba(59,130,246,.65);
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a p {
    margin:0 !important;
    color:inherit !important;
    font-size:.88rem;
    font-weight:600;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a span {
    width:24px;
    margin-right:3px;
    font-size:1rem;
    text-align:center;
    opacity:.9;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] span {
    opacity:1;
}

/* Sidebar footer/status */
[data-testid="stSidebar"] .stCaption {
    margin:16px 4px 4px;
    padding:11px 12px;
    border:1px solid #202B39;
    border-radius:10px;
    background:rgba(255,255,255,.025);
    color:#7F8DA0 !important;
    font-size:.68rem;
    line-height:1.45;
}

/* Mobile menu */
@media (max-width:768px) {
    [data-testid="stSidebar"] [data-testid="stPageLink"] a {
        min-height:46px;
        border-radius:11px;
    }
}


/* mobile-first trading UX */
@media (max-width: 768px) {
    .block-container {
        padding: .65rem .75rem 3rem;
        max-width: 100%;
    }
    .ab-top {
        align-items: flex-start;
        gap: 7px;
        padding: 3px 0 8px;
        margin-bottom: 6px;
    }
    .ab-brand {
        font-size: .82rem;
        letter-spacing: .12em;
    }
    .ab-pills {
        width: 100%;
        gap: 5px;
        overflow-x: auto;
        flex-wrap: nowrap;
        padding-bottom: 2px;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }
    .ab-pills::-webkit-scrollbar { display:none; }
    .ab-pill {
        flex: 0 0 auto;
        padding: 4px 9px;
        font-size: 10px;
    }
    h1 { font-size: 1.65rem !important; }
    h2 { font-size: 1.35rem !important; }
    h3 { font-size: 1.05rem !important; }
    .ab-hero {
        padding: 18px 16px;
        border-radius: 16px;
        margin-bottom: 12px;
    }
    .ab-hero h2 { font-size: 1.45rem; }
    .ab-card {
        min-height: auto;
        padding: 14px;
        border-radius: 12px;
    }
    .ab-nav-card {
        min-height: auto;
        padding: 14px;
    }
    .ab-strip {
        gap: 0;
        padding: 9px 10px;
        border-radius: 11px;
        overflow-x: auto;
        flex-wrap: nowrap;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }
    .ab-strip::-webkit-scrollbar { display:none; }
    .ab-strip > div {
        flex: 0 0 auto;
        min-width: 125px;
        padding-right: 16px;
    }
    .ab-strip .val { font-size: .96rem; }
    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button {
        width: 100%;
        min-height: 46px;
        border-radius: 11px;
    }
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea,
    .stDateInput input,
    .stTimeInput input {
        font-size: 16px !important;
        min-height: 44px;
    }
    .stSelectbox [data-baseweb="select"],
    .stMultiSelect [data-baseweb="select"] {
        min-height: 44px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        overflow-x: auto;
        flex-wrap: nowrap;
        scrollbar-width: none;
    }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display:none; }
    .stTabs [data-baseweb="tab"] {
        flex: 0 0 auto;
        padding: 9px 12px;
        font-size: .84rem;
    }
    [data-testid="stDataFrame"] {
        max-width: 100%;
        overflow-x: auto;
    }
    [data-testid="stSidebar"] {
        min-width: min(88vw, 340px);
        max-width: min(88vw, 340px);
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: .65rem;
    }
    [data-testid="stSidebar"] [data-testid="stPageLink"] {
        margin: 5px 0;
    }
    [data-testid="stSidebar"] [data-testid="stPageLink"] a {
        min-height: 48px;
        padding: 10px 12px !important;
        border-radius: 12px;
        font-size: .92rem;
    }
    .ab-menu-section {
        margin: 12px 6px 4px;
    }
    .stCaption {
        line-height: 1.4;
    }
    /* Streamlit columns become easier to scan when their contents are separated. */
    [data-testid="stHorizontalBlock"] {
        gap: .65rem !important;
    }
}
@media (max-width: 430px) {
    .block-container {
        padding-left: .6rem;
        padding-right: .6rem;
    }
    .ab-brand {
        font-size: .76rem;
    }
    .ab-menu-brand {
        font-size: .92rem;
    }
    .ab-menu-status {
        font-size: .66rem;
    }
    .ab-check {
        gap: 8px;
        padding: 9px 10px;
    }
    .ab-check .txt span {
        font-size: .82rem;
    }
    [data-testid="stMetric"] {
        padding: 10px 12px;
    }
}

/* metric cards */
[data-testid="stMetric"] { background: #121923; border: 1px solid #1F2A37; border-radius: 12px; padding: 12px 16px; }
[data-testid="stMetricLabel"] { color: #8B98A9; text-transform: uppercase; font-size: 0.72rem; letter-spacing: .06em; }
[data-testid="stMetricValue"] { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-variant-numeric: tabular-nums; font-weight: 600; }

/* buttons */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
    border-radius: 9px; font-weight: 600; border: 1px solid #1F2A37; }
.st-key-pr_buy button { background: #16C784; color: #03130C; border: 0; }
.st-key-pr_close button { background: #EA3943; color: #fff; border: 0; }
.st-key-pr_buy button:hover { filter: brightness(1.1); }
.st-key-pr_close button:hover { filter: brightness(1.1); }

/* square graphic workflow cards + shadcn-inspired hover previews */
[class*="st-key-workflow_step_"] > button {
    position: relative !important;
    width: 148px !important;
    min-width: 148px !important;
    max-width: 148px !important;
    height: 148px !important;
    min-height: 148px !important;
    padding: 12px 8px !important;
    border-radius: 18px !important;
    line-height: 1.15 !important;
    white-space: pre-line !important;
    text-align: center !important;
    font-size: .86rem !important;
    overflow: hidden !important;
    transition: transform .16s ease, border-color .16s ease, box-shadow .16s ease !important;
}
[class*="st-key-workflow_step_"] > button:hover {
    transform: translateY(-3px) !important;
    border-color: #3B82F6 !important;
    box-shadow: 0 8px 22px rgba(0,0,0,.24), inset 0 0 0 1px rgba(59,130,246,.18) !important;
    z-index: 20 !important;
}
[class*="st-key-workflow_step_"] > button p {
    white-space: pre-line !important;
    line-height: 1.2 !important;
    margin: 0 !important;
}

/* HoverCard behavior: preview the step description on hover/focus.
   This mirrors shadcn HoverCard's trigger -> content pattern while keeping
   navigation native to Streamlit. */
[class*="st-key-workflow_step_"] > button::after {
    position: absolute !important;
    left: 8px !important;
    right: 8px !important;
    bottom: 8px !important;
    min-height: 52px !important;
    box-sizing: border-box !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 8px 9px !important;
    border: 1px solid rgba(59,130,246,.35) !important;
    border-radius: 11px !important;
    background: linear-gradient(180deg, rgba(17,25,35,.97), rgba(10,15,22,.98)) !important;
    color: #AAB7C7 !important;
    font-size: .70rem !important;
    font-weight: 600 !important;
    line-height: 1.25 !important;
    text-align: center !important;
    white-space: normal !important;
    opacity: 0 !important;
    transform: translateY(7px) !important;
    pointer-events: none !important;
    transition: opacity .14s ease, transform .14s ease !important;
    z-index: 30 !important;
    box-shadow: 0 10px 26px rgba(0,0,0,.38) !important;
}
[class*="st-key-workflow_step_"] > button:hover::after,
[class*="st-key-workflow_step_"] > button:focus-visible::after {
    opacity: 1 !important;
    transform: translateY(0) !important;
}
.st-key-workflow_step_0 > button::after { content: "Start with the trading idea and define what you want to test."; }
.st-key-workflow_step_1 > button::after { content: "Turn the idea into clear, measurable entry and exit rules."; }
.st-key-workflow_step_2 > button::after { content: "Use AI to research, refine, and challenge the strategy."; }
.st-key-workflow_step_3 > button::after { content: "Run the strategy on historical market data and inspect results."; }
.st-key-workflow_step_4 > button::after { content: "Test controlled variations to see how robust the strategy is."; }
.st-key-workflow_step_5 > button::after { content: "Challenge the evidence with risk and robustness checks."; }
.st-key-workflow_step_6 > button::after { content: "Rehearse trades with fake money before using a broker."; }
.st-key-workflow_step_7 > button::after { content: "Test broker integration safely in the sandbox environment."; }
.st-key-workflow_step_8 > button::after { content: "Run the full paper-to-sandbox rehearsal before execution."; }
.st-key-workflow_step_9 > button::after { content: "Controlled execution stage. Live orders remain locked by default."; }

@media (max-width:768px) {
    [class*="st-key-workflow_step_"] > button {
        width: 132px !important;
        min-width: 132px !important;
        max-width: 132px !important;
        height: 132px !important;
        min-height: 132px !important;
        font-size: .8rem !important;
    }
    [class*="st-key-workflow_step_"] > button::after {
        left: 6px !important;
        right: 6px !important;
        bottom: 6px !important;
        min-height: 48px !important;
        font-size: .66rem !important;
        padding: 7px !important;
    }
}

/* tabs, expanders, dataframes */
.stTabs [data-baseweb="tab"] { font-weight: 600; }
[data-testid="stExpander"] { border: 1px solid #1F2A37; border-radius: 12px; background: #121923; }
[data-testid="stDataFrame"] { border: 1px solid #1F2A37; border-radius: 10px; }

/* mobile menu drawer -- opened from header()'s "☰ Menu" button in the utility
   bar now (one menu entry point, not a separate floating one here too). */
@media (max-width:768px) {
    .st-key-mobile_menu_drawer {
        position: fixed !important;
        top: 60px !important;
        left: 10px !important;
        right: 10px !important;
        width: auto !important;
        max-height: calc(100vh - 74px) !important;
        overflow-y: auto !important;
        z-index: 100000 !important;
        padding: 16px !important;
        border: 1px solid #263242 !important;
        border-radius: 18px !important;
        background: linear-gradient(180deg,#111923 0%,#0d131b 100%) !important;
        box-shadow: 0 24px 70px rgba(0,0,0,.58) !important;
    }
    .st-key-mobile_menu_drawer [data-testid="stPageLink"] a {
        min-height: 46px !important;
        padding: 10px 12px !important;
        border-radius: 11px !important;
        font-size: .92rem !important;
    }
    .st-key-mobile_menu_drawer [data-testid="stPageLink"] a:hover {
        background: rgba(255,255,255,.06);
    }
}

/* Floating back-to-top control */
.ta-back-to-top {
    position:fixed;
    left:50%;
    right:auto;
    bottom:22px;
    transform:translateX(-50%);
    z-index:99999;
    display:inline-flex;
    align-items:center;
    gap:7px;
    min-height:40px;
    padding:0 13px;
    border:1px solid #2B394A;
    border-radius:999px;
    background:rgba(18,25,35,.94);
    color:#E7EDF5 !important;
    text-decoration:none !important;
    font-size:.76rem;
    font-weight:800;
    letter-spacing:.02em;
    box-shadow:0 10px 30px rgba(0,0,0,.30);
    backdrop-filter:blur(12px);
    transition:transform .16s ease,background .16s ease,border-color .16s ease,box-shadow .16s ease;
}
.ta-back-to-top:hover {
    transform:translateX(-50%) translateY(-2px);
    background:#172231;
    border-color:#3B82F6;
    box-shadow:0 12px 34px rgba(0,0,0,.38),0 0 0 3px rgba(59,130,246,.08);
    color:#fff !important;
}
.ta-back-to-top span { opacity:.78; }

/* Sidebar appearance control */
[data-testid="stSidebar"] .stToggle {
    margin-bottom:4px !important;
}
</style>
"""



LIGHT_CSS = """
<style>
:root {
    color-scheme: light;
}

/* ---------- App surfaces ---------- */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background: #f6f8fb !important;
    color: #172033 !important;
}
[data-testid="stHeader"] {
    background: rgba(246,248,251,.94) !important;
    border-bottom: 1px solid #e2e8f0 !important;
}
[data-testid="stToolbar"] {
    background: transparent !important;
}
.block-container {
    color: #172033 !important;
}

/* ---------- Typography ---------- */
h1, h2, h3, h4, h5, h6,
p, label, [data-testid="stMarkdownContainer"],
[data-testid="stText"], [data-testid="stCaptionContainer"] {
    color: #172033;
}
.stCaption, [data-testid="stCaptionContainer"] {
    color: #64748b !important;
}
a {
    color: #2563eb !important;
}

/* ---------- Sidebar / navigation ---------- */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #dbe3ee !important;
}
[data-testid="stSidebar"] > div:first-child {
    background: #ffffff !important;
}
[data-testid="stSidebar"] > div:first-child::-webkit-scrollbar-thumb { background:#cbd5e1; }
.ab-menu-head {
    background:linear-gradient(180deg,#ffffff 88%,rgba(255,255,255,.94) 100%) !important;
    backdrop-filter:blur(10px);
}
.ab-menu-head {
    border-bottom-color: #e2e8f0 !important;
}
.ab-menu-brand {
    color: #172033 !important;
}
.ab-menu-brand span {
    color: #059669 !important;
}
.ab-menu-status, .ab-menu-section {
    color: #64748b !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    color: #334155 !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: #eef4ff !important;
    color: #1d4ed8 !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
    background: #e8f0ff !important;
    border-left-color: #2563eb !important;
    color: #1d4ed8 !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a p {
    color: inherit !important;
}

/* ---------- Utility / header ---------- */
[data-testid="stHorizontalBlock"] {
    color: #172033;
}
.st-key-utility_bar {
    background: #ffffff !important;
    border-color: #dbe3ee !important;
}
.st-key-utility_bar [data-testid="stCaptionContainer"] {
    color: #475569 !important;
}
.st-key-desk_header {
    color: #172033 !important;
}
.ab-brand {
    color: #172033 !important;
}
.ab-brand span {
    color: #059669 !important;
}
.ab-pill {
    border-color: #cbd5e1 !important;
}

/* ---------- Cards / panels ---------- */
.ab-card, .ab-hero, .ab-check, .ab-strip,
[data-testid="stMetric"],
[data-testid="stExpander"],
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stForm"] {
    background: #ffffff !important;
    border-color: #dbe3ee !important;
    color: #172033 !important;
}
.ab-card h4, .ab-card p,
.ab-check b, .ab-check .txt,
.ab-strip .lab {
    color: #172033 !important;
}
.ab-check .txt span {
    color: #64748b !important;
}
.ab-strip .val {
    color: #172033 !important;
}
[data-testid="stMetricLabel"] {
    color: #64748b !important;
}
[data-testid="stMetricValue"] {
    color: #172033 !important;
}
[data-testid="stMetricDelta"] {
    color: #475569 !important;
}

/* ---------- Buttons ---------- */
.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button {
    background: #ffffff !important;
    color: #172033 !important;
    border: 1px solid #cbd5e1 !important;
    box-shadow: 0 1px 2px rgba(15,23,42,.04) !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    background: #f1f5f9 !important;
    border-color: #94a3b8 !important;
    color: #0f172a !important;
}
.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible {
    outline: 2px solid rgba(37,99,235,.28) !important;
    outline-offset: 2px !important;
}
/* Preserve semantic trading buttons. */
.st-key-pr_buy button {
    background: #16a34a !important;
    color: #ffffff !important;
    border-color: #16a34a !important;
}
.st-key-pr_close button {
    background: #dc2626 !important;
    color: #ffffff !important;
    border-color: #dc2626 !important;
}

/* ---------- Inputs ---------- */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
.stDateInput input,
.stTimeInput input {
    background: #ffffff !important;
    color: #172033 !important;
    border-color: #cbd5e1 !important;
    caret-color: #2563eb !important;
}
.stTextInput input::placeholder,
.stNumberInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #94a3b8 !important;
}
[data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #172033 !important;
    border-color: #cbd5e1 !important;
}
[data-baseweb="select"] input,
[data-baseweb="select"] [role="combobox"] {
    color: #172033 !important;
}
[data-baseweb="select"] svg {
    fill: #64748b !important;
}
[data-baseweb="popover"],
[data-baseweb="menu"],
[data-baseweb="modal"] {
    background: #ffffff !important;
    color: #172033 !important;
    border-color: #dbe3ee !important;
}
[data-baseweb="menu"] li {
    color: #172033 !important;
}
[data-baseweb="menu"] li:hover,
[data-baseweb="option"]:hover {
    background: #eef4ff !important;
}
[data-baseweb="tag"] {
    background: #e8f0ff !important;
    color: #1d4ed8 !important;
}
[data-testid="stSlider"] [role="slider"] {
    background: #2563eb !important;
}

/* ---------- Tabs / expanders / alerts ---------- */
.stTabs [data-baseweb="tab-list"] {
    border-bottom-color: #dbe3ee !important;
}
.stTabs [data-baseweb="tab"] {
    color: #64748b !important;
}
.stTabs [aria-selected="true"] {
    color: #1d4ed8 !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
    color: #172033 !important;
}
[data-testid="stAlert"] {
    border-color: #dbe3ee !important;
}

/* ---------- Dataframes / tables ---------- */
[data-testid="stDataFrame"] {
    background: #ffffff !important;
    border-color: #dbe3ee !important;
}
[data-testid="stDataFrame"] iframe {
    background: #ffffff !important;
}

/* ---------- Code ---------- */
code, pre {
    background: #eef2f7 !important;
    color: #172033 !important;
    border-color: #dbe3ee !important;
}

/* ---------- Workflow cards ---------- */
[class*="st-key-workflow_step_"] > button {
    background: #ffffff !important;
    color: #172033 !important;
    border-color: #dbe3ee !important;
    box-shadow: 0 2px 8px rgba(15,23,42,.05) !important;
}
[class*="st-key-workflow_step_"] > button:hover {
    background: #f8fbff !important;
    border-color: #2563eb !important;
    box-shadow: 0 10px 24px rgba(15,23,42,.10) !important;
}
[class*="st-key-workflow_step_"] > button::after {
    background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(241,246,252,.99)) !important;
    color: #526176 !important;
    border-color: #cbd5e1 !important;
    box-shadow: 0 10px 26px rgba(15,23,42,.14) !important;
}
[class*="st-key-workflow_step_"] > button:disabled {
    background: #e8f0ff !important;
    color: #1d4ed8 !important;
    border-color: #93c5fd !important;
}

/* ---------- Mobile menu drawer ---------- */
.st-key-mobile_menu_drawer {
    background: linear-gradient(180deg,#ffffff 0%,#f6f8fb 100%) !important;
    border-color: #dbe3ee !important;
    box-shadow: 0 24px 70px rgba(15,23,42,.16) !important;
}
.st-key-mobile_menu_drawer [data-testid="stPageLink"] a {
    color: #334155 !important;
}
.st-key-mobile_menu_drawer [data-testid="stPageLink"] a:hover {
    background: #eef4ff !important;
}

/* ---------- Scrollbars / floating controls ---------- */
html {
    scrollbar-width: thin;
    scrollbar-color: #94a3b8 #eef2f7;
}
html::-webkit-scrollbar-track {
    background: #eef2f7;
}
html::-webkit-scrollbar-thumb {
    background: #94a3b8;
    border: 2px solid #eef2f7;
}
html::-webkit-scrollbar-thumb:hover {
    background: #64748b;
}
.ta-workflow, .ab-strip, .stTabs [data-baseweb="tab-list"],
[data-testid="stDataFrame"] {
    scrollbar-color: #94a3b8 #eef2f7;
}
#algobot-scroll-progress {
    background: linear-gradient(90deg, #2563eb, #16a34a) !important;
    box-shadow: 0 0 8px rgba(37,99,235,.22) !important;
}
.ta-back-to-top {
    background: #ffffff !important;
    color: #172033 !important;
    border-color: #cbd5e1 !important;
    box-shadow: 0 8px 24px rgba(15,23,42,.12) !important;
}
.ta-back-to-top:hover {
    background: #f1f5f9 !important;
    color: #172033 !important;
}
@media (max-width:768px) {
    .ta-back-to-top { left:50%; right:auto; bottom:14px; min-height:42px; padding:0 12px; }
}

/* Sidebar appearance control */
[data-testid="stSidebar"] .stToggle {
    margin-bottom: 4px !important;
}
</style>
"""



WORKFLOW_STEPS = [
    ("guide", "How TradeALGO Works", "pages/18_How_TradeALGO_Works.py"),
    ("strategy", "Strategy Builder", "pages/10_Strategy_Builder.py"),
    ("ai", "AI Strategy Agent", "pages/21_AI_Strategy_Agent.py"),
    ("backtest", "Backtest", "pages/5_Backtest.py"),
    ("auto", "Auto Tester", "pages/13_Auto_Tester.py"),
    ("reality", "Reality Check", "pages/6_Reality_check.py"),
    ("paper", "Paper Trading", "pages/16_Paper_Trading.py"),
    ("sandbox", "Upstox Sandbox", "pages/14_Upstox_Sandbox.py"),
    ("rehearsal", "Sandbox Rehearsal", "pages/17_Sandbox_Rehearsal.py"),
    ("live", "Live Trading", "pages/11_Live_Trading.py"),
]

def page_link(path: str, label: str, icon: str | None = None, use_container_width: bool = True) -> None:
    """Render an internal link, with an AppTest-safe fallback for unregistered pages."""
    try:
        st.page_link(path, label=label, icon=icon, use_container_width=use_container_width)
    except Exception as exc:
        # Streamlit AppTest can execute a page outside the main navigation registry.
        # Keep the UI testable without changing normal Cloud/local navigation.
        if exc.__class__.__name__ == "StreamlitPageNotFoundError":
            href = path.replace(" ", "%20")
            st.markdown(f'<a href="/{href}" target="_self">{escape(label)}</a>', unsafe_allow_html=True)
        else:
            raise


def _menu() -> None:
    """Trader-friendly sidebar navigation shared by every page."""
    # dashboard.py is the registered Streamlit entrypoint on Cloud AND locally
    # (run_windows.bat runs `streamlit run dashboard.py`). Trading_Desk.py is
    # NOT a registered page so st.page_link("Trading_Desk.py") throws on Cloud.
    home_page = "dashboard.py"
    with st.sidebar:
        st.markdown(
            f'<div class="ab-menu-head"><div class="ab-menu-brand">ALGO<span>BOT</span></div>'
            f'<div class="ab-menu-status">TRADING DESK · {"HOSTED" if is_hosted() else "LOCAL"} · LIVE OFF</div></div>',
            unsafe_allow_html=True,
        )
        sections = [
            ("Start Here", [
                ("🗺️", "How TradeALGO Works", "pages/18_How_TradeALGO_Works.py"),
            ]),
            ("Trade Desk", [
                ("🏠", "Trading Desk", home_page),
                ("🧮", "Position Size", "pages/1_Position_size.py"),
                ("📒", "Journal & Report", "pages/2_Journal_and_report.py"),
            ]),
            ("Practice", [
                ("🎯", "Practice Room", "pages/3_Practice_room.py"),
                ("⏳", "Option Breakeven & Ruin", "pages/4_Option_breakeven_and_ruin.py"),
            ]),
            ("Research", [
                ("📊", "Backtest", "pages/5_Backtest.py"),
                ("🎯", "Dynamic Options", "pages/25_Dynamic_Options.py"),
                ("⚡", "Tick Engine", "pages/26_Tick_Engine.py"),
                ("🛡️", "Reality Check", "pages/6_Reality_check.py"),
                ("🧪", "Test Lab", "pages/7_Test_lab.py"),
            ]),
            ("Automation", [
                ("🧠", "Strategy Builder", "pages/10_Strategy_Builder.py"),
                ("🤖", "AI Strategy Agent", "pages/21_AI_Strategy_Agent.py"),
                ("🧪", "Auto Tester", "pages/13_Auto_Tester.py"),
                ("🔬", "Strategy Scanner", "pages/15_Strategy_Scanner.py"),
                ("📝", "Paper Trading", "pages/16_Paper_Trading.py"),
                ("🎬", "Sandbox Rehearsal", "pages/17_Sandbox_Rehearsal.py"),
                ("🧪", "Upstox Sandbox", "pages/14_Upstox_Sandbox.py"),
                ("📲", "Signal Alerts", "pages/20_Signal_Alerts.py"),
                ("📈", "Live Markets", "pages/23_Live_Markets.py"),
                ("🔌", "OpenAlgo Execution", "pages/24_OpenAlgo_Execution.py"),
            ]),
            ("More", [
                ("👤", "My Profile", "pages/22_Profile.py"),
                ("💬", "Feedback", "pages/8_Feedback.py"),
            ]),
            ("Execution", [
                ("🔴", "Live Trading", "pages/11_Live_Trading.py"),
            ]),
        ]
        for section, links in sections:
            st.markdown(f'<div class="ab-menu-section">{escape(section)}</div>', unsafe_allow_html=True)
            for icon_, label, path in links:
                page_link(path, label=f"{icon_}  {label}", use_container_width=True)
        st.caption("🔒 Live orders are locked · fake money only")


def is_hinglish() -> bool:
    """Return the user's current UI language preference."""
    return bool(st.session_state.get("tradealgo_hinglish", False))


def language_toggle() -> None:
    """Compact global language switch."""
    current = is_hinglish()
    value = st.toggle(
        "HI",
        value=current,
        key="tradealgo_hinglish",
        help="Switch between English and Hinglish",
    )
    if value != current:
        st.session_state["tradealgo_hinglish"] = value
        st.rerun()


def _apply_theme_from_toggle(key: str) -> None:
    """Apply a theme toggle before Streamlit reruns the app."""
    st.session_state["tradealgo_theme"] = (
        "dark" if st.session_state.get(key, True) else "light"
    )


def theme_toggle() -> None:
    """Compact global dark/light mode switch."""
    current_dark = is_dark_mode()
    st.toggle(
        "Dark",
        value=current_dark,
        key="tradealgo_theme_toggle",
        help="Switch between dark and light mode",
        on_change=_apply_theme_from_toggle,
        args=("tradealgo_theme_toggle",),
    )



def setup(title: str, icon: str = "📈", layout: str = "wide") -> None:
    """First call on every page: page settings, styling, and the password screen if one is set."""
    st.set_page_config(page_title=f"{title} | TradeALGO", page_icon=icon, layout=layout, initial_sidebar_state="expanded")
    st.session_state.setdefault("tradealgo_theme", "light")
    st.markdown(CSS, unsafe_allow_html=True)
    if not is_dark_mode():
        st.markdown(LIGHT_CSS, unsafe_allow_html=True)

    st.session_state.setdefault("top_menu_open", False)
    st.markdown('<div id="tradealgo-top" aria-hidden="true"></div>', unsafe_allow_html=True)
    _menu()
    password_gate()
    swipe_component = _swipe_menu_component()
    if swipe_component is not None:
        try:
            swipe_component(key="algobot_mobile_swipe_menu")
        except st.errors.StreamlitAPIException:
            # Streamlit AppTest does not mount browser-only v2 components.
            # The gesture is progressive enhancement; page rendering must survive without it.
            pass

    st.markdown(
        '<a class="ta-back-to-top" href="#tradealgo-top" aria-label="Back to top">↑ <span>Back to top</span></a>',
        unsafe_allow_html=True,
    )




def pill(text: str, tone: str = "green") -> str:
    return f'<span class="ab-pill {escape(tone)}">{escape(text)}</span>'


def _top_menu_links() -> list[tuple[str, str, str]]:
    return [
        ("🗺️", "How TradeALGO Works", "pages/18_How_TradeALGO_Works.py"),
        ("🏠", "Trading Desk", "dashboard.py"),
        ("🧮", "Position Size", "pages/1_Position_size.py"),
        ("📒", "Journal & Report", "pages/2_Journal_and_report.py"),
        ("🎯", "Practice Room", "pages/3_Practice_room.py"),
        ("📊", "Backtest", "pages/5_Backtest.py"),
        ("🎯", "Dynamic Options", "pages/25_Dynamic_Options.py"),
        ("⚡", "Tick Engine", "pages/26_Tick_Engine.py"),
        ("🛡️", "Reality Check", "pages/6_Reality_check.py"),
        ("🧪", "Test Lab", "pages/7_Test_lab.py"),
        ("🧠", "Strategy Builder", "pages/10_Strategy_Builder.py"),
        ("🤖", "AI Strategy Agent", "pages/21_AI_Strategy_Agent.py"),
        ("🧪", "Auto Tester", "pages/13_Auto_Tester.py"),
        ("🔬", "Strategy Scanner", "pages/15_Strategy_Scanner.py"),
        ("📝", "Paper Trading", "pages/16_Paper_Trading.py"),
        ("🎬", "Sandbox Rehearsal", "pages/17_Sandbox_Rehearsal.py"),
        ("🧪", "Upstox Sandbox", "pages/14_Upstox_Sandbox.py"),
        ("📲", "Signal Alerts", "pages/20_Signal_Alerts.py"),
        ("📈", "Live Markets", "pages/23_Live_Markets.py"),
        ("🔌", "OpenAlgo Execution", "pages/24_OpenAlgo_Execution.py"),
        ("🔴", "Live Trading", "pages/11_Live_Trading.py"),
    ]


def _top_menu_drawer() -> None:
    if not st.session_state.get("top_menu_open", False):
        return
    with st.container(key="top_menu_drawer"):
        st.markdown('<div class="ta-drawer-title">TRADEALGO MENU</div>', unsafe_allow_html=True)
        st.markdown('<div class="ta-drawer-subtitle">Navigate anywhere without opening the sidebar.</div>',
                    unsafe_allow_html=True)
        if st.button("✕  Close menu", key="top_menu_close", width="stretch"):
            st.session_state["top_menu_open"] = False
            st.rerun()
        st.divider()
        for icon_, label, path in _top_menu_links():
            page_link(path, label=f"{icon_}  {label}", use_container_width=True)


def header(title: str, subtitle: str = "", mode: Optional[str] = None) -> None:
    """Render a clean utility bar followed by the trading-desk header."""
    pills = [pill("NO LIVE ORDERS", "green")]
    if mode:
        tone = {
            "practice": "amber",
            "backtest": "blue",
            "journal": "green",
            "research": "blue",
        }.get(mode.split(":")[0], "blue")
        pills.insert(0, pill(mode.split(":", 1)[-1].upper(), tone))
    pills.append(pill("HOSTED" if is_hosted() else "LOCAL", "blue"))

    # One consistent horizontal action bar. Nothing is fixed over the page,
    # so it never creates a large empty area or overlaps Streamlit's toolbar.
    # Profile/Feedback are routed through the page_link() wrapper (not raw
    # st.page_link) so they get the same AppTest-safe fallback as every other
    # nav link — a direct st.page_link call here previously broke every
    # single page under Streamlit's AppTest harness (see page_link()'s
    # docstring above), which is also what GitHub Actions CI runs.
    with st.container(
        key="utility_bar",
        horizontal=True,
        vertical_alignment="center",
        horizontal_alignment="left",
        gap="small",
        border=True,
    ):
        st.markdown(
            '''<div class="ta-utility-brand" aria-label="TradeALGO">
                <svg class="ta-logo-svg" viewBox="0 0 100 100" role="img" aria-label="TradeALGO logo">
                    <defs>
                        <linearGradient id="taBlueGreen" x1="0" y1="0" x2="1" y2="1">
                            <stop offset="0%" stop-color="#2563EB"/>
                            <stop offset="52%" stop-color="#12B8FF"/>
                            <stop offset="100%" stop-color="#20E39B"/>
                        </linearGradient>
                    </defs>
                    <path d="M10 18h52L48 36H28v48H10z" fill="url(#taBlueGreen)"/>
                    <path d="M51 18l39 64H70L59 63 47 82H29z" fill="url(#taBlueGreen)"/>
                    <path d="M41 62l8-12 8 12-8 13z" fill="#20E39B"/>
                    <path d="M47 72v-9M55 72V55M63 72V46" stroke="#D9FFF1" stroke-width="3" stroke-linecap="round"/>
                </svg>
                <span class="ta-utility-wordmark">
                    <span class="ta-utility-name">TRADE<span>ALGO</span></span>
                    <span class="ta-utility-tag">TRADING DESK</span>
                </span>
            </div>''',
            unsafe_allow_html=True,
        )
        with st.container(
            key="utility_actions",
            horizontal=True,
            vertical_alignment="center",
            horizontal_alignment="right",
            gap="small",
        ):
            page_link("dashboard.py", label="⌂ Home", use_container_width=False)
            page_link("pages/22_Profile.py", label="👤 Profile", use_container_width=False)
            page_link("pages/8_Feedback.py", label="💬 Feedback", use_container_width=False)
            st.toggle(
                "🌙",
                value=is_dark_mode(),
                key="tradealgo_theme_toggle_top",
                help="Switch between dark and light mode",
                label_visibility="collapsed",
                on_change=_apply_theme_from_toggle,
                args=("tradealgo_theme_toggle_top",),
            )
            if st.button("☰ Menu", key="top_menu", type="secondary"):
                st.session_state["top_menu_open"] = not st.session_state.get("top_menu_open", False)
                st.rerun()

    with st.container(key="desk_header"):
        left, middle = st.columns([4.8, 5.2], vertical_alignment="center")
        with left:
            st.markdown(
                '<div class="ab-brand">TRADE<span>ALGO</span> &nbsp;·&nbsp; TRADING RESEARCH</div>',
                unsafe_allow_html=True,
            )
        with middle:
            st.markdown(
                f'<div class="ab-pills" style="justify-content:flex-end">{"".join(pills)}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(f"## {title}")
        if subtitle:
            st.caption(subtitle)

    _top_menu_drawer()



def ticker(items: Iterable) -> None:
    """A strip of live-style numbers. Each item is (label, value, tone) with tone 'up', 'down', 'warn' or None."""
    cells = "".join(
        f'<div><div class="lab">{escape(str(label))}</div>'
        f'<div class="val {escape(tone or "")}">{escape(str(value))}</div></div>'
        for label, value, tone in items)
    st.markdown(f'<div class="ab-strip">{cells}</div>', unsafe_allow_html=True)


def card(title: str, body: str, icon: str = "") -> str:
    return f'<div class="ab-card"><h4>{escape(icon)} {escape(title)}</h4><p>{escape(body)}</p></div>'


def check_row(status: str, title: str, detail: str) -> None:
    """One audit-style line with a coloured status pill."""
    tone = {"PASS": "green", "WARN": "amber", "FAIL": "red", "SKIP": "blue"}.get(status, "blue")
    st.markdown(f'<div class="ab-check">{pill(status, tone)}<div class="txt"><b>{escape(title)}</b>'
                f'<span>{escape(detail)}</span></div></div>', unsafe_allow_html=True)


def tone(value: float) -> str:
    return "up" if value > 0 else ("down" if value < 0 else "")


def inr(value: float, sign: bool = False) -> str:
    """Rupees with Indian-style thousands? Plain thousands separators keep it simple and unambiguous."""
    prefix = "+" if sign and value > 0 else ""
    return f"{prefix}₹{value:,.0f}" if value >= 0 else f"-₹{abs(value):,.0f}"


def show_chart(chart) -> None:
    """Draw an Altair chart full width, on any Streamlit version."""
    if chart is None:
        st.caption("Nothing to draw yet.")
        return
    try:
        st.altair_chart(chart, width="stretch")
    except TypeError:                                   # older Streamlit
        st.altair_chart(chart, use_container_width=True)


def show_table(frame, **kwargs) -> None:
    try:
        st.dataframe(frame, width="stretch", **kwargs)
    except TypeError:
        st.dataframe(frame, use_container_width=True, **kwargs)



def workflow_nav(current_key: str, complete: bool = False) -> None:
    """Render the workflow as large, horizontally scrollable navigation cards."""
    index = next((i for i, item in enumerate(WORKFLOW_STEPS) if item[0] == current_key), 0)
    total = len(WORKFLOW_STEPS)
    # Fixed-width buttons inside a no-wrap horizontal container preserve the
    # large workflow-card appearance while allowing sideways scrolling.
    with st.container(
        horizontal=True,
        wrap=False,
        horizontal_alignment="left",
        gap="small",
        border=True,
    ):
        workflow_icons = ["🗺️", "🧠", "🤖", "📊", "🧪", "🛡️", "📝", "🏦", "🎬", "🚀"]
        for i, (_, name, path) in enumerate(WORKFLOW_STEPS):
            label = f"{workflow_icons[i]}\nSTEP {i+1:02d}\n{name}"
            if st.button(
                label,
                key=f"workflow_step_{i}",
                disabled=(i == index),
                type="primary" if i == index else "secondary",
                width=170,
            ):
                st.switch_page(path)

    st.caption(
        f"Step {index+1} of {total} · scroll sideways to see all steps · "
        "click any step to open its page"
    )

    prev_step = WORKFLOW_STEPS[index - 1] if index > 0 else None
    next_step = WORKFLOW_STEPS[index + 1] if index < total - 1 else None
    left, right = st.columns(2)
    with left:
        if prev_step:
            if st.button(
                f"⬅️  Previous: {prev_step[1]}",
                key=f"workflow_prev_{current_key}",
                width="stretch",
            ):
                st.switch_page(prev_step[2])
    with right:
        if next_step:
            if st.button(
                f"Next: {next_step[1]}  ➡️",
                key=f"workflow_next_{current_key}",
                width="stretch",
            ):
                st.switch_page(next_step[2])
        else:
            st.success("✅ Workflow complete — you have reached Live Trading.")

def footer_note(text: str = "Practice and research tool. Not advice. It never places orders and never asks for broker keys.") -> None:
    st.markdown(f'<p style="color:#8B98A9;font-size:.8rem;margin-top:2rem">{escape(text)} &nbsp;·&nbsp; algobot v{escape(__version__)}</p>',
                unsafe_allow_html=True)
