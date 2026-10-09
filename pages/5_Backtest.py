"""Backtest: see how a trading idea would have done on past prices, with pretend money."""
import glob
from html import escape
import io
import os

import pandas as pd
import streamlit as st
import yaml

from algobot import ui

# Resilient import from ai_provider with auto-reload for hot deployment
try:
    from algobot.ai_provider import (
        ProviderError,
        _find_gemini_key,
        _find_groq_key,
        _find_grok_key,
        find_gemini_key,
        find_groq_key,
        find_grok_key,
        get_ai_status,
        read_strategy_image,
    )
except ImportError:
    import importlib
    import sys
    if "algobot.ai_provider" in sys.modules:
        importlib.reload(sys.modules["algobot.ai_provider"])
    try:
        from algobot.ai_provider import (
            ProviderError,
            _find_gemini_key,
            _find_groq_key,
            _find_grok_key,
            find_gemini_key,
            find_groq_key,
            find_grok_key,
            get_ai_status,
            read_strategy_image,
        )
    except Exception:
        class ProviderError(RuntimeError):
            pass

        def get_ai_status() -> dict:
            return {"gemini_connected": False, "groq_connected": False, "dual_active": False}

        def _find_gemini_key() -> str:
            return ""

        def _find_groq_key() -> str:
            return ""

        def _find_grok_key() -> str:
            return ""

        find_gemini_key = _find_gemini_key
        find_groq_key = _find_groq_key
        find_grok_key = _find_grok_key

        def read_strategy_image(*args, **kwargs):
            raise ProviderError("AI Provider is temporarily reloading. Please refresh the page.")
from algobot.appstate import experiments_scope, strategies_scope
from algobot.charts import candlestick, equity_drawdown
from algobot.config import ConfigError, validate_config
from algobot.data import DataError, generate_sample_data, load_csv
from algobot.explain import explain_config
from algobot.live_data import INTERVALS, MARKETS, LiveDataError, fetch_ohlc
from algobot.lookahead import run_lookahead_checks
from algobot.mirofish_qa import build_strategy_evidence
from algobot.mirofish_sim import run_mirofish
from algobot.prompt import AI_STRATEGY_PROMPT
from algobot.report import summary_text
from algobot.runner import check_strategy, run_from_dict

HMA_RULES = """\
indicators:
  - {name: hma_20, type: hma, period: 20}
entry_long:  "close > hma_20 and hma_20 > hma_20_prev"
exit_long:   "hma_20 < hma_20_prev"
entry_short: "close < hma_20 and hma_20 < hma_20_prev"
exit_short:  "hma_20 > hma_20_prev"
"""

FLOW_RULES = """\
indicators:
  - {name: flow, type: mfi, period: 14}
entry_long:  "flow > 55 and flow > flow_prev"
exit_long:   "flow < 50"
entry_short: "flow < 45 and flow < flow_prev"
exit_short:  "flow > 50"
"""

CONSERVATIVE_10K_RULES = """\
indicators:
  - {name: rsi5, type: rsi, period: 5}
  - {name: e20,  type: ema, period: 20}
  - {name: e50,  type: ema, period: 50}
entry_long:  "rsi5 < 25 and close > open and close > e50"
exit_long:   "rsi5 > 65"
entry_short: "rsi5 > 75 and close < open and close < e50"
exit_short:  "rsi5 < 35"
"""

STOCK_PULLBACK_RULES = """\
indicators:
  - {name: rsi5, type: rsi, period: 5}
  - {name: e20,  type: ema, period: 20}
  - {name: e50,  type: ema, period: 50}
entry_long:  "rsi5 < 25 and close > open and close > e50"
exit_long:   "rsi5 > 60"
entry_short: "rsi5 > 75 and close < open and close < e50"
exit_short:  "rsi5 < 40"
"""

NIFTY_PIVOT_RULES = """\
indicators:
  - {name: piv,  type: pivot}
  - {name: s1,   type: pivot_s1}
  - {name: r1,   type: pivot_r1}
  - {name: rsi5, type: rsi, period: 5}
entry_long:  "close > s1 and close_prev <= s1_prev and rsi5 < 35"
exit_long:   "close >= piv or rsi5 > 65"
entry_short: "close < r1 and close_prev >= r1_prev and rsi5 > 65"
exit_short:  "close <= piv or rsi5 < 35"
"""
PIVOT_RULES = NIFTY_PIVOT_RULES

BANKNIFTY_MOM_RULES = """\
indicators:
  - {name: e9,    type: ema, period: 9}
  - {name: e21,   type: ema, period: 21}
  - {name: rsi14, type: rsi, period: 14}
entry_long:  "e9 > e21 and e9_prev <= e21_prev and rsi14 > 50 and rsi14 < 70"
exit_long:   "e9 < e21 or rsi14 > 75"
entry_short: "e9 < e21 and e9_prev >= e21_prev and rsi14 < 50 and rsi14 > 30"
exit_short:  "e9 > e21 or rsi14 < 25"
"""

# Kept as the "Write my own rules" starting template -- not a ready-made choice
# of its own, just a familiar, simple starting point to edit from.
DEFAULT_RULES = HMA_RULES

# Strategy choices (label -> one-line plain description)
K_HMA = "HMA trend rule (ready-made)"
K_10K = "Conservative 10k Pullback (₹10,000 Capital — Tested)"
K_PULLBACK = "Stock Pullback (Bluechip Mean Reversion — Tested)"
K_PIVOT = "Nifty Pivot Bounce (Floor S1/R1 Reversal — Tested)"
K_MOM = "Bank Nifty Momentum (Fast/Slow Trend + RSI — Tested)"
K_FLOW = "Order flow / volume pressure (ready-made)"
K_SMA = "Moving-average crossover (ready-made)"
K_NEW = "New Era Strategy 1.0"
K_OWN = "Write my own rules (advanced)"

# Dedicated modes for external/custom sources
K_YAML = "📁 Load from configs/ YAML (conservative_10k.yaml, etc.)"
K_VISION = "📸 AI Photo-to-Strategy (Upload strategy photo / screenshot)"

PRESET_STRATEGIES = [
    K_HMA,
    K_10K,
    K_PULLBACK,
    K_PIVOT,
    K_MOM,
    K_FLOW,
    K_SMA,
    K_NEW,
    K_OWN,
]

MODE_PRESET = "🎯 Tested & Ready-Made Strategies"
MODE_VISION = "📸 AI Photo-to-Strategy (Upload Image)"
MODE_YAML = "📁 Load from configs/ YAML"
STRATEGY_MODES = [MODE_PRESET, MODE_VISION, MODE_YAML]

KIND_HELP = {
    K_HMA: "Buys when price is above a Hull Moving Average (HMA) that is itself still rising. Sells when the HMA "
           "turns down. The HMA hugs price more closely than a plain moving average, so it reacts sooner.",
    K_10K: "Regime-filtered pullback calibrated specifically for ₹10,000 capital. "
           "Dip-buy when RSI(5) dips < 25 above 50 EMA; limits daily loss to ₹300 (configs/conservative_10k.yaml).",
    K_PULLBACK: "High-win-rate intraday mean reversion for bluechips (Reliance, HDFC Bank, ICICI Bank). "
                "Buys when RSI(5) dips below 25 while above 50 EMA; exits when RSI reaches 60.",
    K_PIVOT: "Floor pivot reversal for Nifty 50 index. Buys when price bounces off S1 with oversold RSI; exits at central pivot.",
    K_MOM: "9/21 EMA trend following with RSI(14) momentum filter for Bank Nifty intraday swings.",
    K_FLOW: "Buys when the Money Flow Index — price combined with volume, as a proxy for buying/selling pressure — "
            "is above 55 and still rising. Sells when it drops back under 50. Note: Requires volume data (use with stocks, not index spot tickers).",
    K_SMA: "Buys when the short-term average price crosses above the long-term one, sells when it crosses back. "
           "The simplest classic.",
    K_NEW: "The New Era Strategy 1.0 rules, translated for this backtester.",
    K_OWN: "Type exact buy/sell conditions yourself, or paste ones an AI wrote. "
           "You will be asked to confirm them before running.",
    K_YAML: "Load any strategy YAML configuration file directly from the repository configs/ directory.",
    K_VISION: "Upload a photo, screenshot, or handwritten notes of a strategy. Multimodal AI reads it and extracts backtest rules.",
}

# Price data choices
SRC_SAMPLE = "Practice data (made-up prices, just to try the page)"
SRC_REAL = "Real market history (Nifty, Bank Nifty, ...)"
SRC_CSV = "My own price file (CSV)"

ui.setup("Backtest", "📊")
ui.header("Backtest", "See how a trading idea would have done on old prices, using pretend money. "
          "Nothing here can lose you real money.", mode="backtest:Backtest · past prices")

st.markdown(
    "**Three steps:** &nbsp; **1.** Pick an idea &nbsp;→&nbsp; **2.** Pick the prices &nbsp;→&nbsp; "
    "**3.** Press **Run backtest**."
)
with st.expander("Words explained (tap if any word on this page is unclear)"):
    st.markdown(
        "- **Backtest**: replaying a trading idea on prices that already happened, to see what it *would* have done.\n"
        "- **Stop-loss**: automatic exit when a trade loses a set percent, so one trade can't hurt too much.\n"
        "- **Profit target**: automatic exit when a trade gains a set percent.\n"
        "- **Short selling**: selling first, hoping the price falls, then buying back cheaper.\n"
        "- **Biggest fall (drawdown)**: the largest drop of the account from its highest point. "
        "Ask yourself: could I sit through this?\n"
        "- **Profit factor**: total money won ÷ total money lost. Above 1 means winners beat losers.\n"
        "- **Slippage**: the small gap between the price you wanted and the price you actually got.\n"
        "- **STT, GST, SEBI fee, stamp duty**: government taxes and fees added to every trade.\n"
        "- **Peek-ahead (look-ahead)**: a rule that accidentally uses future prices makes a test look far better than "
        "real life. The optional safety check catches this.\n"
        "- **HMA (Hull Moving Average)**: like a regular moving average line, but it hugs the price more closely and "
        "reacts sooner — at the cost of wobbling more on sharp reversals.\n"
        "- **Order flow / Money Flow Index**: an estimate of buying vs. selling pressure from price and volume "
        "together. Not the same as real order flow (which reads actual buy/sell orders tick by tick) — this engine "
        "only has candle data, so it's the closest proxy available here."
    )


@st.cache_data(show_spinner=False)
def sample_data(days: int):
    return generate_sample_data(days=days, seed=42)


def none_if_zero(value):
    return None if value in (0, 0.0) else value


def colour_pnl(value):
    if isinstance(value, (int, float)) and value == value:
        return "color: #16C784" if value > 0 else ("color: #EA3943" if value < 0 else "")
    return ""


# ------------------------------------------------------------ step 1: the idea
st.markdown("### Step 1 · Pick a trading idea")

# Sync session state if set externally
if "strategy_mode" not in st.session_state:
    if st.session_state.get("strategy_kind") == K_VISION:
        st.session_state["strategy_mode"] = MODE_VISION
    elif st.session_state.get("strategy_kind") == K_YAML:
        st.session_state["strategy_mode"] = MODE_YAML
    else:
        st.session_state["strategy_mode"] = MODE_PRESET

strategy_mode = st.radio(
    "Strategy Source",
    STRATEGY_MODES,
    horizontal=True,
    key="strategy_mode",
    help="Select whether to test curated algorithms, upload a strategy screenshot with AI, or load a repository YAML config."
)

if strategy_mode == MODE_PRESET:
    kind = st.radio(
        "Which idea do you want to test?",
        PRESET_STRATEGIES,
        captions=[KIND_HELP[k] for k in PRESET_STRATEGIES],
        key="strategy_kind"
    )
elif strategy_mode == MODE_VISION:
    kind = K_VISION
    st.session_state["strategy_kind"] = K_VISION
elif strategy_mode == MODE_YAML:
    kind = K_YAML
    st.session_state["strategy_kind"] = K_YAML
else:
    kind = K_HMA

own_rules = kind in (K_OWN, K_VISION)
yaml_loaded_cfg = {}

# Auto-adjust sensible defaults if strategy preset changed
if st.session_state.get("_bt_prev_kind") != kind:
    st.session_state["_bt_prev_kind"] = kind
    if kind == K_10K:
        st.session_state["capital"] = 10000
        st.session_state["quantity"] = 25
        st.session_state["stop_pct"] = 0.25
        st.session_state["target_pct"] = 0.60
        st.session_state["max_loss"] = 300
        st.session_state["max_trades"] = 1

if kind == K_10K:
    strategy_name = "rules"
    st.markdown("""
    <div class="ta-preset-callout">
        <span class="ta-callout-pill">₹10,000 CAPITAL</span>
        <span class="ta-callout-text">Calibrated specifically for ₹10,000 capital: limits maximum daily loss to ₹300 (3%) and uses a regime-filtered pullback setup.</span>
    </div>
    """, unsafe_allow_html=True)
    with st.expander("See the exact rules behind this idea", expanded=True):
        st.code(CONSERVATIVE_10K_RULES, language="yaml")
elif kind == K_YAML:
    strategy_name = "rules"
    st.markdown("""
    <div class="ta-vision-header-card">
        <div class="ta-vision-badge">📁 REPOSITORY CONFIGURATIONS</div>
        <div class="ta-vision-title">Load Strategy Configuration File</div>
        <div class="ta-vision-desc">Select any audited or pre-configured strategy YAML file directly from the repository's <code>configs/</code> directory.</div>
    </div>
    """, unsafe_allow_html=True)

    cfg_files = sorted(glob.glob("configs/*.yaml"))
    def_idx = 0
    for idx, cpath in enumerate(cfg_files):
        if "conservative_10k.yaml" in cpath.replace("\\", "/"):
            def_idx = idx
            break
    
    col_sel, col_meta = st.columns([1.2, 0.8])
    with col_sel:
        selected_yaml = st.selectbox("Pick a strategy YAML from configs/", cfg_files, index=def_idx, key="bt_yaml_select")
    
    if selected_yaml and os.path.exists(selected_yaml):
        with open(selected_yaml, "r", encoding="utf-8") as yf:
            yaml_raw_text = yf.read()
        try:
            yaml_loaded_cfg = yaml.safe_load(yaml_raw_text) or {}
            cap = yaml_loaded_cfg.get("capital", 10000)
            max_l = yaml_loaded_cfg.get("risk", {}).get("max_daily_loss", 300)
            with col_meta:
                st.caption(f"📄 **{os.path.basename(selected_yaml)}** loaded · Starting Pretend Capital: **₹{cap:,}** · Max Loss: **₹{max_l:,}**")
        except Exception as exc:
            st.error(f"Could not parse YAML: {exc}")
        
        with st.expander(f"View content of {os.path.basename(selected_yaml)}", expanded=True):
            st.code(yaml_raw_text, language="yaml")
elif kind == K_VISION:
    strategy_name = "rules"
    st.markdown("""
    <div class="ta-vision-header-card">
        <div class="ta-vision-badge">📸 MULTIMODAL AI VISION</div>
        <div class="ta-vision-title">Upload Strategy Photo or Screenshot</div>
        <div class="ta-vision-desc">Upload a TradingView chart screenshot, Pine script screenshot, or photo of handwritten strategy rules. TradeALGO's multimodal AI reads indicators, triggers, and SL/target levels to extract backtest rules automatically.</div>
    </div>
    """, unsafe_allow_html=True)

    col_up, col_prov = st.columns([1.1, 0.9])
    with col_up:
        photo_file = st.file_uploader("Upload strategy image (PNG, JPG, WEBP)", type=["png", "jpg", "jpeg", "webp"], key="bt_photo_file")
        if photo_file:
            st.image(photo_file, caption="📷 Uploaded Strategy Snapshot", use_container_width=True)
        else:
            st.info("💡 **Supported**: TradingView screenshots, indicator charts, Pine script code snapshots, or clear mobile photos of strategy notes.")

    with col_prov:
        with st.container():
            engine_options = [
                "Google Gemini 2.5 Flash (Recommended)",
                "Google Gemini 2.0 Flash",
                "Google Gemini 1.5 Flash",
                "Groq (Llama 3.2 11B Vision)",
                "xAI Grok Vision",
                "OpenAI (GPT-4o)",
            ]
            selected_engine = st.selectbox("AI Vision Engine", engine_options, key="bt_selected_engine")

            if "gemini 2.5" in selected_engine.lower():
                prov_name, prov_model = "gemini", "gemini-2.5-flash"
            elif "gemini 2.0" in selected_engine.lower():
                prov_name, prov_model = "gemini", "gemini-2.0-flash"
            elif "gemini 1.5" in selected_engine.lower():
                prov_name, prov_model = "gemini", "gemini-1.5-flash"
            elif "groq" in selected_engine.lower():
                prov_name, prov_model = "groq", "llama-3.2-11b-vision-preview"
            elif "grok" in selected_engine.lower():
                prov_name, prov_model = "grok", "grok-4.5"
            elif "openai" in selected_engine.lower():
                prov_name, prov_model = "openai", "gpt-4o"
            else:
                prov_name, prov_model = "gemini", "gemini-2.5-flash"

            pasted_key_input = st.text_input(
                "🔑 Paste API Key (or auto-detect from secret.yml / secrets)",
                value=st.session_state.get("custom_ai_key", ""),
                type="password",
                placeholder="AIzaSy... (Gemini) or gsk_... (Groq)",
                key="bt_direct_ai_key_input",
                help="Paste your API key here directly if secret.yml is not detected.",
            )
            if pasted_key_input != st.session_state.get("custom_ai_key", ""):
                st.session_state["custom_ai_key"] = pasted_key_input.strip()

            active_key = (st.session_state.get("custom_ai_key") or "").strip()
            if not active_key:
                if prov_name == "gemini" and callable(globals().get("_find_gemini_key")):
                    active_key = _find_gemini_key()
                elif prov_name == "groq" and callable(globals().get("_find_groq_key")):
                    active_key = _find_groq_key()
                elif prov_name == "grok" and callable(globals().get("_find_grok_key")):
                    active_key = _find_grok_key()

            if active_key:
                badge_title = f"{prov_name.upper()} ACTIVE · {prov_model.upper()}"
                src_label = "Pasted in box above" if (st.session_state.get("custom_ai_key") or "").strip() else "Auto-detected from secrets / secret.yml"
                badge_desc = f"Key ready ({src_label}). Ready to analyze charts, screenshots & handwritten strategies."
                badge_color = "#20D9A0"
                badge_bg = "rgba(32, 217, 160, 0.08)"
                badge_border = "rgba(32, 217, 160, 0.28)"
            else:
                badge_title = f"WAITING FOR {prov_name.upper()} KEY"
                badge_desc = f"Paste your {prov_name.capitalize()} key in the box above or add to <code>secret.yml</code> / Streamlit Secrets."
                badge_color = "#F59E0B"
                badge_bg = "rgba(245, 158, 11, 0.08)"
                badge_border = "rgba(245, 158, 11, 0.28)"

            st.markdown(f"""
            <div style="padding: 14px 16px; background: {badge_bg}; border: 1px solid {badge_border}; border-radius: 12px; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: {badge_color}; box-shadow: 0 0 8px {badge_color};"></span>
                    <span style="font-weight: 800; color: {badge_color}; font-size: 0.88rem; letter-spacing: 0.02em;">{badge_title}</span>
                </div>
                <div style="color: #94A3B8; font-size: 0.82rem; margin-top: 6px; line-height: 1.5;">
                    {badge_desc}
                </div>
            </div>
            """, unsafe_allow_html=True)

            extract_btn = st.button("⚡ Read Photo & Extract Strategy", type="primary", key="bt_v_btn", disabled=photo_file is None, use_container_width=True)
            if photo_file and extract_btn:
                with st.spinner(f"Analyzing image and extracting strict TradeALGO rules with {selected_engine}..."):
                    try:
                        mime = photo_file.type or "image/png"
                        res = read_strategy_image(
                            photo_file.getvalue(),
                            mime_type=mime,
                            custom_key=active_key,
                            provider_name=prov_name,
                            model=prov_model,
                        )
                        st.session_state["vision_rules_text"] = res["yaml"]
                        st.session_state["vision_explanation"] = res["explanation"]
                        st.success(f"✅ Strategy extracted successfully with {selected_engine}!")
                    except Exception as exc:
                        st.error(f"Vision extraction error: {exc}")

    if st.session_state.get("vision_explanation"):
        st.markdown(f"""
        <div class="ta-vision-result-card">
            <div class="ta-vision-result-badge">✨ AI DETECTED STRATEGY</div>
            <div class="ta-vision-result-text">{escape(st.session_state['vision_explanation'])}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("##### 📝 Extracted Strategy Rules (YAML)")
    st.caption("Verify or fine-tune what the AI extracted before executing your test:")
    vision_rules_text = st.text_area("Your rules (edit, or verify what the AI extracted)",
                                     st.session_state.get("vision_rules_text", DEFAULT_RULES),
                                     height=230, key="vision_rules_text", label_visibility="collapsed")
elif kind == K_OWN:
    strategy_name = "rules"
    rules_text = st.text_area("Your rules (edit, or paste what an AI wrote)", DEFAULT_RULES, height=230,
                              key="rules_text")
    with st.expander("Want an AI to write the rules for you? Copy this prompt into any AI chat"):
        st.code(AI_STRATEGY_PROMPT, language="text")
        st.caption("Paste the yaml block it gives you into the box above. Never paste broker keys or passwords into an "
                   "AI chat. The plain-English summary below is produced by this program, not by the AI: use it to "
                   "check the AI understood you.")
elif kind == K_NEW:
    strategy_name = "new_era_1_0"
    c1, c2 = st.columns(2)
    new_era_sl = c1.number_input("Largest stop-loss (%) · 0 = off", min_value=0.0, value=0.0, step=0.1, key="new_era_sl")
    new_era_ratio = c2.number_input("Target ratio (profit target ÷ risk)", min_value=0.0, value=2.0, step=0.5,
                                    key="new_era_ratio")
    with st.expander("Technical note for the developer"):
        st.markdown(
            "This is the supplied New Era Strategy 1.0 translated into the deterministic backtest engine. It uses the "
            "formation state, RSI/CCI/EMA/HMA conditions, next-bar entry, and signal-bar-derived SL/target.\n\n"
            "**Source-parity note:** the supplied Pine script explicitly calls Day Close only while position_size > 0, "
            "whereas TradeALGO's conservative backtest engine squares off both long and short positions at the "
            "configured square-off time."
        )
elif kind == K_SMA:
    strategy_name = "sma_crossover"
    c1, c2 = st.columns(2)
    fast = c1.number_input("Short average (candles)", min_value=1, value=10, step=1, key="sma_fast",
                           help="The quick-moving average. Smaller number = reacts faster.")
    slow = c2.number_input("Long average (candles)", min_value=2, value=30, step=1, key="sma_slow",
                           help="The slow-moving average. It must be bigger than the short one.")
elif kind == K_FLOW:
    strategy_name = "rules"
    with st.expander("See the exact rules behind this idea"):
        st.code(FLOW_RULES, language="yaml")
elif kind == K_PULLBACK:
    strategy_name = "rules"
    with st.expander("See the exact rules behind this idea"):
        st.code(STOCK_PULLBACK_RULES, language="yaml")
elif kind == K_PIVOT:
    strategy_name = "rules"
    with st.expander("See the exact rules behind this idea"):
        st.code(PIVOT_RULES, language="yaml")
elif kind == K_MOM:
    strategy_name = "rules"
    with st.expander("See the exact rules behind this idea"):
        st.code(BANKNIFTY_MOM_RULES, language="yaml")
else:
    strategy_name = "rules"
    with st.expander("See the exact rules behind this idea"):
        st.code(HMA_RULES, language="yaml")

# ------------------------------------------------------------ step 2: the prices
st.markdown("### Step 2 · Pick the prices to test on")
days, uploaded, hist_symbol, hist_interval = 60, None, None, None
source = st.radio("Where should the prices come from?", [SRC_SAMPLE, SRC_REAL, SRC_CSV], key="data_source")
if source == SRC_SAMPLE:
    st.caption("Made-up prices: every idea loses a little here after costs, on purpose. Use this only to learn how the "
               "page works, then switch to real market history to see a meaningful result.")
    days = st.slider("How many days of practice data?", 10, 120, 60, key="sample_days")
elif source == SRC_REAL:
    c1, c2 = st.columns(2)
    hist_symbol = c1.selectbox("Market", list(MARKETS), key="hist_symbol")
    hist_interval = c2.selectbox("Candle size", list(INTERVALS), index=1, key="hist_interval")
    if hist_symbol in ("Nifty 50", "Bank Nifty", "Sensex") and kind == K_FLOW:
        st.warning("⚠️ Yahoo Finance index data has 0 volume; Order flow / MFI requires volume. Select a stock like Reliance or TCS to test this rule.")
    st.caption("Needs internet. Free data from Yahoo Finance, slightly delayed. A good result on one period is still "
               "just one run: use the Reality check page next.")
else:
    uploaded = st.file_uploader("CSV with datetime, open, high, low, close (volume optional)", type=["csv"], key="csv")

# ------------------------------------------------------------ optional settings
st.markdown("### Optional · Money and safety settings")
st.caption("The defaults are sensible. You do not need to change anything to continue.")
with st.expander("Money, stop-loss and daily limits"):
    c1, c2, c3 = st.columns(3)
    def_cap = 10000 if kind == K_10K else 100000
    def_qty = 25 if kind == K_10K else 10
    capital = c1.number_input("Starting pretend money (Rs)", min_value=1000, value=def_cap, step=1000, key="capital",
                              help="The pretend account balance the backtest starts with.")
    quantity = c2.number_input("Quantity per trade", min_value=1, value=def_qty, step=1, key="quantity",
                               help="How many shares/units to buy or sell each time the rule fires.")
    allow_short = c3.checkbox("Also bet on the price falling (short selling)", value=False, key="allow_short",
                              help="Short selling means selling first, hoping the price falls. Leave this off if you "
                                   "only want to buy first and sell later.")
    c1, c2, c3 = st.columns(3)
    def_stop = 0.25 if kind == K_10K else 0.5
    def_target = 0.60 if kind == K_10K else 1.0
    def_loss = 300 if kind == K_10K else 2000
    stop_pct = c1.number_input("Stop-loss (%) · 0 = off", min_value=0.0, value=def_stop, step=0.1, key="stop_pct",
                               help="Automatically exit if the price moves against you by this percent, to cap the "
                                    "loss on one trade.")
    target_pct = c2.number_input("Profit target (%) · 0 = off", min_value=0.0, value=def_target, step=0.1, key="target_pct",
                                 help="Automatically take profit once the price moves in your favour by this percent.")
    max_loss = c3.number_input("Stop for the day after losing (Rs) · 0 = off", min_value=0, value=def_loss, step=100,
                               key="max_loss",
                               help="A daily 'enough for today' brake, so one bad day can't run away.")
    c1, c2, c3 = st.columns(3)
    def_trades = 1 if kind == K_10K else 6
    max_trades = c1.number_input("Max trades per day · 0 = no limit", min_value=0, value=def_trades, step=1, key="max_trades",
                                 help="Caps how many times the rule is allowed to trade in a single day.")
    max_position = c2.number_input("Max money in one trade (Rs) · 0 = no limit", min_value=0, value=50000, step=1000,
                                   key="max_position",
                                   help="The most the strategy can put into one trade at a time.")
    t_start = c3.text_input("Don't trade before (HH:MM)", "09:20", key="t_start",
                            help="Skip the noisy first few minutes after the market opens.")
    c1, c2 = st.columns(2)
    t_last = c1.text_input("No new trades after (HH:MM)", "14:45", key="t_last",
                           help="Stop opening brand-new trades this late in the day.")
    t_off = c2.text_input("Close all trades at (HH:MM)", "15:15", key="t_off",
                          help="Force any open position shut before the market closes for the day.")
    st.caption("Times use the 24-hour clock, for example 15:15 means 3:15 pm.")
with st.expander("Charges and brokerage (defaults match typical Indian discount brokers)"):
    st.caption("Every real trade has small, unavoidable charges. Including them keeps the result honest. If you are not "
               "sure, leave these as they are. For exact numbers, use your own broker's charge calculator.")
    c1, c2, c3 = st.columns(3)
    brokerage_pct = c1.number_input("Brokerage (% of order value)", min_value=0.0, value=0.03, step=0.01,
                                    format="%.4f", key="c_brokerage",
                                    help="What your broker charges to place an order, as a percent of the trade's value.")
    brokerage_cap = c2.number_input("Brokerage cap per order (Rs) · 0 = no cap", min_value=0.0, value=20.0, key="c_cap",
                                    help="Most discount brokers never charge more than this per order, however large "
                                         "the trade.")
    stt_sell = c3.number_input("STT on sell side (%)", min_value=0.0, value=0.025, format="%.4f", key="c_stt_sell",
                               help="Securities Transaction Tax: a fixed government tax on trades, not something your "
                                    "broker controls.")
    c1, c2, c3 = st.columns(3)
    stt_buy = c1.number_input("STT on buy side (%)", min_value=0.0, value=0.0, format="%.4f", key="c_stt_buy",
                              help="Same government tax as STT on sells, but for the buy side (usually zero for "
                                   "intraday equity).")
    exch = c2.number_input("Exchange charges (%)", min_value=0.0, value=0.003, format="%.5f", key="c_exch",
                           help="A small transaction fee the stock exchange (NSE/BSE) itself charges on every trade.")
    sebi = c3.number_input("SEBI fee (%)", min_value=0.0, value=0.0001, format="%.5f", key="c_sebi",
                           help="A tiny fee that funds the market regulator, SEBI, charged on every trade.")
    c1, c2, c3 = st.columns(3)
    stamp = c1.number_input("Stamp duty on buys (%)", min_value=0.0, value=0.003, format="%.4f", key="c_stamp",
                            help="A small state government tax charged when you buy, not when you sell.")
    gst = c2.number_input("GST (%) on brokerage and fees", min_value=0.0, value=18.0, key="c_gst",
                          help="Goods and Services Tax, charged on top of the brokerage and fees above "
                               "(18% is the standard rate).")
    slippage = c3.number_input("Slippage (bps) · 1 bps = 0.01%", min_value=0.0, value=2.0, key="c_slip",
                               help="The gap between the price you expected and the price you actually got, because "
                                    "the market moved while your order went through.")

# ------------------------------------------------------------ build + validate the config
try:
    if kind == K_OWN:
        params = yaml.safe_load(rules_text)
        if not isinstance(params, dict):
            raise ConfigError("The rules box must contain settings like entry_long: \"...\".")
    elif kind == K_VISION:
        params = yaml.safe_load(vision_rules_text)
        if not isinstance(params, dict):
            raise ConfigError("The rules box must contain settings like entry_long: \"...\".")
    elif kind == K_10K:
        params = yaml.safe_load(CONSERVATIVE_10K_RULES)
    elif kind == K_YAML:
        if isinstance(yaml_loaded_cfg.get("strategy"), dict):
            strategy_name = yaml_loaded_cfg["strategy"].get("name", "rules")
            params = yaml_loaded_cfg["strategy"].get("params", {})
        else:
            params = yaml_loaded_cfg
    elif kind == K_SMA:
        params = {"fast": int(fast), "slow": int(slow)}
    elif kind == K_NEW:
        params = {"sl_max_points_percent": float(new_era_sl), "target_ratio": float(new_era_ratio)}
    elif kind == K_FLOW:
        params = yaml.safe_load(FLOW_RULES)
    elif kind == K_PULLBACK:
        params = yaml.safe_load(STOCK_PULLBACK_RULES)
    elif kind == K_PIVOT:
        params = yaml.safe_load(NIFTY_PIVOT_RULES)
    elif kind == K_MOM:
        params = yaml.safe_load(BANKNIFTY_MOM_RULES)
    else:
        params = yaml.safe_load(HMA_RULES)
    raw = {
        "name": "dashboard_run", "capital": capital,
        "strategy": {"name": strategy_name, "params": params, "quantity": int(quantity), "allow_short": allow_short,
                     "stop_loss_pct": none_if_zero(stop_pct), "target_pct": none_if_zero(target_pct)},
        "risk": {"max_daily_loss": none_if_zero(max_loss), "max_trades_per_day": none_if_zero(int(max_trades)),
                 "max_position_value": none_if_zero(max_position), "trading_start": t_start.strip(),
                 "no_new_entries_after": t_last.strip(), "square_off_time": t_off.strip()},
        "costs": {"brokerage_pct": brokerage_pct, "brokerage_cap": none_if_zero(brokerage_cap), "stt_buy_pct": stt_buy,
                  "stt_sell_pct": stt_sell, "exchange_txn_pct": exch, "sebi_fee_pct": sebi, "stamp_buy_pct": stamp,
                  "gst_pct": gst, "slippage_bps": slippage},
    }
    saved_cfg = st.session_state.pop("saved_backtest_cfg", None) or st.session_state.pop("last_raw", None)
    if saved_cfg:
        raw = saved_cfg
    cfg = validate_config(raw)
    check_strategy(cfg)
except (ConfigError, yaml.YAMLError) as exc:
    st.error(f"Please fix this first: {exc}")
    st.stop()


# Plain-English readback. Ready-made ideas just show it tucked away; your own rules must be confirmed.
with st.expander("What exactly will be tested? (in plain English)", expanded=own_rules):
    st.text(explain_config(cfg))
if own_rules:
    confirmed = st.checkbox("Yes, this is exactly what I meant", key="confirm")
else:
    confirmed = True


def load_prices():
    if source == SRC_SAMPLE:
        return sample_data(days)
    if source == SRC_REAL:
        ticker = MARKETS[hist_symbol]
        yf_interval, yf_period = INTERVALS[hist_interval]
        return fetch_ohlc(ticker, yf_interval, yf_period)
    if uploaded is None:
        st.info("Upload a CSV file in Step 2, or switch to practice data or real market history.")
        return None
    return load_csv(io.BytesIO(uploaded.getvalue()))


# ------------------------------------------------------------ step 3: run
st.markdown("### Step 3 · Run it")
run_clicked = st.button("▶  Run backtest", type="primary", key="btn_run", disabled=not confirmed, width="stretch")
if not confirmed:
    st.caption("Tick \"Yes, this is exactly what I meant\" above to enable the button.")
with st.expander("Extra safety check (optional): make sure the rule isn't secretly peeking at future prices"):
    st.caption("A rule that accidentally uses tomorrow's prices makes a test look far better than real life. "
               "This check proves your rule only uses information available at the time.")
    check_clicked = st.button("Run the peek-ahead check", key="btn_lookahead", disabled=not confirmed)

prices = st.session_state.get("last_prices")

if check_clicked or run_clicked:
    try:
        prices = load_prices()
    except (DataError, LiveDataError) as exc:
        st.error(f"Problem with the price data: {exc}")
        prices = None
    if prices is not None and check_clicked:
        try:
            st.session_state["lookahead"] = run_lookahead_checks(cfg, prices)
        except ConfigError as exc:
            st.error(f"The check could not run: {exc}")
    if prices is not None and run_clicked:
        try:
            st.session_state["result"] = run_from_dict(raw, prices)
            st.session_state["result_yaml"] = yaml.safe_dump(raw, sort_keys=False)
            st.session_state["used_sample"] = source == SRC_SAMPLE
            st.session_state["last_raw"] = raw            # used by the Reality check and Test lab pages
            st.session_state["last_prices"] = prices
            with experiments_scope() as log:
                log.record(prices, cfg, st.session_state["result"])
                st.session_state["variants_tried"] = log.count_trials(prices)
        except (ConfigError, DataError) as exc:
            st.error(f"The backtest could not run: {exc}")

checks = st.session_state.get("lookahead")
if checks:
    st.subheader("Peek-ahead check")
    st.caption("Proves the rules cannot secretly use information from the future, the classic reason a backtest looks "
               "better than reality.")
    for c in checks:
        (st.success if c.passed else st.error)(f"{c.name}: {c.detail}")

# ------------------------------------------------------------ results
result = st.session_state.get("result")
if result is not None:
    st.subheader("Results")
    if st.session_state.get("used_sample"):
        st.warning("This used random sample data (made-up prices). The numbers say nothing about the real market. "
                   "Switch Step 2 to real market history for a meaningful result.")
    m = result.metrics
    st.divider()
    st.markdown("### Save this backtest")
    st.caption("Save the exact strategy configuration together with its backtest metrics so you can reuse it later.")
    save_name = st.text_input("Saved strategy name", value=str(cfg.get("name", "Backtest strategy")), key="save_backtest_name")
    if st.button("💾 Save strategy + results", key="save_backtest_result", disabled=not save_name.strip()):
        with strategies_scope() as library:
            saved_id = library.save(
                save_name,
                cfg,
                result=result,
                market=hist_symbol or ("Practice" if source == SRC_SAMPLE else "CSV"),
                timeframe=hist_interval or "custom",
            )
            st.session_state["selected_saved_strategy"] = saved_id
            count = library.count()
            st.success(f"Saved **{save_name.strip()}**. You now have {count} saved strateg{'y' if count == 1 else 'ies'}.")
    blocked_big = result.rejections.get("position_too_large", 0)
    prices_check = prices if prices is not None else st.session_state.get("last_prices")
    has_zero_volume = (
        isinstance(prices_check, pd.DataFrame)
        and "volume" in prices_check.columns
        and float(prices_check["volume"].sum()) == 0.0
    )
    uses_volume = kind == K_FLOW or any(
        isinstance(i, dict) and i.get("type") in ("mfi", "vwap")
        for i in (cfg.get("strategy", {}).get("params", {}).get("indicators") or [])
    )
    if m["trades"] == 0 and blocked_big:
        st.warning(f"The idea found {blocked_big} chances to trade, but every one was blocked because a single trade "
                   f"would be bigger than your limit of {ui.inr(max_position)}. Prices on this data are high (an index "
                   "like Nifty is worth lakhs per 10 units). Fix: open **Money, stop-loss and daily limits** above and "
                   "either lower **Quantity per trade** (try 1 or 2) or raise **Max money in one trade** "
                   "(or set it to 0 for no limit), then run again.")
        if st.button("⚡ One-click fix: Set Quantity=1 & Max Position=0 (no limit)", key="btn_fix_pos_limit"):
            st.session_state["quantity"] = 1
            st.session_state["max_position"] = 0
            st.rerun()
    elif m["trades"] == 0 and has_zero_volume and uses_volume:
        st.warning("⚠️ This strategy requires volume (e.g. MFI or VWAP), but free Yahoo Finance index feeds (^NSEI, ^NSEBANK) "
                   "do not report volume (volume is 0). To test this idea, switch Step 2 Market to a liquid stock like Reliance, TCS, or Infosys.")
    elif m["trades"] == 0:
        st.info("The rule never triggered on this data, so there is nothing to judge yet. "
                "Try a longer period or a different idea.")
    elif m["net_pnl"] > 0:
        st.success(f"On this data, the idea would have made {ui.inr(m['net_pnl'])} across {m['trades']} trades. "
                   "That is on old prices with pretend money, not a promise about the future. "
                   "Next: try to break it on the Reality check page.")
    else:
        st.warning(f"On this data, the idea would have lost {ui.inr(abs(m['net_pnl']))} across {m['trades']} trades. "
                   "Try a different idea or different settings.")

    a, b, c, d = st.columns(4)
    a.metric("Net profit / loss (Rs)", f"{m['net_pnl']:,.0f}", f"{m['return_pct']:+.2f}%",
             help="What you would have made or lost after all charges. The small number under it is the return on "
                  "your starting money.")
    b.metric("Trades", m["trades"], help="How many trades the idea took.")
    c.metric("Winning trades", "n/a" if m["win_rate_pct"] is None else f"{m['win_rate_pct']:.0f}%",
             help="Out of all trades, how many made money. A high number alone doesn't mean profit: winners can be "
                  "small and losers big.")
    d.metric("Biggest fall (Rs)", f"{m['max_drawdown']:,.0f}",
             help="The largest drop of your account from its highest point. Ask yourself: could I sit through this?")

    with st.expander("More numbers (for the curious)"):
        e, f, g, h = st.columns(4)
        e.metric("Return", f"{m['return_pct']:.2f}%", help="Profit or loss as a percent of the starting money.")
        f.metric("Before costs (Rs)", f"{m['gross_pnl']:,.0f}", help="Result before brokerage, taxes and slippage.")
        g.metric("Costs paid (Rs)", f"{m['total_costs']:,.0f}",
                 help="Brokerage, taxes and slippage added up. Many ideas look good until costs are counted.")
        pf = m["profit_factor"]
        h.metric("Profit factor", "n/a" if pf is None else ("infinite" if pf == float("inf") else f"{pf:.2f}"),
                 help="Total won ÷ total lost. Above 1 means winners beat losers.")
        i, j, k, l = st.columns(4)
        i.metric("Average win (Rs)", "n/a" if m["avg_win"] is None else f"{m['avg_win']:,.0f}")
        j.metric("Average loss (Rs)", "n/a" if m["avg_loss"] is None else f"{m['avg_loss']:,.0f}")
        k.metric("Longest winning run", m["max_win_streak"], help="Most wins in a row.")
        l.metric("Longest losing run", m["max_loss_streak"], help="Most losses in a row.")
        st.caption(f"Time in market: {m['exposure_pct']:.1f}% of the tested period had an open trade "
                   "(the rest was spent waiting for a signal).")
    tried = st.session_state.get("variants_tried")
    if tried:
        st.caption(f"Variants tried on this data so far: {tried}. The more you try, the more a good-looking result can "
                   "be luck. Open the Reality check page before believing any result.")

    tab_price, tab_equity, tab_trades, tab_notes = st.tabs(["Chart", "Account balance", "Trade list", "Details"])
    with tab_price:
        prices_now = prices if prices is not None else st.session_state.get("last_prices")
        if prices_now is not None:
            window = st.slider("Candles shown (latest)", 100, 1000, 300, step=50, key="bt_window")
            ui.show_chart(candlestick(prices_now, trades=result.trades, height=360, max_bars=int(window)))
            st.caption("Blue triangle: entry (up = bought first, down = sold first). Green cross: winning exit. "
                       "Red cross: losing exit.")
    with tab_equity:
        st.caption("Top: how your pretend account balance moved over time. Bottom: how far it sat below its best "
                   "level. A deep dip means you would need strong nerves to hold on.")
        ui.show_chart(equity_drawdown(result.equity))
    with tab_trades:
        if len(result.trades):
            blotter = result.trades.copy()
            blotter["entry_time"] = pd.to_datetime(blotter["entry_time"]).dt.strftime("%d %b %H:%M")
            blotter["exit_time"] = pd.to_datetime(blotter["exit_time"]).dt.strftime("%d %b %H:%M")
            blotter = blotter.rename(columns={
                "entry_time": "Entered", "exit_time": "Exited", "side": "Type", "qty": "Qty",
                "entry_price": "Entry price", "exit_price": "Exit price", "gross_pnl": "Profit before costs",
                "costs": "Costs", "net_pnl": "Profit / loss", "exit_reason": "Why it exited"})
            money = ["Profit before costs", "Costs", "Profit / loss"]
            styler = blotter.style.format({c: "{:,.2f}" for c in money})
            colour_cols = ["Profit / loss", "Profit before costs"]
            styler = styler.map(colour_pnl, subset=colour_cols) if hasattr(styler, "map") else styler.applymap(colour_pnl, subset=colour_cols)
            ui.show_table(styler, hide_index=True)
        else:
            st.info("No trades were taken.")
        st.download_button("Download trades (CSV)", result.trades.to_csv(index=False), "trades.csv", "text/csv",
                           key="dl_trades")
        st.download_button("Download these settings (YAML)", st.session_state["result_yaml"], "my_strategy.yaml",
                           "text/yaml", key="dl_settings")
    with tab_notes:
        if result.events or result.rejections:
            st.markdown("**Safety rules that stepped in**")
            for ev in result.events:
                st.write(ev)
            for reason, count in result.rejections.items():
                st.write(f"Entries blocked ({reason}): {count}")
        st.text(summary_text(result))

    # ------------------------------------------------------------ MiroFish Swarm Audit
    st.divider()
    st.markdown("### 🐟 MiroFish Agent Swarm · Strategy Audit Jobs")
    st.caption(
        "Put your strategy in front of an adversarial cohort of synthetic agents acting as different work jobs "
        "(Risk Manager, Adversarial Attacker, Optimizer, Momentum, Contrarian, Beginner). "
        "The swarm stress-tests your strategy across 6 independent market regimes (trend, chop, mean reversion, volatile, shocks, noise)."
    )
    col_mf1, col_mf2 = st.columns([2, 1])
    mf_rounds = col_mf1.slider("Stress test rounds across regimes", 6, 24, 12, key="bt_mf_rounds")
    mf_btn = col_mf2.button("🐟 Run MiroFish Agent Swarm Check", key="btn_run_mirofish_check", type="primary")

    if mf_btn:
        with st.spinner("MiroFish agents are running adversarial checks across market regimes..."):
            try:
                ev_report = build_strategy_evidence(cfg, rounds=mf_rounds, days=8, seed=9001)
                strat_score = min(1.0, max(0.0, ev_report.profitable_rate / 100.0))
                risk_score = 0.8 if ev_report.worst_drawdown < cfg.get("capital", 10000) * 0.1 else 0.4
                sim_rep, cohort, msgs, graph, events = run_mirofish(
                    agents=8, ticks=24, seed=700, strategy_score=strat_score, risk_score=risk_score
                )
                st.session_state["bt_mf_audit"] = {
                    "evidence": ev_report,
                    "sim": sim_rep,
                    "cohort": cohort,
                    "msgs": msgs,
                }
                st.success("MiroFish Agent Swarm Audit Completed!")
            except Exception as exc:
                st.error(f"MiroFish audit failed: {exc}")

    audit = st.session_state.get("bt_mf_audit")
    if audit:
        ev = audit["evidence"]
        sim = audit["sim"]
        cohort = audit["cohort"]

        v_col, c_col, pf_col, dd_col = st.columns(4)
        v_col.metric("Adversarial Verdict", ev.verdict)
        c_col.metric("Swarm Consensus", f"{sim.consensus:+.2f}", f"Strength {sim.consensus_strength:.2f}")
        pf_col.metric("Mean Profit Factor", f"{ev.mean_profit_factor:.2f}", f"{ev.profitable_rate:.0f}% profitable")
        dd_col.metric("Worst Drawdown", f"Rs {ev.worst_drawdown:,.0f}")

        st.markdown("#### 👷 Agent Work Jobs Breakdown")
        job_rows = []
        for a in cohort:
            role_desc = {
                "beginner": "🚸 Beginner Auditor · Assesses fee drag & small-account survivability",
                "risk_manager": "🛡️ Risk Manager · Audits capital protection & drawdown limits",
                "momentum": "🌊 Momentum Specialist · Audits trend continuation regimes",
                "contrarian": "🔄 Contrarian Auditor · Audits mean-reversion & chop resilience",
                "optimizer": "📊 Optimizer & Stats · Audits profit factor & trade frequency",
                "impatient": "⚡ Rapid Execution · Tests signal latency & churn",
                "power_user": "🛠️ Power User · Stress-tests sizing & session rules",
                "adversarial": "⚔️ Adversarial Attacker · Actively probes shock & noise failure modes",
            }.get(a.persona.name, f"{a.persona.name} ({a.persona.role})")

            job_rows.append({
                "Agent Job": role_desc,
                "Stance": f"{a.stance:+.2f} ({'Bullish' if a.stance > 0.2 else ('Defensive' if a.stance < -0.2 else 'Neutral')})",
                "Strategy Belief": f"{a.memory.beliefs['strategy_quality']:.2f}",
                "Risk Belief": f"{a.memory.beliefs['risk_safety']:.2f}",
                "Simulated P&L": f"{a.pnl:+.2f}",
                "Debate Messages": a.messages,
            })
        st.dataframe(job_rows, hide_index=True, use_container_width=True)

        if ev.failure_modes:
            st.error("⚠️ Adversarial Failure Modes Found: " + " · ".join(ev.failure_modes))
        else:
            st.success("✅ No critical failure modes detected across independent stress regimes.")

        with st.expander("📊 View Independent Regime Stress-Test Evidence"):
            st.dataframe(
                [
                    {
                        "Market Regime": item.regime.capitalize(),
                        "Net P&L (Rs)": round(item.pnl, 2),
                        "Trades": item.trades,
                        "Profit Factor": round(item.profit_factor, 2),
                        "Drawdown (Rs)": round(item.drawdown, 2),
                        "Passed Stress": "✅ Pass" if item.passed else "❌ Fail",
                    }
                    for item in ev.evidence
                ],
                hide_index=True,
                use_container_width=True,
            )

ui.workflow_nav("backtest", complete=st.session_state.get("result") is not None)
ui.footer_note()
