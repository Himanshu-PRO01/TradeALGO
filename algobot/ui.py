"""The look and feel of every page: a dark trading desk.

Each page starts with `ui.setup(...)` (which must be the first Streamlit call) and then `ui.header(...)`.
Colours come from palette.py so the CSS and the charts always agree: green is up, profit and buy; red is
down, loss and sell; amber means caution or practice.
"""
from __future__ import annotations

from html import escape
from typing import Iterable, Optional

import streamlit as st

from . import __version__
from .appstate import is_hosted, password_gate
from .palette import BG, BLUE, BORDER, DOWN, MUTED, PANEL, TEXT, UP, WARN

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

/* larger glassy sidebar navigation */
[data-testid="stSidebar"] [data-testid="stPageLink"] {
    margin: 7px 0;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    min-height: 50px;
    padding: 11px 14px !important;
    border: 1px solid rgba(255,255,255,.09);
    border-radius: 14px;
    background: rgba(255,255,255,.045);
    box-shadow: 0 8px 24px rgba(0,0,0,.16), inset 0 1px 0 rgba(255,255,255,.055);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    font-size: .96rem;
    font-weight: 650;
    letter-spacing: .01em;
    transition: background .18s ease, border-color .18s ease, transform .18s ease, box-shadow .18s ease;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: rgba(255,255,255,.085);
    border-color: rgba(59,130,246,.42);
    box-shadow: 0 10px 28px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.08);
    transform: translateX(2px);
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
    background: linear-gradient(135deg, rgba(59,130,246,.20), rgba(22,199,132,.10));
    border-color: rgba(59,130,246,.48);
    box-shadow: 0 10px 30px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.09);
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a p {
    font-size: .96rem;
    font-weight: 650;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a span {
    font-size: 1.15rem;
}

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
</style>
"""


def _menu() -> None:
    """Trader-friendly sidebar navigation shared by every page."""
    # Streamlit uses dashboard.py as the deployed entrypoint; keep Home tied to it.
    home_page = "dashboard.py"
    with st.sidebar:
        st.markdown(
            f'<div class="ab-menu-head"><div class="ab-menu-brand">ALGO<span>BOT</span></div>'
            f'<div class="ab-menu-status">TRADING DESK · {"HOSTED" if is_hosted() else "LOCAL"} · LIVE OFF</div></div>',
            unsafe_allow_html=True,
        )
        sections = [
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
                ("💬", "Feedback", "pages/8_Feedback.py"),
                ("🚀", "Deployment Status", "pages/9_Deployment_Status.py"),
                ("🧠", "Strategy Builder", "pages/10_Strategy_Builder.py"),
                ("📈", "Market Charts", "pages/12_Market_Charts.py"),
            ]),
            ("Execution", [
                ("🔴", "Live Trading", "pages/11_Live_Trading.py"),
            ]),
        ]
        for section, links in sections:
            st.markdown(f'<div class="ab-menu-section">{escape(section)}</div>', unsafe_allow_html=True)
            for icon_, label, path in links:
                st.page_link(path, label=f"{icon_}  {label}", use_container_width=True)
        st.caption("🔒 Live orders are locked · fake money only")


def setup(title: str, icon: str = "📈", layout: str = "wide") -> None:
    """First call on every page: page settings, styling, and the password screen if one is set."""
    st.set_page_config(page_title=f"{title} | Algobot", page_icon=icon, layout=layout, initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)
    _menu()
    password_gate()


def pill(text: str, tone: str = "green") -> str:
    return f'<span class="ab-pill {escape(tone)}">{escape(text)}</span>'


def header(title: str, subtitle: str = "", mode: Optional[str] = None) -> None:
    """Brand bar with the safety pills, then the page title."""
    pills = [pill("NO LIVE ORDERS", "green")]
    if mode:
        tone = {"practice": "amber", "backtest": "blue", "journal": "green", "research": "blue"}.get(mode.split(":")[0], "blue")
        pills.insert(0, pill(mode.split(":", 1)[-1].upper(), tone))
    pills.append(pill("HOSTED" if is_hosted() else "LOCAL", "blue"))
    st.markdown(f'<div class="ab-top"><div class="ab-brand">ALGO<span>BOT</span> &nbsp;·&nbsp; TRADING DESK</div>'
                f'<div class="ab-pills">{"".join(pills)}</div></div>', unsafe_allow_html=True)
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)


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


def footer_note(text: str = "Practice and research tool. Not advice. It never places orders and never asks for broker keys.") -> None:
    st.markdown(f'<p style="color:{MUTED};font-size:.8rem;margin-top:2rem">{escape(text)} &nbsp;·&nbsp; algobot v{escape(__version__)}</p>',
                unsafe_allow_html=True)
