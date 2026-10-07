# Strategy spec: Prior-Day Value Area Breakout (long only)

**Status: UNVERIFIED idea, not yet backtested.** It was passed along as the method of a trading-championship
winner (Gianluca Bruni). A web search did not confirm that person, that result, or that this is his method, so
judge the rules on test results alone, not on the name.

## Task for the coding agent (paste this)
> Read this file and `value_area_breakout.py`. (1) Run `python -m pytest test_value_area_breakout.py`.
> (2) Get real intraday data with real volume (NSE stocks or futures, 1-minute, at least 6 to 12 months, several
> liquid symbols) and run the backtest and the grid. (3) Report results using the test protocol below, including the
> no-volume-filter baseline. (4) Do NOT trade live and do NOT touch any live-order code. Sandbox only. Never print
> or commit API tokens. (5) Tell me honestly if the results are weak or the sample is too small.

## Rules
1. **Value area.** For each session, build a volume profile (each bar's volume spread over the prices it traded
   through). POC = price with most volume. Value area = smallest range around the POC holding 70% of volume.
   VAH and VAL are its top and bottom. Use **yesterday's** values only (no look-ahead).
2. **Signal.** On 15-minute candles, a candle **closes above VAH** and its volume is **low** (relative volume
   <= `low_volume_ratio`, where relative volume = candle volume / average volume of the same time slot over the
   previous 20 sessions).
3. **Entry.** Buy at the **open of the next candle** (a close can only be acted on afterwards).
4. **Stop.** Low of the signal candle. **Target.** Entry + 2 x risk (risk = entry - stop).
5. **Exit.** Stop, target, or the 15:15 square-off, whichever comes first. If a candle touches both stop and
   target, assume the **stop** hit first. One trade per day. Long only.

## Assumptions I had to make (the description was ambiguous)
| Question | Choice in the code | Parameter |
|---|---|---|
| "wait for price to come back to that zone" | Price must overlap [VAL, VAH] earlier the same day, otherwise no trade (gap-up days skip) | `require_return_to_zone` |
| Is the breakout the first close above VAH? | Yes, the previous 15m close must be <= VAH | `require_fresh_cross` |
| What is "low volume"? | Relative volume <= 0.8 (same time slot, 20-day baseline) | `low_volume_ratio` |
| Value area size | 70% of volume | `value_area_pct` |
| Skip silly stops | Risk must be between 0.05% and 1.5% of entry | `min/max_risk_pct` |
| Costs | 3 bps + 2 bps slippage per side (rough; use the app's cost model in the app) | `cost_bps_per_side`, `slippage_bps_per_side` |
| Shorts | Not tested (the description only mentions buying) | none |

## Data requirements
- Needs an instrument with **real volume**: stocks or futures. **Indices such as Nifty 50 have no volume**, and the
  script refuses to run on them.
- 1-minute bars (or at most 15-minute). Value area built from 1-minute bars is much better than from 15-minute bars.
- Optional Upstox download is included (`--upstox-key`, `--start`, `--end`, token from `UPSTOX_ANALYTICS_TOKEN`).
  It is not covered by tests; check the first download by eye.

## Why it needs a hard test
Many traders are taught the opposite: breakouts on **high** volume are more reliable, and low-volume breakouts
fail more often. The claim here (low volume means buyers are in control) may or may not hold. The no-volume-filter
rows in the grid answer it directly: if "none" does as well as 0.6 or 0.8, the volume condition adds nothing.

## Test protocol
1. Run the base rules and `--grid` on each symbol, then pooled across symbols.
2. Compare each result to **the same strategy with no volume filter** and to **random entry times** with the same
   stop/target rules.
3. Split by time: first 60% in-sample, last 40% out-of-sample. Judge the out-of-sample part.
4. Check robustness: results should not depend on one lucky setting. Nearby values (0.6/0.8/1.0, RR 1.5/2/3) should
   behave similarly.
5. Report: trades, win rate, average R, profit factor, max drawdown (R), longest losing streak, by month.

Suggested bar to pass (adjust if you disagree, but decide it **before** looking at results):
at least 100 trades, positive average R after costs in the out-of-sample part, profit factor above 1.2,
and no collapse when costs are doubled.

## Phase 2: only if it passes, add to TradeALGO
The current rule engine (`configs/*.yaml`, `algobot/levels.py`) can use `prev_day_high/low` but cannot express this:
- new level types `prev_day_vah`, `prev_day_val`, `prev_day_poc`, built from the previous finished session only
  (same no-look-ahead pattern as `prev_day_high`);
- a relative-volume indicator (same time slot, prior N sessions only);
- stop at the signal candle's low and target as a multiple of risk (the engine currently has percent stops/targets);
- a config in `configs/`, tests, and a run of `python -m algobot lookahead-check`.
Keep it in paper/sandbox. Live orders stay locked.

## Not financial advice
This is a research tool. A backtest on past data does not predict future results.
