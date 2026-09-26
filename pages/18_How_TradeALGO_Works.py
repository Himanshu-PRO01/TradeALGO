"""Start page for the TradeALGO guided workflow."""

import streamlit as st

from algobot import ui

ui.setup("How TradeALGO Works", "🗺️")
ui.header(
    "How TradeALGO Works",
    "Start here. Follow the workflow from strategy idea to controlled execution.",
    mode="research:START HERE",
)

st.markdown(
    """
<div class="ab-hero">
  <div class="ab-kicker">START HERE · FOR YOUR BROTHER</div>
  <h2>One clear path from idea → tested strategy → controlled execution</h2>
  <p>
    TradeALGO is organised as a workflow. You do not need to understand every page at once.
    Start with the strategy, make every rule measurable, test it, rehearse it, and only then
    reach the execution layer.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

ui.workflow_nav("guide")

st.markdown("### 🧭 Your TradeALGO path")

st.info(
    "Important: the Next button is never blocked by a completion banner. "
    "You can move forward at any time; the completion indicators are guidance, not permissions."
)

st.markdown("### 👨‍💻 What you do on each step")

steps = [
    ("01", "Idea", "Describe the setup in plain language. Write down where the level comes from, what you look for, and when you skip the trade."),
    ("02", "Strategy Builder", "Convert the idea into measurable entry, confirmation, stop, target, position-size and skip rules."),
    ("03", "Backtest", "Run the written rules on historical data and inspect trade count, P&L, drawdown and costs."),
    ("04", "Auto Tester", "Test controlled parameter variations. Treat the output as research evidence, not as a promise or an automatic strategy rewrite."),
    ("05", "Reality Check", "Review the evidence, risk limits, sample quality and robustness before moving to practice."),
    ("06", "Paper Trading", "Rehearse the workflow with simulated money and record what actually happens."),
    ("07", "Upstox Sandbox", "Connect the sandbox credentials privately and verify the broker-facing order path without real-money execution."),
    ("08", "Sandbox Rehearsal", "Run the end-to-end execution rehearsal: strategy/risk checks → execution layer → sandbox."),
    ("09", "Live Trading", "Only after the earlier work is understood. Live execution remains behind explicit execution-mode, kill-switch and human-confirmation safeguards."),
]
for number, title, body in steps:
    st.markdown(
        f'<div class="ab-check"><span class="ab-pill blue">{number}</span>'
        f'<div class="txt"><b>{title}</b><span>{body}</span></div></div>',
        unsafe_allow_html=True,
    )

st.markdown("### 🧠 How to make your strategy")

q1, q2 = st.columns(2)
with q1:
    st.markdown(ui.card("1. Market", "What instrument and market are you trading?", "📌"), unsafe_allow_html=True)
    st.markdown(ui.card("2. Setup", "What exact price structure creates the opportunity?", "🎯"), unsafe_allow_html=True)
    st.markdown(ui.card("3. Confirmation", "What observable condition confirms the entry?", "✅"), unsafe_allow_html=True)
    st.markdown(ui.card("4. Order", "Which side, instrument, expiry and strike rule?", "🧾"), unsafe_allow_html=True)
with q2:
    st.markdown(ui.card("5. Stop", "Where is the trade invalidated, and how is the distance measured?", "🛑"), unsafe_allow_html=True)
    st.markdown(ui.card("6. Exit", "What exact rule closes the position: target, trailing rule, time or invalidation?", "🚪"), unsafe_allow_html=True)
    st.markdown(ui.card("7. Skip", "Which market conditions make the strategy stand aside?", "⛔"), unsafe_allow_html=True)
    st.markdown(ui.card("8. Size", "How many units/lots are allowed under the risk limit?", "📐"), unsafe_allow_html=True)

st.markdown("### 📋 What we already know about the brother's current strategy")
known = [
    ("Holding period", "Usually same day; sometimes overnight."),
    ("Timeframe", "15-minute chart."),
    ("Levels", "Previous-week high/low, swing highs/lows, and manually drawn TradingView lines."),
    ("Entry idea", "Price touches a level plus extra confirmation such as volume or an indicator."),
    ("Options", "Only buy selected; typical strike is 1–2 strikes OTM; current weekly expiry; typical premium around ₹150."),
    ("Trading windows", "09:30–11:00 and 13:00–15:15."),
    ("Skip condition", "Big news."),
    ("Risk limits", "₹500/day and ₹2,000/month."),
]
for label, value in known:
    st.markdown(
        f'<div class="ab-check"><span class="ab-pill green">KNOWN</span>'
        f'<div class="txt"><b>{label}</b><span>{value}</span></div></div>',
        unsafe_allow_html=True,
    )

st.warning(
    "Before coding this strategy, several rules still need exact definitions: "
    "swing-high/low definition, the confirmation indicator/volume condition, stop distance, "
    "profit-taking rule, position sizing/lots, how manual levels are defined, whether to use "
    "1 or 2 strikes OTM, expiry-day handling, and the meaning of the 21 Sep CE 'sell' example."
)

st.markdown("### 🚦 Open the next step")
a, b, c = st.columns(3)
with a:
    st.page_link("pages/10_Strategy_Builder.py", label="🧠 Open Strategy Builder", icon="🧠", use_container_width=True)
with b:
    st.page_link("pages/5_Backtest.py", label="📊 Open Backtest", icon="📊", use_container_width=True)
with c:
    st.page_link("pages/6_Reality_check.py", label="🛡️ Open Reality Check", icon="🛡️", use_container_width=True)

st.markdown("### 🔐 Safety architecture")
st.markdown(
    """
<div class="ab-card">
  <h4>Strategy first → risk checks → execution gate → OpenAlgo → broker</h4>
  <p>
    The AI/research layer is for defining, testing and analysing strategies.
    The deterministic execution layer handles risk and order mechanics.
    OpenAlgo is the execution bridge; it does not invent the strategy.
    Live mode remains explicitly gated and is not enabled by default.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

ui.footer_note("TradeALGO workflow guide. Research and practice first; execution is a separate controlled stage.")
