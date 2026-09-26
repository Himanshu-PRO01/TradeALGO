"""Brother-friendly guide to using TradeALGO from idea to controlled execution."""

import streamlit as st

from algobot import ui

ui.setup("How TradeALGO Works", "🗺️")
ui.header(
    "How TradeALGO Works — Start Here",
    "This page explains exactly what you and your brother need to do, in order.",
    mode="guide:How it works",
)

ui.banner(
    "Bhai ke liye simple rule: pehle strategy ko exact rules mein likho → test karo → paper/sandbox mein rehearse karo → tabhi execution.",
    tone="success",
)

st.markdown("## 👋 Bhai, website par tumhe kya karna hai?")

st.markdown(
    """
    <div style="border:1px solid #334155;border-radius:16px;padding:20px;background:#0f172a;margin:12px 0 20px;">
      <div style="font-size:18px;font-weight:750;margin-bottom:10px;">Tumhara main kaam strategy ko clearly define karna hai.</div>
      <ol style="color:#cbd5e1;line-height:1.8;margin-bottom:0;">
        <li>Apna setup explain karo.</li>
        <li>Entry aur confirmation ko exact rule banao.</li>
        <li>Stop-loss, target, quantity aur skip conditions fix karo.</li>
        <li>Strategy Builder mein rules likho.</li>
        <li>Backtest se historical result dekho.</li>
        <li>Auto Tester se controlled variations test karo.</li>
        <li>Reality Check mein risk aur robustness dekho.</li>
        <li>Paper/Sandbox mein execution rehearse karo.</li>
        <li>Sab clear hone ke baad hi execution layer/OpenAlgo ko use karo.</li>
      </ol>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("## 🎬 1-minute walkthrough")

st.caption(
    "Flow ko left-to-right samjho. Har stage ka output agle stage ka input hai. "
    "Abhi is repo mein dedicated MP4 video file available nahi hai, isliye neeche same walkthrough ko interactive form mein diya gaya hai."
)

st.markdown(
    """
    <style>
    .flow-wrap { display:flex; flex-direction:column; gap:10px; margin:16px 0 24px; }
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
    @media (max-width: 760px) { .flow-row { flex-direction:column; } }
    </style>
    <div class="flow-wrap">
      <div class="flow-row">
        <div class="flow-card"><div class="num">01</div><div class="title">Idea</div><div class="body">Market setup aur trade ka reason define karo.</div></div>
        <div class="flow-card"><div class="num">02</div><div class="title">Strategy Builder</div><div class="body">Idea ko exact entry, confirmation, stop, target, skip aur sizing rules mein badlo.</div></div>
        <div class="flow-card"><div class="num">03</div><div class="title">Backtest</div><div class="body">Historical data par written rules ko test karo.</div></div>
      </div>
      <div class="flow-arrow">↓</div>
      <div class="flow-row">
        <div class="flow-card"><div class="num">04</div><div class="title">Auto Tester</div><div class="body">Controlled parameter variations test karo; strategy ko silently rewrite nahi kiya jata.</div></div>
        <div class="flow-card"><div class="num">05</div><div class="title">Reality Check</div><div class="body">Risk, robustness, sample quality aur next-stage readiness review karo.</div></div>
        <div class="flow-card"><div class="num">06</div><div class="title">Paper / Sandbox</div><div class="body">Fake-money rehearsal se signal aur execution workflow check karo.</div></div>
      </div>
      <div class="flow-arrow">↓</div>
      <div class="flow-gate"><strong>SAFETY GATE</strong><span>Risk checks → persistent kill switch → execution mode → human confirmation</span></div>
      <div class="flow-arrow">↓</div>
      <div class="flow-row">
        <div class="flow-live"><strong>07 · OpenAlgo</strong><span>Approved order ko execution bridge ke through broker tak bhejne ka infrastructure.</span></div>
        <div class="flow-live"><strong>08 · Broker</strong><span>Connected broker actual market order handle karta hai.</span></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("## ✅ Tumhe kis order mein kaam karna hai")

todo = [
    ("1", "Strategy Builder", "Strategy ke saare rules likho. Agar koi rule subjective hai, usko exact banao."),
    ("2", "Backtest", "Historical result, trades, drawdown aur assumptions dekho."),
    ("3", "Auto Tester", "Controlled variations test karo; result ko evidence samjho, guarantee nahi."),
    ("4", "Reality Check", "Risk limits aur robustness review karo."),
    ("5", "Paper Trading / Sandbox", "Real money ke bina workflow rehearse karo."),
    ("6", "OpenAlgo / execution", "Sirf approved order ko execution infrastructure tak le jao."),
]
for n, name, job in todo:
    with st.expander(f"{n}. {name}", expanded=(n == "1")):
        st.write(job)

st.markdown("## 🧩 Strategy banane ke 7 sawaal")

questions = [
    ("1. Market", "Kya trade karna hai? NIFTY/BANKNIFTY/stock? Kaunsa timeframe? Kaunse trading hours?"),
    ("2. Setup", "Kaunsa exact level/setup trade ko possible banata hai?"),
    ("3. Confirmation", "Entry se pehle exactly kya confirm hona chahiye?"),
    ("4. Order", "BUY/SELL, CE/PE, strike, expiry aur quantity ka exact rule kya hai?"),
    ("5. Risk", "Stop-loss aur max daily/monthly loss kya hai?"),
    ("6. Exit", "Profit kaise book hoga? Exact measurable rule kya hai?"),
    ("7. Skip", "Kab trade nahi karna hai — news, time, volatility ya koi aur condition?"),
]
for title, text in questions:
    ui.check_row("TODO", title, text)

st.divider()
st.markdown("## 📌 Tumhare bhai ki current strategy — jo already known hai")

known = [
    ("Holding period", "Usually same day; sometimes overnight."),
    ("Timeframe", "15 minutes."),
    ("Levels", "Previous-week high/low, swing highs/lows, and manually drawn TradingView lines."),
    ("Entry idea", "Price touches a level plus additional confirmation such as volume or an indicator."),
    ("Options", "Only buy; typically 1–2 strikes OTM; current weekly expiry."),
    ("Typical premium", "About ₹150."),
    ("Stop", "Fixed number of index points beyond the level."),
    ("Trading hours", "09:30–11:00 and 13:00–15:15."),
    ("Skip", "Big news."),
    ("Risk limits", "₹500 per day and ₹2,000 per month."),
]
for label, value in known:
    ui.check_row("PASS", label, value)

st.markdown("### ❗ Backtest se pehle ye rules exact karne hain")

missing = [
    "Swing high / swing low ki exact definition.",
    "Confirmation indicator ya volume condition.",
    "Exact stop distance in index points.",
    "Exact profit-taking / exit rule.",
    "Position sizing aur lot-selection rule.",
    "Manually drawn TradingView level ki exact definition.",
    "1 OTM vs 2 OTM ka fixed/rule-based choice.",
    "Expiry-day handling.",
    "21 Sep NIFTY 23500 CE 'sell' trade: opening short, exit, ya hedge?",
]
for item in missing:
    ui.check_row("TODO", "Rule to specify", item)

st.divider()
st.markdown("## 🛠️ Website ke pages ka kaam")

roles = [
    ("Strategy Builder", "Strategy ko explicit rules mein likhna.", "Orders place nahi karta."),
    ("Backtest", "Historical data par rules test karna.", "Results aur assumptions dikhata hai."),
    ("Auto Tester", "Controlled variations test karna.", "Khud se strategy/risk rules rewrite nahi karta."),
    ("Reality Check", "Evidence aur risk readiness review karna.", "Live approval automatically nahi deta."),
    ("Paper Trading", "Fake-money rehearsal.", "Real broker order nahi."),
    ("Upstox Sandbox", "Sandbox broker flow test karna.", "Sandbox-only environment."),
    ("OpenAlgo", "Execution infrastructure.", "Strategy ka owner nahi; approved order receive karta hai."),
    ("Live Trading", "Controlled live execution.", "Explicit live mode + kill switch clear + human confirmation required."),
]
for name, job, boundary in roles:
    with st.expander(name):
        st.write(f"**Kaam:** {job}")
        st.write(f"**Boundary:** {boundary}")

st.divider()
ui.banner(
    "STRATEGY FIRST → BACKTEST → AUTO TEST → REALITY CHECK → PAPER/SANDBOX → SAFETY GATE → OPENALGO → BROKER",
    tone="success",
)

st.markdown("## 🚀 Start here")
st.page_link("pages/10_Strategy_Builder.py", label="Open Strategy Builder", icon="🧠")
st.page_link("pages/5_Backtest.py", label="Open Backtest", icon="📊")
st.page_link("pages/13_Auto_Tester.py", label="Open Auto Tester", icon="🧪")
st.page_link("pages/6_Reality_check.py", label="Open Reality Check", icon="🛡️")
st.page_link("pages/16_Paper_Trading.py", label="Open Paper Trading", icon="📝")
st.page_link("pages/14_Upstox_Sandbox.py", label="Open Upstox Sandbox", icon="🧰")
st.page_link("pages/11_Live_Trading.py", label="Open Live Trading", icon="⚡")

ui.footer_note()
