"""Plain-English guide to how TradeALGO turns a strategy idea into a tested, controlled trading workflow."""

import streamlit as st

from algobot import ui

ui.setup("How TradeALGO Works", "🗺️")
ui.header(
    "How TradeALGO Works",
    "A simple map from your trading idea to testing, paper trading, and controlled execution.",
    mode="guide:How it works",
)

ui.banner(
    "Start with the strategy. TradeALGO helps make the rules precise, test them, and only then move toward execution.",
    tone="info",
)

# Flowchart
st.markdown(
    """
    <style>
    .flow-wrap { display:flex; flex-direction:column; gap:10px; margin:18px 0 26px; }
    .flow-row { display:flex; align-items:stretch; gap:12px; }
    .flow-card {
        flex:1; border:1px solid #334155; border-radius:14px; padding:16px;
        background:#111827; min-height:108px;
    }
    .flow-card .num { font-size:12px; color:#38bdf8; font-weight:700; letter-spacing:.08em; }
    .flow-card .title { font-size:19px; font-weight:750; margin:5px 0 7px; }
    .flow-card .body { color:#cbd5e1; font-size:14px; line-height:1.45; }
    .flow-arrow { text-align:center; font-size:26px; color:#64748b; line-height:24px; }
    .flow-gate {
        border:1px solid #475569; border-radius:14px; padding:15px 18px;
        background:#0f172a; text-align:center;
    }
    .flow-gate strong { font-size:17px; }
    .flow-gate span { display:block; color:#cbd5e1; margin-top:4px; font-size:13px; }
    .flow-live {
        border:1px solid #14532d; background:#052e16;
        border-radius:14px; padding:15px 18px; text-align:center;
    }
    .flow-live strong { color:#86efac; font-size:17px; }
    .flow-live span { display:block; color:#bbf7d0; margin-top:4px; font-size:13px; }
    @media (max-width: 760px) {
        .flow-row { flex-direction:column; }
    }
    </style>

    <div class="flow-wrap">
      <div class="flow-row">
        <div class="flow-card">
          <div class="num">01</div>
          <div class="title">Idea</div>
          <div class="body">Describe what you see in the market and when you want to trade.</div>
        </div>
        <div class="flow-card">
          <div class="num">02</div>
          <div class="title">Strategy Builder</div>
          <div class="body">Turn the idea into exact entry, confirmation, stop, target, skip and sizing rules.</div>
        </div>
        <div class="flow-card">
          <div class="num">03</div>
          <div class="title">Backtest</div>
          <div class="body">Run the written rules on historical data and inspect trades, costs and drawdown.</div>
        </div>
      </div>

      <div class="flow-arrow">↓</div>

      <div class="flow-row">
        <div class="flow-card">
          <div class="num">04</div>
          <div class="title">Auto Tester</div>
          <div class="body">Test controlled variations without letting the learning layer rewrite the strategy or risk rules.</div>
        </div>
        <div class="flow-card">
          <div class="num">05</div>
          <div class="title">Reality Check</div>
          <div class="body">Review robustness, risk limits, sample quality and whether the evidence supports the next test stage.</div>
        </div>
        <div class="flow-card">
          <div class="num">06</div>
          <div class="title">Paper / Sandbox</div>
          <div class="body">Rehearse signals and execution without putting real money at risk.</div>
        </div>
      </div>

      <div class="flow-arrow">↓</div>

      <div class="flow-gate">
        <strong>Safety Gate</strong>
        <span>Risk checks → persistent kill switch → execution mode → human confirmation</span>
      </div>

      <div class="flow-arrow">↓</div>

      <div class="flow-row">
        <div class="flow-live">
          <strong>07 · OpenAlgo</strong>
          <span>Execution bridge that receives an approved order and routes it to the connected broker.</span>
        </div>
        <div class="flow-live">
          <strong>08 · Broker</strong>
          <span>Upstox or another supported broker handles the actual market order.</span>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("## How to make a strategy")

steps = [
    (
        "1. Define the market",
        "Choose the instrument, timeframe and trading hours.",
        "Example: NIFTY, 15-minute chart, trade only during your defined sessions.",
    ),
    (
        "2. Define the setup",
        "Write the exact condition that creates a possible trade.",
        "Example: price reaches a previous-week high/low or another explicitly defined level.",
    ),
    (
        "3. Define confirmation",
        "State exactly what must happen before entry. Avoid words like 'looks strong'.",
        "Example: a measurable candle, volume or indicator condition.",
    ),
    (
        "4. Define the order",
        "Specify direction, option type, strike selection, expiry and quantity.",
        "Every choice must be explicit enough that two people would make the same decision.",
    ),
    (
        "5. Define risk",
        "Write the stop-loss, position size, daily loss limit and monthly loss limit.",
        "These become testable risk constraints rather than decisions made after entry.",
    ),
    (
        "6. Define the exit",
        "Turn the profit-taking idea into a measurable rule.",
        "If the rule is 'I decide as it happens', it cannot be reproduced reliably in a backtest.",
    ),
    (
        "7. Define when NOT to trade",
        "List news conditions, time windows and other skip rules.",
        "A skip condition is part of the strategy, not an optional note.",
    ),
]

for title, body, example in steps:
    with st.expander(title, expanded=False):
        st.write(body)
        st.caption(example)

st.divider()
st.markdown("## Your brother's current strategy — what we know")

known = [
    ("Holding period", "Usually same day; sometimes overnight."),
    ("Timeframe", "15 minutes."),
    ("Levels", "Previous-week high/low, swing highs/lows, and manually drawn TradingView lines."),
    ("Entry idea", "Price touches a level plus an additional confirmation such as volume or an indicator."),
    ("Options", "Only buy; typically 1–2 strikes OTM; current weekly expiry."),
    ("Typical premium", "About ₹150."),
    ("Stop", "Fixed number of index points beyond the level."),
    ("Trading hours", "09:30–11:00 and 13:00–15:15."),
    ("Skip", "Big news."),
    ("Risk limits", "₹500 per day and ₹2,000 per month."),
]

for label, value in known:
    ui.check_row("PASS", label, value)

st.markdown("### Rules still needed before a deterministic backtest")
missing = [
    "Exact definition of a swing high / swing low.",
    "Exact confirmation indicator or volume condition.",
    "Exact stop distance in index points.",
    "Exact profit-taking / exit rule.",
    "Position sizing and lot-selection rule.",
    "Exact definition of a manually drawn TradingView level.",
    "Whether the OTM choice is always 1 strike, always 2 strikes, or rule-based.",
    "Expiry-day handling.",
    "Clarification of the recorded 21 Sep NIFTY 23500 CE 'sell' trade: opening short, exit, or hedge.",
]

for item in missing:
    ui.check_row("TODO", "Rule to specify", item)

st.divider()
st.markdown("## What each part of TradeALGO does")

roles = [
    ("Strategy Builder", "Writes the strategy as explicit rules.", "Does not place orders."),
    ("Backtest", "Checks the rules against historical data.", "Shows results and assumptions."),
    ("Auto Tester", "Tests controlled parameter variations.", "Does not rewrite the strategy by itself."),
    ("Reality Check", "Reviews evidence and risk readiness.", "Does not approve live trading automatically."),
    ("Paper Trading", "Rehearses the workflow with fake money.", "No real broker order."),
    ("OpenAlgo", "Execution infrastructure.", "Receives an approved order; it is not the strategy owner."),
    ("Live Trading", "Controlled execution.", "Requires explicit live mode, kill switch clear and human confirmation."),
]

for name, job, boundary in roles:
    with st.expander(name):
        st.write(f"**Job:** {job}")
        st.write(f"**Boundary:** {boundary}")

st.divider()
st.markdown("## The simple rule")

ui.banner(
    "Strategy first → test → reality check → paper/sandbox → safety gate → OpenAlgo → broker.",
    tone="success",
)

st.page_link("pages/10_Strategy_Builder.py", label="Start building the strategy", icon="🧠")
st.page_link("pages/5_Backtest.py", label="Backtest a written strategy", icon="📊")

ui.footer_note()
