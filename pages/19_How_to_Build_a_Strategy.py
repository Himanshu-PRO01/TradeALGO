"""How to Build a Strategy: a reference/checklist page, not a form. Turns a
trader's plain-English idea into the exact rule format Backtest/Paper
Trading/Sandbox Rehearsal all consume. No values here are executed --
copying an example still requires running it through Backtest yourself.
"""
import streamlit as st

from algobot import ui
from algobot.prompt import AI_STRATEGY_PROMPT

ui.setup("How to Build a Strategy", "\U0001F4D8")
ui.header(
    "How to Build a Strategy",
    "A strategy here means one specific thing: a rule precise enough that this program (not a person) "
    "can decide, bar by bar, whether to enter or exit. If an idea can't be written this precisely yet, "
    "that's useful information -- it means the idea isn't ready to test, not that the tool is missing a feature.",
    mode="guide:How to Build a Strategy",
)

st.markdown("### The fastest path: let an AI write it, this program checks it")
st.caption(
    "You never have to write the YAML below by hand. Describe your idea in plain English to any AI chat "
    "(ChatGPT, Claude, Gemini -- whichever you already use), using this exact prompt, then paste what it "
    "gives you into the Backtest page's strategy box."
)
with st.expander("Copy this prompt"):
    st.code(AI_STRATEGY_PROMPT, language="text")
    st.caption(
        "The AI fills in a small, strict format. This program then validates every field itself -- the AI's "
        "answer never runs as code, so a wrong or confused answer can't do anything except fail to validate. "
        "Always check the plain-English readback on the Backtest page (written by this program, not the AI) "
        "before trusting that it understood you."
    )

st.divider()
st.markdown("### The checklist (answer all seven before you're actually done)")
st.caption("Every field below is either required or defaults to something -- but a default is a decision too. "
           "Deliberately choosing a value is different from never having thought about it.")

checklist = [
    ("1. Instrument & timeframe", "What exactly are you trading (index, stock, which option) and on what "
     "candle size (1 min, 5 min, ...)? Different timeframes need different indicator periods."),
    ("2. Entry rule", "The exact condition that opens a position. \"Buy when it looks like it's turning up\" "
     "is not a rule yet. \"ema_fast crosses above ema_slow\" is."),
    ("3. Exit rule", "The condition that closes a position for a reason OTHER than a stop or target -- e.g. "
     "the same average crossing back. If you only ever exit on the stop-loss or target below, that's a valid "
     "answer too -- but say so on purpose."),
    ("4. Stop-loss and target", "stop_loss_pct / target_pct -- the percent move against/for you that force-closes "
     "a trade automatically, checked every bar, before the exit rule even gets a chance to fire. Leave a field "
     "empty on purpose if you really don't want one -- don't leave it blank by accident."),
    ("5. Position size", "strategy.quantity -- a fixed number of units per trade. Nothing here sizes a position "
     "based on account risk automatically yet; you decide the number."),
    ("6. Risk limits", "max_daily_loss, max_trades_per_day, max_position_value, and the trading_start / "
     "no_new_entries_after / square_off_time window. These apply on top of the strategy's own logic, as a "
     "second, independent brake."),
    ("7. Costs", "The defaults are typical Indian discount-broker charges (brokerage, STT, exchange fees, GST, "
     "slippage) -- realistic enough to start with, but check your own broker's charge calculator, especially "
     "for options, before trusting a result."),
]
for title, detail in checklist:
    st.markdown(f"**{title}**")
    st.caption(detail)

st.divider()
st.markdown("### Indicators you can use in a rule")
st.caption("Every one of these is look-ahead safe: none of them can see a bar before it has actually finished forming.")

ind_col1, ind_col2 = st.columns(2)
with ind_col1:
    st.markdown("**Need a period**")
    st.markdown(
        "- `sma`, `ema` -- moving average (period = bars)\n"
        "- `rsi` -- 0-100 momentum oscillator (period = bars)\n"
        "- `atr` -- average true range, a volatility measure (period = bars)\n"
        "- `highest`, `lowest` -- highest high / lowest low of the **previous** n bars\n"
        "- `swing_high`, `swing_low` -- a swing point confirmed by `period` bars on each side\n"
        "- `opening_range_high`, `opening_range_low` -- high/low of the first `period` **minutes** of the day"
    )
with ind_col2:
    st.markdown("**No period needed**")
    st.markdown(
        "- `vwap` -- volume-weighted average price\n"
        "- `prev_day_high`, `prev_day_low`, `prev_day_close`\n"
        "- `prev_week_high`, `prev_week_low`\n"
        "- `pivot`, `pivot_r1`/`r2`/`r3`, `pivot_s1`/`s2`/`s3` -- classic floor-trader pivot levels, built from "
        "the previous day's high/low/close"
    )
st.caption("Optional on sma/ema/rsi: `source` (open, high, low, close, or volume -- default close).")

st.divider()
st.markdown("### Writing the condition itself")
st.markdown(
    "A condition is a true/false statement built **only** from:\n"
    "- `open`, `high`, `low`, `close`, `volume`\n"
    "- the indicator names you defined above\n"
    "- `<name>_prev` for that same value one bar earlier (e.g. `close_prev`, `ema_fast_prev`) -- this is how "
    "you detect a crossover\n"
    "- numbers, `+ - * /`, comparisons (`> < >= <= == !=`), `and` / `or` / `not`, and brackets\n\n"
    "**Not allowed, on purpose:** function calls, dots (no `close.shift(1)`), quotes, or any other words -- "
    "a stricter language is what makes every rule here checkable automatically instead of trusted blindly."
)

st.divider()
st.markdown("### A worked example")
st.caption("Plain English -> exact rule -> the YAML this program actually reads.")
st.markdown(
    "> *\"Buy when the 9-period EMA crosses above the 21-period EMA, but only if RSI confirms real momentum "
    "(above 50) and volume is above its own 20-bar average. Exit the long when the EMA crosses back. Mirror "
    "the same logic for short trades.\"*"
)
st.code(
    """indicators:
  - {name: ema_fast, type: ema, period: 9}
  - {name: ema_slow, type: ema, period: 21}
  - {name: rsi_14,   type: rsi, period: 14}
  - {name: vol_avg,  type: sma, period: 20, source: volume}
entry_long:  "ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev and rsi_14 > 50 and volume > vol_avg"
exit_long:   "ema_fast < ema_slow"
entry_short: "ema_fast < ema_slow and ema_fast_prev >= ema_slow_prev and rsi_14 < 50 and volume < vol_avg"
exit_short:  "ema_fast > ema_slow"
""",
    language="yaml",
)
st.caption(
    "Notice what makes this a real rule and not just a phrase: every word above is either a price field, a "
    "named indicator, or a comparison -- there's no \"looks like\", \"seems to be turning\", or \"probably\". "
    "If your own idea has a word like that in it, that's the exact spot to sharpen before testing it."
)

st.divider()
st.markdown("### What happens after you have one")
st.caption(
    "This page only produces the rule. The rule then has to survive, in order: **Backtest** (does it even "
    "make money after costs, on some data) -> **Reality Check** (tries hard to break the result) -> "
    "**Paper Trading** (does it hold up on real, unseen prices with no money at risk) -> **Sandbox Rehearsal** "
    "(exercises the exact order-placement code path with fake money) -> a human deciding, deliberately, to "
    "approve real execution. Skipping straight to the end defeats the point of every step before it."
)

ui.footer_note("Reference only. Nothing on this page runs, backtests, or trades anything.")
