"""The look and feel of every page: a premium quant trading workstation.

Each page starts with `ui.setup(...)` (which must be the first Streamlit call) and then `ui.header(...)`.
Colours come from palette.py so the CSS and the charts always agree: green is positive, red is negative.
"""
from __future__ import annotations

import pathlib
import sys
from html import escape
from typing import Iterable, Optional

import streamlit as st

try:
    import streamlit.components.v2 as _components_v2
except ImportError:
    _components_v2 = None

from . import __version__
from .appstate import is_hosted, password_gate
from .execution_policy import ExecutionMode, get_execution_mode
from .palette import BG, BLUE, BORDER, DOWN, MUTED, PANEL, TEXT, UP, WARN, PURPLE


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
/* Base typography */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}
.block-container {{ padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1500px; }}
h1, h2, h3, h4, h5, h6 {{ letter-spacing: -0.01em; color: {TEXT}; }}
h1 {{ font-size: 2rem !important; line-height: 1.2; font-weight: 700; margin-bottom: 0.6rem; }}
h2 {{ font-size: 1.5rem !important; line-height: 1.25; font-weight: 600; }}
h3 {{ font-size: 1.25rem !important; line-height: 1.3; font-weight: 600; }}
p, span, div {{ color: {TEXT}; font-size: 0.93rem; }}
[data-testid="stSidebar"] {{ background: {PANEL}; border-right: 1px solid {BORDER}; }}
[data-testid="stSidebarNav"] {{ display:none; }}
[data-testid="stAppViewContainer"] {{ background: {BG}; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] > div:first-child {{ padding-top: 1.2rem; }}

/* Menu */
.ab-menu-head {{ padding:4px 6px 12px; border-bottom:1px solid {BORDER}; margin-bottom:10px; }}
.ab-menu-brand {{ font-weight:700; font-size:1.1rem; color: {TEXT}; display:flex; flex-direction:column; gap:2px; }}
.ab-menu-brand span {{ color:{BLUE}; font-size:0.75rem; font-weight:500; letter-spacing:0.05em; text-transform:uppercase; }}
.ab-menu-section {{ color:{MUTED}; font-size:.68rem; font-weight:600; letter-spacing:.08em; text-transform:uppercase; margin:16px 6px 6px; }}
.ab-menu-locked {{ margin: 24px 12px 12px; padding: 12px; background: {DOWN}15; border: 1px solid {DOWN}40; border-radius: 8px; color: {DOWN}; font-size: 0.75rem; font-weight: 600; text-align: center; display: flex; align-items: center; justify-content: center; gap: 6px; letter-spacing: 0.05em; }}
.ab-menu-locked.active {{ background: {UP}15; border-color: {UP}40; color: {UP}; }}

[data-testid="stSidebar"] [data-testid="stPageLink"] {{ margin: 2px 0; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {{
    min-height: 40px;
    padding: 8px 12px !important;
    border: 1px solid transparent;
    border-radius: 6px;
    background: transparent;
    font-size: .9rem;
    font-weight: 500;
    color: {MUTED};
    transition: all .15s ease;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {{
    background: {BORDER};
    color: {TEXT};
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {{
    background: {BLUE}1A;
    border: 1px solid {BLUE}33;
    color: {BLUE};
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a p {{ font-size: .9rem; font-weight: 500; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a span {{ font-size: 1rem; }}

/* Top Header */
.ab-header {{ display:flex; justify-content:space-between; align-items:center; padding-bottom:16px; border-bottom:1px solid {BORDER}; margin-bottom:24px; flex-wrap:wrap; gap:16px; }}
.ab-header-title {{ display:flex; flex-direction:column; gap:4px; }}
.ab-header-title h1 {{ margin:0; font-size:2rem !important; line-height:1.2; }}
.ab-header-title span {{ color:{MUTED}; font-size:1rem; line-height:1.4; }}
.ab-header-status {{ display:flex; gap:12px; flex-wrap:wrap; }}
.ab-status-card {{ display:flex; flex-direction:column; background:{PANEL}; border:1px solid {BORDER}; border-radius:6px; padding:6px 12px; min-width:110px; }}
.ab-status-card span.label {{ color:{MUTED}; font-size:0.65rem; text-transform:uppercase; letter-spacing:0.05em; font-weight:600; }}
.ab-status-card span.value {{ color:{TEXT}; font-size:0.8rem; font-weight:600; display:flex; align-items:center; gap:4px; }}
.ab-status-card span.value.locked {{ color:{DOWN}; }}
.ab-status-card span.value.active {{ color:{UP}; }}
.ab-status-card span.value.research {{ color:{PURPLE}; }}
.ab-status-card span.value.warning {{ color:{WARN}; }}

/* KPI Cards */
.ab-kpis {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:12px; margin-bottom:24px; }}
.ab-kpi {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:8px; padding:12px 16px; display:flex; flex-direction:column; gap:4px; transition:border-color .15s ease; }}
.ab-kpi:hover {{ border-color:{MUTED}; }}
.ab-kpi .label {{ color:{MUTED}; font-size:0.75rem; text-transform:uppercase; font-weight:600; letter-spacing:0.05em; }}
.ab-kpi .value {{ font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size:1.15rem; font-weight:700; color:{TEXT}; }}
.ab-kpi .value.up {{ color:{UP}; }}
.ab-kpi .value.down {{ color:{DOWN}; }}
.ab-kpi .value.warn {{ color:{WARN}; }}

/* Badges */
.ab-badge {{ display:inline-flex; align-items:center; padding:2px 8px; border-radius:4px; font-size:0.7rem; font-weight:600; letter-spacing:0.02em; text-transform:uppercase; border:1px solid; }}
.ab-badge.green {{ color:{UP}; background:{UP}15; border-color:{UP}30; }}
.ab-badge.red {{ color:{DOWN}; background:{DOWN}15; border-color:{DOWN}30; }}
.ab-badge.amber {{ color:{WARN}; background:{WARN}15; border-color:{WARN}30; }}
.ab-badge.blue {{ color:{BLUE}; background:{BLUE}15; border-color:{BLUE}30; }}
.ab-badge.purple {{ color:{PURPLE}; background:{PURPLE}15; border-color:{PURPLE}30; }}
.ab-badge.gray {{ color:{MUTED}; background:{MUTED}15; border-color:{MUTED}30; }}

/* Banners */
.ab-banner {{ display:flex; align-items:center; gap:12px; padding:12px 16px; border-radius:8px; margin-bottom:16px; border-left:4px solid; }}
.ab-banner.safety {{ background:{DOWN}10; border:1px solid {DOWN}20; border-left-color:{DOWN}; }}
.ab-banner.safety .icon {{ color:{DOWN}; font-size:1.2rem; }}
.ab-banner.safety .content {{ color:{TEXT}; font-size:0.9rem; font-weight:500; }}
.ab-banner.warning {{ background:{WARN}10; border:1px solid {WARN}20; border-left-color:{WARN}; }}
.ab-banner.info {{ background:{BLUE}10; border:1px solid {BLUE}20; border-left-color:{BLUE}; }}

/* General Elements */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {{
    border-radius: 6px; font-weight: 500; border: 1px solid {BORDER}; background: {PANEL}; color: {TEXT}; transition: all .15s ease;
}}
.stButton > button:hover {{ border-color: {BLUE}; color: {BLUE}; }}
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"],
.stMultiSelect [data-baseweb="select"], .stDateInput input, .stTimeInput input {{ border-radius: 6px; background: {PANEL}; border-color: {BORDER}; }}
[data-testid="stMetric"] {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px; padding: 12px 16px; }}
[data-testid="stMetricLabel"] {{ color: {MUTED}; text-transform: uppercase; font-size: 0.72rem; letter-spacing: .05em; font-weight: 600; }}
[data-testid="stMetricValue"] {{ font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-weight: 600; color: {TEXT}; }}
[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 8px; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 500; color: {MUTED}; }}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{ color: {TEXT}; }}
[data-testid="stExpander"] {{ border: 1px solid {BORDER}; border-radius: 8px; background: {PANEL}; }}

/* Research & Learning Cards */
.ab-research-card {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:8px; padding:16px; margin-bottom:12px; display:flex; flex-direction:column; gap:8px; }}
.ab-research-card h4 {{ margin:0; font-size:1rem; color:{TEXT}; display:flex; justify-content:space-between; align-items:center; }}
.ab-research-card p {{ margin:0; font-size:0.85rem; color:{MUTED}; line-height:1.4; }}
.ab-research-card .footer {{ display:flex; justify-content:space-between; align-items:center; margin-top:8px; padding-top:8px; border-top:1px solid {BORDER}; }}

.ab-learning {{ background: linear-gradient(180deg, {PANEL} 0%, {BG} 100%); border:1px solid {PURPLE}40; border-radius:8px; padding:16px; margin-bottom:16px; box-shadow: 0 4px 20px {PURPLE}10; }}
.ab-learning-header {{ display:flex; align-items:center; gap:8px; margin-bottom:12px; color:{PURPLE}; font-weight:600; font-size:0.9rem; letter-spacing:0.05em; text-transform:uppercase; }}
.ab-learning-row {{ display:flex; justify-content:space-between; margin-bottom:8px; font-size:0.85rem; }}
.ab-learning-row .lab {{ color:{MUTED}; }}
.ab-learning-row .val {{ color:{TEXT}; font-weight:500; }}

/* Mobile */
@media (max-width: 768px) {{
    .block-container {{ padding: 0.75rem 0.75rem 4.5rem; max-width: 100%; }}
    .ab-header {{ flex-direction:column; align-items:flex-start; gap:12px; }}
    .ab-header-status {{ width:100%; justify-content:space-between; overflow-x:auto; flex-wrap:nowrap; padding-bottom:4px; }}
    .ab-status-card {{ flex: 0 0 auto; min-width:auto; }}
    .ab-kpis {{ grid-template-columns:repeat(2, 1fr); }}
    h1 {{ font-size: 1.75rem !important; }}
    h2 {{ font-size: 1.35rem !important; }}
    h3 {{ font-size: 1.2rem !important; }}
    .ab-header-title h1 {{ font-size: 1.75rem !important; }}
    .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {{ min-height: 44px; }}
    .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input, .stTimeInput input {{ min-height: 44px; font-size:16px !important; }}
    [data-testid="stSidebar"] {{ min-width: min(88vw, 340px); max-width: min(88vw, 340px); }}
    [data-testid="stSidebar"] [data-testid="stPageLink"] a {{ min-height: 44px; }}
}}
@media (max-width: 430px) {{
    .ab-kpis {{ grid-template-columns: 1fr; }}
}}
</style>
"""

def _execution_status() -> tuple[str, str, str]:
    mode = get_execution_mode()
    if mode is ExecutionMode.LIVE:
        return "LIVE", "active", "● LIVE"
    if mode is ExecutionMode.PAPER:
        return "PAPER", "research", "● PAPER"
    if mode is ExecutionMode.SANDBOX:
        return "SANDBOX", "warning", "● SANDBOX"
    if mode is ExecutionMode.RESEARCH:
        return "RESEARCH", "research", "● RESEARCH"
    return "DISABLED", "locked", "● LIVE DISABLED"


def _menu() -> None:
    """Trader-friendly sidebar navigation shared by every page."""
    # dashboard.py is the registered Streamlit entrypoint on Cloud AND locally
    home_page = "dashboard.py"
    with st.sidebar:
        st.markdown(
            f'<div class="ab-menu-head"><div class="ab-menu-brand">TradeALGO<span>RESEARCH LAB</span></div></div>',
            unsafe_allow_html=True,
        )
        sections = [
            ("Trading", [
                ("🏠", "Trade Desk", home_page),
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
                ("🧠", "Strategy Builder", "pages/10_Strategy_Builder.py"),
                ("🤖", "Auto Tester", "pages/13_Auto_Tester.py"),
                ("🔬", "Strategy Scanner", "pages/15_Strategy_Scanner.py"),
                ("💬", "Feedback", "pages/8_Feedback.py"),
                ("🚀", "Deployment Status", "pages/9_Deployment_Status.py"),
            ]),
            ("Paper / Sandbox", [
                ("📝", "Paper Trading", "pages/16_Paper_Trading.py"),
                ("🧪", "Upstox Sandbox", "pages/14_Upstox_Sandbox.py"),
                ("🎬", "Sandbox Rehearsal", "pages/17_Sandbox_Rehearsal.py"),
            ]),
            ("Execution", [
                ("🔴", "Live Trading", "pages/11_Live_Trading.py"),
            ]),
        ]
        for section, links in sections:
            st.markdown(f'<div class="ab-menu-section">{escape(section)}</div>', unsafe_allow_html=True)
            for icon_, label, path in links:
                try:
                    st.page_link(path, label=f"{icon_}  {label}", use_container_width=True)
                except Exception:
                    pass # Skip missing pages if any
                    
        _, _, execution_badge = _execution_status()
        badge_class = "active" if get_execution_mode() is ExecutionMode.LIVE else ""
        st.markdown(f'<div class="ab-menu-locked {badge_class}">{escape(execution_badge)}</div>', unsafe_allow_html=True)

def setup(title: str, icon: str = "📈", layout: str = "wide") -> None:
    """First call on every page: page settings, styling, and the password screen if one is set."""
    st.set_page_config(page_title=f"{title} | TradeALGO", page_icon=icon, layout=layout, initial_sidebar_state="collapsed")
    st.markdown(CSS, unsafe_allow_html=True)
    _menu()
    swipe_component = _swipe_menu_component()
    if swipe_component is not None:
        try:
            swipe_component(key="algobot_mobile_swipe_menu")
        except Exception:
            pass
    password_gate()

def badge(text: str, tone: str = "gray") -> str:
    return f'<span class="ab-badge {escape(tone)}">{escape(text)}</span>'

def pill(text: str, tone: str = "green") -> str:
    # Backwards compatibility alias
    return badge(text, tone)

def header(title: str, subtitle: str = "", mode: Optional[str] = None) -> None:
    """Polished header with system status cards."""
    # Determine mode tone
    mode_tone = "blue"
    mode_text = "Standard Mode"
    if mode:
        m = mode.split(":")[0].lower()
        mode_text = mode.split(":", 1)[-1].upper()
        mode_tone = {"practice": "amber", "backtest": "blue", "journal": "green", "research": "purple"}.get(m, "blue")
    else:
        mode_text = "RESEARCH MODE"
        mode_tone = "purple"
        
    execution_text, execution_tone, _ = _execution_status()
    openalgo_host = bool(os.environ.get("OPENALGO_HOST"))
    openalgo_key = bool(os.environ.get("OPENALGO_API_KEY"))
    broker_text = "Configured" if openalgo_host and openalgo_key else "Not Configured"
    status_html = f"""<div class="ab-header">
<div class="ab-header-title">
<h1>{escape(title)}</h1>
<span>{escape(subtitle) if subtitle else 'TradeALGO • Research • Test • Validate'}</span>
</div>
<div class="ab-header-status">
<div class="ab-status-card">
<span class="label">SYSTEM</span>
<span class="value {escape(mode_tone)}">{escape(mode_text)}</span>
</div>
<div class="ab-status-card">
<span class="label">EXECUTION</span>
<span class="value {escape(execution_tone)}">{escape(execution_text)}</span>
</div>
<div class="ab-status-card">
<span class="label">BROKER</span>
<span class="value">{escape(broker_text)}</span>
</div>
</div>
</div>"""
    st.markdown(status_html, unsafe_allow_html=True)

def ticker(items: Iterable) -> None:
    """A strip of live-style numbers. Each item is (label, value, tone) with tone 'up', 'down', 'warn' or None."""
    cells = ""
    for label, value, t in items:
        tone_class = f" {escape(t)}" if t else ""
        cells += f"""<div class="ab-kpi">
<span class="label">{escape(str(label))}</span>
<span class="value{tone_class}">{escape(str(value))}</span>
</div>"""
    st.markdown(f'<div class="ab-kpis">{cells}</div>', unsafe_allow_html=True)

def card(title: str, body: str, icon: str = "") -> str:
    """Reusable research card."""
    return f"""<div class="ab-research-card">
<h4>{escape(title)} {escape(icon)}</h4>
<p>{escape(body)}</p>
</div>"""

def check_row(status: str, title: str, detail: str) -> None:
    """One audit-style line with a coloured status badge."""
    t = {"PASS": "green", "WARN": "amber", "FAIL": "red", "SKIP": "blue", "TODO": "gray"}.get(status, "blue")
    st.markdown(f'<div style="display:flex; gap:12px; align-items:flex-start; padding:8px 0; border-bottom:1px solid {BORDER};">'
                f'{badge(status, t)}<div><div style="font-weight:600; font-size:0.9rem;">{escape(title)}</div>'
                f'<div style="color:{MUTED}; font-size:0.85rem;">{escape(detail)}</div></div></div>', unsafe_allow_html=True)

def banner(text: str, tone: str = "info", icon: str = "ℹ️") -> None:
    """Reusable colored banners: safety (red), warning (amber), info (blue)."""
    st.markdown(f"""<div class="ab-banner {escape(tone)}">
<div class="icon">{escape(icon)}</div>
<div class="content">{escape(text)}</div>
</div>""", unsafe_allow_html=True)

def learning_memory(observations: dict, confidence: str, action: str) -> None:
    """Reusable learning memory component for Auto Tester."""
    rows = ""
    for k, v in observations.items():
        rows += f'<div class="ab-learning-row"><span class="lab">{escape(k)}</span><span class="val">{escape(str(v))}</span></div>'
    
    html = f"""
    <div class="ab-learning">
        <div class="ab-learning-header">🧠 Learning Memory</div>
        {rows}
        <div class="ab-learning-row"><span class="lab">Confidence</span><span class="val">{escape(confidence)}</span></div>
        <div class="ab-learning-row" style="margin-top:8px; padding-top:8px; border-top:1px solid {BORDER};">
            <span class="lab">Action</span><span class="val" style="color:{BLUE}">{escape(action)}</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def tone(value: float) -> str:
    return "up" if value > 0 else ("down" if value < 0 else "")

def inr(value: float, sign: bool = False) -> str:
    """Rupees with Indian-style thousands."""
    prefix = "+" if sign and value > 0 else ""
    return f"{prefix}₹{value:,.0f}" if value >= 0 else f"-₹{abs(value):,.0f}"

def show_chart(chart) -> None:
    """Draw an Altair chart full width, on any Streamlit version."""
    if chart is None:
        st.caption("Nothing to draw yet.")
        return
    try:
        st.altair_chart(chart, width="stretch")
    except TypeError:
        st.altair_chart(chart, use_container_width=True)

def show_table(frame, **kwargs) -> None:
    try:
        st.dataframe(frame, width="stretch", **kwargs)
    except TypeError:
        st.dataframe(frame, use_container_width=True, **kwargs)

def footer_note(text: str = "Practice and research tool. Not advice. It never places orders and never asks for broker keys.") -> None:
    st.markdown(f'<p style="color:{MUTED};font-size:.8rem;margin-top:2rem">{escape(text)} &nbsp;·&nbsp; TradeALGO v{escape(__version__)}</p>',
                unsafe_allow_html=True)
