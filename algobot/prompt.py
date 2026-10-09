"""The prompt a trader can give to any AI chat assistant to turn an idea
written in plain English into rules this toolkit accepts.

Design principle (learned from reviewing "AI writes the code" tutorials):
the AI fills in a small, strict format that this program then VALIDATES. It
never writes code that gets executed, so a wrong or malicious answer cannot
run anything. The trader then checks the plain-English readback produced by
this program (not by the AI) before running any test.
"""

AI_STRATEGY_PROMPT = """\
You are helping me write a trading strategy in a strict format for my
backtesting tool. Reply with ONE yaml block and nothing else inside it, using
exactly these keys (leave a rule out if the strategy does not need it):

indicators:
  - {name: <letters_digits_underscores>, type: <type>, period: <whole number>}
entry_long: "<condition>"
exit_long: "<condition>"
entry_short: "<condition>"
exit_short: "<condition>"

ALLOWED indicator types: sma, ema, wma, hma, rsi, mfi, cci, atr, highest, lowest, vwap,
  prev_day_high, prev_day_low, prev_day_close, prev_week_high, prev_week_low,
  swing_high, swing_low, opening_range_high, opening_range_low,
  pivot, pivot_r1, pivot_r2, pivot_r3, pivot_s1, pivot_s2, pivot_s3.
  - vwap, the prev_day_* / prev_week_* types, and pivot / pivot_r1..r3 / pivot_s1..s3
    need no period.
  - swing_high / swing_low: period = bars on EACH side needed to confirm the swing.
  - opening_range_high / opening_range_low: period = minutes in the opening window
    (e.g. 15 for the first 15 minutes of the day).
  - Optional key "source": open, high, low, close or volume (default close) for
    sma, ema, wma and rsi. hma uses close only (no "source"). mfi always uses
    high, low, close and volume together (no "source"). cci defaults to typical price
    (high + low + close) / 3 if source is omitted.
  - highest / lowest = the highest high / lowest low of the PREVIOUS n bars.
  - hma (Hull Moving Average): tracks price more closely than sma/ema/wma, with
    less lag, at the cost of overshooting a little right after a sharp move.
  - mfi (Money Flow Index, 0-100): like rsi but weighted by volume, so it reads
    as buying/selling PRESSURE rather than just direction. The closest proxy to
    order flow this engine can offer from candle (OHLCV) data -- it has no
    bid/ask or trade-by-trade tape, so it cannot see real buy vs. sell order
    volume the way a genuine order-flow/footprint tool does.
  - cci (Commodity Channel Index): measures price variation from its statistical
    mean (-100 to +100 normal channel, overbought > +100, oversold < -100).

A condition is a true/false statement using ONLY:
  - open, high, low, close, volume
  - the indicator names I defined
  - <name>_prev for the value one bar earlier (example: close_prev, ema_fast_prev)
  - numbers, + - * /, comparisons (> < >= <= == !=), and / or / not, brackets.
NOT allowed: function calls, dots (no close.shift(1)), quotes, any other words.
To detect a crossover, compare now and one bar ago, for example:
  "ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev"

Rules for you:
  - If my idea needs something this format cannot express, say exactly what is
    missing. Do NOT invent new syntax or indicator types.
  - Use the exact numbers I give. Do not add extra filters I did not ask for.
  - After the yaml block, restate the strategy in plain English in 3 to 6
    lines so I can check it matches my idea.

My strategy idea:
<describe it here in your own words, for example: buy when the 9-bar average
crosses above the 21-bar average and RSI is above 50; sell when it crosses back>
"""
