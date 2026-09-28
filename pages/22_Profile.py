"""TradeALGO profile: identity, preferences, progress and research stats."""
import streamlit as st
from algobot import ui

ui.setup("Profile", "👤")
ui.header(
    "My Profile",
    "Your TradeALGO identity, research preferences and progress — all stored for this session.",
    mode="research:Profile",
)

# Session-backed profile fields keep this page private to the current app session.
defaults = {
    "profile_name": "Himanshu",
    "profile_username": "@himanshu",
    "profile_bio": "Building, testing and improving systematic trading ideas.",
    "profile_market": "NIFTY / Indian Markets",
    "profile_style": "Systematic / rule-based",
    "profile_experience": "Learning & building",
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)

st.markdown(
    """
<style>
.profile-hero {
    position:relative; overflow:hidden; padding:28px; border-radius:22px;
    border:1px solid #263242; background:linear-gradient(135deg,#111b28 0%,#0d141d 65%,#10251e 100%);
    margin:8px 0 18px;
}
.profile-hero:after {
    content:""; position:absolute; width:260px; height:260px; right:-100px; top:-120px;
    border:1px solid #16c78433; border-radius:50%;
    box-shadow:0 0 0 28px #16c78409,0 0 0 58px #3b82f608;
}
.profile-avatar {
    width:82px; height:82px; border-radius:22px; display:flex; align-items:center; justify-content:center;
    background:linear-gradient(135deg,#16c784,#3b82f6); color:#07100d; font-size:30px; font-weight:900;
    box-shadow:0 10px 30px #0005; margin-bottom:14px;
}
.profile-name {font-size:1.75rem;font-weight:850;margin:0 0 2px;}
.profile-handle {color:#8b98a9;font-size:.9rem;margin-bottom:10px;}
.profile-bio {color:#d7dee7;max-width:760px;line-height:1.5;}
.profile-chip {
    display:inline-block;padding:5px 10px;margin:8px 6px 0 0;border-radius:999px;
    border:1px solid #2b3849;background:#151e29;color:#aeb9c8;font-size:.75rem;font-weight:700;
}
.profile-section {
    margin:24px 0 10px;font-size:1.05rem;font-weight:800;
}
.profile-stat {
    padding:17px;border:1px solid #263242;border-radius:14px;background:#111923;
}
.profile-stat .label {color:#8b98a9;font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;}
.profile-stat .value {font-size:1.45rem;font-weight:800;margin-top:5px;}
</style>
""",
    unsafe_allow_html=True,
)

initials = "".join(part[0] for part in st.session_state.profile_name.split()[:2]).upper() or "T"

st.markdown(
    f"""
<div class="profile-hero">
  <div class="profile-avatar">{initials}</div>
  <div class="profile-name">{st.session_state.profile_name}</div>
  <div class="profile-handle">{st.session_state.profile_username}</div>
  <div class="profile-bio">{st.session_state.profile_bio}</div>
  <span class="profile-chip">📈 {st.session_state.profile_market}</span>
  <span class="profile-chip">⚙️ {st.session_state.profile_style}</span>
  <span class="profile-chip">🎯 {st.session_state.profile_experience}</span>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="profile-section">📊 Your TradeALGO activity</div>', unsafe_allow_html=True)

result = st.session_state.get("result")
trades = int(result.metrics.get("trades", 0)) if result is not None else 0
pnl = float(result.metrics.get("net_pnl", 0)) if result is not None else 0
variants = int(st.session_state.get("variants_tried", 0) or 0)
strategy_saved = bool(st.session_state.get("strategy_rules"))

a, b, c, d = st.columns(4)
for col, label, value in [
    (a, "Backtest trades", f"{trades:,}"),
    (b, "Latest P&L", ui.inr(pnl, sign=True) if pnl else "₹0"),
    (c, "Variants tested", f"{variants:,}"),
    (d, "Strategy status", "Ready" if strategy_saved else "Not set"),
]:
    with col:
        st.markdown(
            f'<div class="profile-stat"><div class="label">{label}</div><div class="value">{value}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown('<div class="profile-section">✏️ Profile settings</div>', unsafe_allow_html=True)

left, right = st.columns(2)
with left:
    st.text_input("Display name", key="profile_name")
    st.text_input("Username", key="profile_username")
    st.text_area("Bio", key="profile_bio", height=110)
with right:
    st.selectbox(
        "Primary market",
        ["NIFTY / Indian Markets", "BANKNIFTY", "Equities", "F&O", "Crypto", "Global Markets"],
        key="profile_market",
    )
    st.selectbox(
        "Trading approach",
        ["Systematic / rule-based", "Discretionary", "Quantitative", "Learning / experimental"],
        key="profile_style",
    )
    st.selectbox(
        "Experience",
        ["Learning & building", "Beginner", "Intermediate", "Advanced"],
        key="profile_experience",
    )

st.markdown('<div class="profile-section">🧭 Your research journey</div>', unsafe_allow_html=True)

steps = [
    ("01", "Build", "Create measurable trading rules.", "pages/10_Strategy_Builder.py"),
    ("02", "AI Research", "Use the AI Strategy Agent to inspect the idea.", "pages/21_AI_Strategy_Agent.py"),
    ("03", "Backtest", "Replay the strategy against historical prices.", "pages/5_Backtest.py"),
    ("04", "Reality Check", "Challenge the result before moving forward.", "pages/6_Reality_check.py"),
]
cols = st.columns(4)
for col, (num, title, desc, path) in zip(cols, steps):
    with col:
        st.markdown(
            f'<div class="ab-nav-card"><div class="icon">{num}</div><h4>{title}</h4><p>{desc}</p></div>',
            unsafe_allow_html=True,
        )
        if st.button(f"Open {title}", key=f"profile_open_{num}", width="stretch"):
            st.switch_page(path)

st.markdown('<div class="profile-section">🔐 Account & safety</div>', unsafe_allow_html=True)
st.info(
    "Profile preferences are stored in your current Streamlit session. "
    "TradeALGO's profile page does not ask for broker passwords or API secrets."
)

ui.footer_note()
