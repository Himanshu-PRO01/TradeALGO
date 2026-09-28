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

CSS = f"""
<style>
.block-container {{ padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1500px; }}
h1, h2, h3 {{ letter-spacing: -0.01em; }}
[data-testid="stSidebar"] {{ background: {PANEL}; border-right: 1px solid {BORDER}; }}
[data-testid="stSidebarNav"] {{ display:none; }}
.ab-menu-head {{ padding:4px 6px 12px; border-bottom:1px solid {BORDER}; margin-bottom:10px; }}
.ab-menu-brand {{ font-weight:900; letter-spacing:.12em; font-size:1rem; }}
.ab-menu-brand span {{ color:{UP}; }}
.ab-menu-status {{ color:{MUTED}; font-size:.72rem; margin-top:4px; }}
.ab-menu-section {{ color:{MUTED}; font-size:.66rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin:14px 6px 5px; }}

/* lightweight sidebar navigation -- flat surfaces only, no blur/shadow stacking,
   so the menu stays smooth to scroll and repaint on low-end and mobile devices */
[data-testid="stSidebar"] [data-testid="stPageLink"] {{
    margin: 3px 0;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {{
    min-height: 44px;
    padding: 9px 12px !important;
    border: 1px solid transparent;
    border-left: 2px solid transparent;
    border-radius: 8px;
    background: transparent;
    font-size: .93rem;
    font-weight: 600;
    letter-spacing: .01em;
    transition: background-color .12s ease, border-color .12s ease;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {{
    background: rgba(255,255,255,.055);
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {{
    background: rgba(59,130,246,.12);
    border-left: 2px solid {BLUE};
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a p {{
    font-size: .93rem;
    font-weight: 600;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a span {{
    font-size: 1.05rem;
}}


/* mobile-first trading UX */
@media (max-width: 768px) {{
    .block-container {{
        padding: .65rem .75rem 4.5rem;
        max-width: 100%;
    }}
    .ab-top {{
        align-items: flex-start;
        gap: 7px;
        padding: 3px 0 8px;
        margin-bottom: 6px;
    }}
    .ab-brand {{
        font-size: .82rem;
        letter-spacing: .12em;
    }}
    .ab-pills {{
        width: 100%;
        gap: 5px;
        overflow-x: auto;
        flex-wrap: nowrap;
        padding-bottom: 2px;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }}
    .ab-pills::-webkit-scrollbar {{ display:none; }}
    .ab-pill {{
        flex: 0 0 auto;
        padding: 4px 9px;
        font-size: 10px;
    }}
    h1 {{ font-size: 1.65rem !important; }}
    h2 {{ font-size: 1.35rem !important; }}
    h3 {{ font-size: 1.05rem !important; }}
    .ab-hero {{
        padding: 18px 16px;
        border-radius: 16px;
        margin-bottom: 12px;
    }}
    .ab-hero h2 {{ font-size: 1.45rem; }}
    .ab-card {{
        min-height: auto;
        padding: 14px;
        border-radius: 12px;
    }}
    .ab-nav-card {{
        min-height: auto;
        padding: 14px;
    }}
    .ab-strip {{
        gap: 0;
        padding: 9px 10px;
        border-radius: 11px;
        overflow-x: auto;
        flex-wrap: nowrap;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }}
    .ab-strip::-webkit-scrollbar {{ display:none; }}
    .ab-strip > div {{
        flex: 0 0 auto;
        min-width: 125px;
        padding-right: 16px;
    }}
    .ab-strip .val {{ font-size: .96rem; }}
    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button {{
        width: 100%;
        min-height: 46px;
        border-radius: 11px;
    }}
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea,
    .stDateInput input,
    .stTimeInput input {{
        font-size: 16px !important;
        min-height: 44px;
    }}
    .stSelectbox [data-baseweb="select"],
    .stMultiSelect [data-baseweb="select"] {{
        min-height: 44px;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        overflow-x: auto;
        flex-wrap: nowrap;
        scrollbar-width: none;
    }}
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {{ display:none; }}
    .stTabs [data-baseweb="tab"] {{
        flex: 0 0 auto;
        padding: 9px 12px;
        font-size: .84rem;
    }}
    [data-testid="stDataFrame"] {{
        max-width: 100%;
        overflow-x: auto;
    }}
    [data-testid="stSidebar"] {{
        min-width: min(88vw, 340px);
        max-width: min(88vw, 340px);
    }}
    [data-testid="stSidebar"] > div:first-child {{
        padding-top: .65rem;
    }}
    [data-testid="stSidebar"] [data-testid="stPageLink"] {{
        margin: 5px 0;
    }}
    [data-testid="stSidebar"] [data-testid="stPageLink"] a {{
        min-height: 48px;
        padding: 10px 12px !important;
        border-radius: 12px;
        font-size: .92rem;
    }}
    .ab-menu-section {{
        margin: 12px 6px 4px;
    }}
    .stCaption {{
        line-height: 1.4;
    }}
    /* Streamlit columns become easier to scan when their contents are separated. */
    [data-testid="stHorizontalBlock"] {{
        gap: .65rem !important;
    }}
}}
@media (max-width: 430px) {{
    .block-container {{
        padding-left: .6rem;
        padding-right: .6rem;
    }}
    .ab-brand {{
        font-size: .76rem;
    }}
    .ab-menu-brand {{
        font-size: .92rem;
    }}
    .ab-menu-status {{
        font-size: .66rem;
    }}
    .ab-check {{
        gap: 8px;
        padding: 9px 10px;
    }}
    .ab-check .txt span {{
        font-size: .82rem;
    }}
    [data-testid="stMetric"] {{
        padding: 10px 12px;
    }}
}}

/* metric cards */
[data-testid="stMetric"] {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 12px; padding: 12px 16px; }}
[data-testid="stMetricLabel"] {{ color: {MUTED}; text-transform: uppercase; font-size: 0.72rem; letter-spacing: .06em; }}
[data-testid="stMetricValue"] {{ font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-variant-numeric: tabular-nums; font-weight: 600; }}

/* buttons */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {{
    border-radius: 9px; font-weight: 600; border: 1px solid {BORDER}; }}
.st-key-pr_buy button {{ background: {UP}; color: #03130C; border: 0; }}
.st-key-pr_close button {{ background: {DOWN}; color: #fff; border: 0; }}
.st-key-pr_buy button:hover {{ filter: brightness(1.1); }}
.st-key-pr_close button:hover {{ filter: brightness(1.1); }}

/* square graphic workflow cards + shadcn-inspired hover previews */
[class*="st-key-workflow_step_"] > button {{
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
}}
[class*="st-key-workflow_step_"] > button:hover {{
    transform: translateY(-3px) !important;
    border-color: #3B82F6 !important;
    box-shadow: 0 8px 22px rgba(0,0,0,.24), inset 0 0 0 1px rgba(59,130,246,.18) !important;
    z-index: 20 !important;
}}
[class*="st-key-workflow_step_"] > button p {{
    white-space: pre-line !important;
    line-height: 1.2 !important;
    margin: 0 !important;
}}

/* HoverCard behavior: preview the step description on hover/focus.
   This mirrors shadcn HoverCard's trigger -> content pattern while keeping
   navigation native to Streamlit. */
[class*="st-key-workflow_step_"] > button::after {{
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
}}
[class*="st-key-workflow_step_"] > button:hover::after,
[class*="st-key-workflow_step_"] > button:focus-visible::after {{
    opacity: 1 !important;
    transform: translateY(0) !important;
}}
.st-key-workflow_step_0 > button::after {{ content: "Start with the trading idea and define what you want to test."; }}
.st-key-workflow_step_1 > button::after {{ content: "Turn the idea into clear, measurable entry and exit rules."; }}
.st-key-workflow_step_2 > button::after {{ content: "Use AI to research, refine, and challenge the strategy."; }}
.st-key-workflow_step_3 > button::after {{ content: "Run the strategy on historical market data and inspect results."; }}
.st-key-workflow_step_4 > button::after {{ content: "Test controlled variations to see how robust the strategy is."; }}
.st-key-workflow_step_5 > button::after {{ content: "Challenge the evidence with risk and robustness checks."; }}
.st-key-workflow_step_6 > button::after {{ content: "Rehearse trades with fake money before using a broker."; }}
.st-key-workflow_step_7 > button::after {{ content: "Test broker integration safely in the sandbox environment."; }}
.st-key-workflow_step_8 > button::after {{ content: "Run the full paper-to-sandbox rehearsal before execution."; }}
.st-key-workflow_step_9 > button::after {{ content: "Controlled execution stage. Live orders remain locked by default."; }}

@media (max-width:768px) {{
    [class*="st-key-workflow_step_"] > button {{
        width: 132px !important;
        min-width: 132px !important;
        max-width: 132px !important;
        height: 132px !important;
        min-height: 132px !important;
        font-size: .8rem !important;
    }}
    [class*="st-key-workflow_step_"] > button::after {{
        left: 6px !important;
        right: 6px !important;
        bottom: 6px !important;
        min-height: 48px !important;
        font-size: .66rem !important;
        padding: 7px !important;
    }}
}}

/* tabs, expanders, dataframes */
.stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
[data-testid="stExpander"] {{ border: 1px solid {BORDER}; border-radius: 12px; background: {PANEL}; }}
[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 10px; }}

/* top bar, pills, ticker */
.ab-top {{ display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;
    padding: 6px 2px 10px 2px; border-bottom: 1px solid {BORDER}; margin-bottom: 8px; }}
.ab-brand {{ font-weight: 800; letter-spacing: .18em; font-size: 0.95rem; }}
.ab-brand span {{ color: {UP}; }}
.ab-pills {{ display:flex; gap:8px; flex-wrap:wrap; }}
.ab-pill {{ display:inline-block; padding: 3px 11px; border-radius: 999px; font-size: 11px; font-weight: 700;
    letter-spacing: .07em; border: 1px solid; }}
.ab-pill.green {{ color:{UP}; border-color:{UP}55; background:{UP}14; }}
.ab-pill.amber {{ color:{WARN}; border-color:{WARN}55; background:{WARN}14; }}
.ab-pill.blue  {{ color:{BLUE}; border-color:{BLUE}55; background:{BLUE}14; }}
.ab-pill.red   {{ color:{DOWN}; border-color:{DOWN}55; background:{DOWN}14; }}
.ab-strip {{ display:flex; gap:26px; flex-wrap:wrap; padding: 10px 16px; background:{PANEL}; border:1px solid {BORDER};
    border-radius: 12px; margin: 4px 0 14px 0; font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; }}
.ab-strip .lab {{ color:{MUTED}; font-size: 0.68rem; text-transform: uppercase; letter-spacing:.08em; }}
.ab-strip .val {{ font-size: 1.05rem; font-weight: 700; font-variant-numeric: tabular-nums; }}
.up {{ color: {UP}; }} .down {{ color: {DOWN}; }} .warn {{ color: {WARN}; }}

/* polished dashboard surfaces */
[data-testid="stAppViewContainer"] {{ background: radial-gradient(circle at 85% 0%, #16243a 0%, #0B0F14 34%); }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] > div:first-child {{ padding-top: 1.2rem; }}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{ color: #8B98A9; }}
[data-testid="stCaptionContainer"] {{ color: #8B98A9; }}
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"],
.stMultiSelect [data-baseweb="select"], .stDateInput input, .stTimeInput input {{ border-radius: 10px; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ transform: translateY(-1px); border-color: #3B82F6; }}
.ab-hero {{ position:relative; overflow:hidden; background:linear-gradient(135deg,#121923 0%,#0F1B2A 100%);
    border:1px solid #1F2A37; border-radius:20px; padding:24px 26px; margin:6px 0 18px; }}
.ab-hero:after {{ content:""; position:absolute; width:220px; height:220px; right:-90px; top:-110px;
    border-radius:50%; border:1px solid #16C78433; box-shadow:0 0 0 24px #16C78408,0 0 0 48px #16C78405; }}
.ab-kicker {{ color:#16C784; font-size:.72rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; }}
.ab-hero h2 {{ margin:5px 0 6px; font-size:1.8rem; }}
.ab-hero p {{ color:#8B98A9; max-width:760px; margin:0; line-height:1.55; }}
.ab-section {{ display:flex; align-items:center; gap:10px; margin:22px 0 10px; }}
.ab-section .dot {{ width:8px; height:8px; border-radius:50%; background:#16C784; box-shadow:0 0 14px #16C78499; }}
.ab-section h3 {{ margin:0; font-size:1.05rem; }}
.ab-section span {{ color:#8B98A9; font-size:.8rem; }}
.ab-nav-card {{ background:#121923; border:1px solid #1F2A37; border-radius:14px; padding:15px 16px; min-height:120px;
    transition:transform .15s ease,border-color .15s ease; }}
.ab-nav-card:hover {{ transform:translateY(-2px); border-color:#3B82F688; }}
.ab-nav-card .icon {{ font-size:1.35rem; }}
.ab-nav-card h4 {{ margin:7px 0 4px; }}
.ab-nav-card p {{ margin:0; color:#8B98A9; font-size:.84rem; line-height:1.45; }}
/* cards */
.ab-card {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:14px; padding:16px 18px; min-height:170px; margin-bottom:10px; }}
.ab-card h4 {{ margin: 0 0 6px 0; }}
.ab-card p {{ color:{MUTED}; margin: 0; font-size: .92rem; }}
.ab-check {{ display:flex; gap:12px; align-items:flex-start; background:{PANEL}; border:1px solid {BORDER};
    border-radius:12px; padding:10px 14px; margin-bottom:8px; }}
.ab-check .txt b {{ display:block; }}
.ab-check .txt span {{ color:{MUTED}; font-size:.88rem; }}

/* top-right navigation button: float it into Streamlit's toolbar row,
   beside Share instead of taking space in the page header */
.ta-menu-trigger {{
    display:flex;
    justify-content:flex-end;
    align-items:center;
}}
.st-key-top_menu {{
    position:fixed !important;
    top:8px !important;
    right:208px !important;
    z-index:100000 !important;
    width:auto !important;
}}
.st-key-top_menu button {{
    min-height:38px !important;
    height:38px !important;
    padding:7px 14px !important;
    border-radius:10px !important;
    font-weight:800 !important;
    letter-spacing:.02em !important;
    white-space:nowrap !important;
    background:#111923 !important;
    border:1px solid #263242 !important;
}}
/* Profile sits immediately beside the Menu control in the top toolbar. */
.st-key-top_profile {{
    position:fixed !important;
    top:8px !important;
    right:320px !important;
    z-index:100000 !important;
    width:auto !important;
}}
.st-key-top_feedback {{
    position:fixed !important;
    top:8px !important;
    right:438px !important;
    z-index:100000 !important;
    width:auto !important;
}}
.st-key-top_feedback {{
    display:flex !important;
    align-items:center !important;
}}
.st-key-top_feedback [data-testid="stPageLink"] {{
    margin:0 !important;
}}
.st-key-top_feedback [data-testid="stPageLink"] a {{
    min-height:38px !important;
    height:38px !important;
    box-sizing:border-box !important;
    display:flex !important;
    align-items:center !important;
    padding:7px 14px !important;
    border-radius:10px !important;
    font-weight:800 !important;
    letter-spacing:.02em !important;
    white-space:nowrap !important;
    background:#111923 !important;
    border:1px solid #263242 !important;
    text-decoration:none !important;
}}
.st-key-top_feedback [data-testid="stPageLink"] a:hover {{
    border-color:#3B82F6 !important;
    background:#172231 !important;
}}
.st-key-top_profile {{
    display:flex !important;
    align-items:center !important;
}}
.st-key-top_profile [data-testid="stPageLink"] {{
    margin:0 !important;
}}
.st-key-top_profile [data-testid="stPageLink"] a {{
    min-height:38px !important;
    height:38px !important;
    box-sizing:border-box !important;
    display:flex !important;
    align-items:center !important;
    padding:7px 14px !important;
    border-radius:10px !important;
    font-weight:800 !important;
    letter-spacing:.02em !important;
    white-space:nowrap !important;
    background:#111923 !important;
    border:1px solid #263242 !important;
    text-decoration:none !important;
}}
.st-key-top_profile [data-testid="stPageLink"] a:hover {{
    border-color:#16C784 !important;
    background:#17251f !important;
}}

.st-key-top_menu button:hover {{
    border-color:#3B82F6 !important;
    background:#172231 !important;
}}
.st-key-top_menu_drawer {{
    position:fixed !important;
    top:76px !important;
    right:24px !important;
    width:min(390px, calc(100vw - 32px)) !important;
    max-height:calc(100vh - 100px) !important;
    overflow-y:auto !important;
    z-index:9999 !important;
    padding:18px !important;
    border:1px solid #263242 !important;
    border-radius:20px !important;
    background:linear-gradient(180deg,#111923 0%,#0d131b 100%) !important;
    box-shadow:0 24px 70px rgba(0,0,0,.55), 0 0 0 1px rgba(59,130,246,.08) !important;
}}
.st-key-top_menu_drawer [data-testid="stPageLink"] a {{
    min-height:42px;
    border-radius:10px;
    padding:9px 12px !important;
    transition:background-color .12s ease, transform .12s ease;
}}
.st-key-top_menu_drawer [data-testid="stPageLink"] a:hover {{
    background:rgba(255,255,255,.06);
    transform:translateX(2px);
}}
.ta-drawer-title {{
    font-size:.72rem;
    font-weight:900;
    letter-spacing:.14em;
    text-transform:uppercase;
    color:#16C784;
    margin-bottom:3px;
}}
.ta-drawer-subtitle {{
    color:#8B98A9;
    font-size:.78rem;
    margin-bottom:12px;
}}
@media (max-width:768px) {{
    .st-key-top_profile {{
        top:8px !important;
        right:232px !important;
        width:auto !important;
    }}
    .st-key-top_profile [data-testid="stPageLink"] a {{
        width:auto !important;
        justify-content:center !important;
        padding-left:10px !important;
        padding-right:10px !important;
    }}
    .st-key-top_feedback {{
        top:8px !important;
        right:116px !important;
        width:auto !important;
    }}
    .st-key-top_feedback [data-testid="stPageLink"] a {{
        padding-left:9px !important;
        padding-right:9px !important;
    }}
    .st-key-top_menu {{
        top:8px !important;
        right:10px !important;
    }}
    .st-key-top_menu_drawer {{
        top:62px !important;
        right:10px !important;
        width:calc(100vw - 20px) !important;
        max-height:calc(100vh - 78px) !important;
        border-radius:16px !important;
    }}
}}
/* guided workflow */
.ta-workflow {{
    width: 100%;
    box-sizing: border-box;
    margin: 14px 0 20px;
    padding: 16px;
    border: 1px solid #263242;
    border-radius: 18px;
    background: linear-gradient(180deg,#111923 0%,#0d131b 100%);
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
}}
.ta-workflow-track {{
    display: flex;
    align-items: stretch;
    gap: 8px;
    min-width: 1160px;
}}
.ta-workflow-step {{
    flex: 1 1 0;
    min-width: 112px;
    min-height: 92px;
    box-sizing: border-box;
    padding: 12px 10px;
    border: 1px solid #2b3849;
    border-radius: 14px;
    background: #151d28;
    text-align: center;
    transition: transform .15s ease,border-color .15s ease,background .15s ease;
}}
.ta-workflow-step:hover {{
    transform: translateY(-2px);
    border-color: #3b82f6;
}}
.ta-workflow-step.active {{
    border-color: #16c784;
    background: linear-gradient(180deg,#11271f 0%,#121e1b 100%);
    box-shadow: inset 0 0 0 1px #16c78422;
}}
.ta-workflow-step .num {{
    color: #7f8da0;
    font-size: .67rem;
    font-weight: 900;
    letter-spacing: .12em;
}}
.ta-workflow-step.active .num {{
    color: #16c784;
}}
.ta-workflow-step .name {{
    margin-top: 7px;
    color: #f2f5f8;
    font-size: .78rem;
    line-height: 1.15;
    font-weight: 800;
}}
.ta-workflow-step .desc {{
    margin-top: 7px;
    color: #8b98a9;
    font-size: .67rem;
    line-height: 1.25;
}}
.ta-workflow-arrow {{
    flex: 0 0 auto;
    align-self: center;
    color: #526176;
    font-size: 1.2rem;
    font-weight: 700;
}}
.ta-flow-note {{
    margin-top: 11px;
    color: #8b98a9;
    font-size: .76rem;
    text-align: center;
}}
@media (max-width:768px) {{
    .ta-workflow {{
        margin-left: 0;
        margin-right: 0;
        padding: 11px;
    }}
    .ta-workflow-track {{
        min-width: 1020px;
    }}
    .ta-workflow-step {{
        min-width: 100px;
        min-height: 86px;
    }}
}}
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
    """Compact global English/Hinglish switch shown at the top of every page."""
    current = is_hinglish()
    col1, col2, col3 = st.columns([1, 1.2, 8])
    with col1:
        st.caption("EN")
    with col2:
        value = st.toggle(
            "Hinglish",
            value=current,
            key="tradealgo_hinglish",
            label_visibility="collapsed",
        )
    with col3:
        st.caption("Hinglish" if value else "English")


def setup(title: str, icon: str = "📈", layout: str = "wide") -> None:
    """First call on every page: page settings, styling, and the password screen if one is set."""
    st.set_page_config(page_title=f"{title} | Algobot", page_icon=icon, layout=layout, initial_sidebar_state="collapsed")
    st.markdown(CSS, unsafe_allow_html=True)
    st.session_state.setdefault("top_menu_open", False)
    _menu()
    language_toggle()
    swipe_component = _swipe_menu_component()
    if swipe_component is not None:
        try:
            swipe_component(key="algobot_mobile_swipe_menu")
        except st.errors.StreamlitAPIException:
            # Streamlit AppTest does not mount browser-only v2 components.
            # The gesture is progressive enhancement; page rendering must survive without it.
            pass
    password_gate()


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
    """Brand bar with safety pills and a shadcn-inspired top-right drawer trigger."""
    lang = "Hinglish" if is_hinglish() else "English"
    pills = [pill("LIVE ORDERS OFF" if is_hinglish() else "NO LIVE ORDERS", "green")]
    if mode:
        tone = {"practice": "amber", "backtest": "blue", "journal": "green", "research": "blue"}.get(mode.split(":")[0], "blue")
        pills.insert(0, pill(mode.split(":", 1)[-1].upper(), tone))
    pills.append(pill("HOSTED" if is_hosted() else "LOCAL", "blue"))

    # Use a native Streamlit page link for Profile so navigation does not
    # depend on a widget callback or rerun timing. st.page_link is designed
    # for multipage navigation and preserves the current Streamlit session.
    with st.container(key="top_profile"):
        st.page_link(
            "pages/22_Profile.py",
            label="👤  Profile",
            use_container_width=False,
        )

    with st.container(key="top_feedback"):
        st.page_link(
            "pages/8_Feedback.py",
            label="💬  Feedback",
            use_container_width=False,
        )

    if st.button("☰  Menu", key="top_menu", type="secondary"):
        st.session_state["top_menu_open"] = not st.session_state.get("top_menu_open", False)
        st.rerun()

    left, middle = st.columns([4.8, 5.2], vertical_alignment="center")
    with left:
        st.markdown('<div class="ab-brand">ALGO<span>BOT</span> &nbsp;·&nbsp; TRADING DESK</div>',
                    unsafe_allow_html=True)
    with middle:
        st.markdown(f'<div class="ab-pills" style="justify-content:flex-end">{"".join(pills)}</div>',
                    unsafe_allow_html=True)

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
    st.markdown(f'<p style="color:{MUTED};font-size:.8rem;margin-top:2rem">{escape(text)} &nbsp;·&nbsp; algobot v{escape(__version__)}</p>',
                unsafe_allow_html=True)
