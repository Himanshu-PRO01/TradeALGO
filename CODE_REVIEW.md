# v0.6 engineering review

## What was verified

- The complete automated test suite passes: **239 tests**.
- The read-only OpenAlgo bridge has no code path for placing, changing, or cancelling orders.
- The demo EMA/RSI strategy was run through the built-in reality check. It lost money after the configured costs and was correctly rated **NOT READY**. It must not be paper traded as a strategy.

## Safety improvement made in v0.6

The option breakeven calculator used only a Black-Scholes theoretical premium as its entry cost. That is unsafe when the actual ask is materially higher than the model price.

It now accepts an optional actual `entry_premium` / ask:

- CLI: `--entry-premium 118.5`
- Dashboard: **Actual entry premium / ask**
- The output states whether it used the actual market premium or a model estimate.
- If the actual premium is missing, the dashboard and report explicitly warn that the result is not a tradable quote.

## Claims this project must not make

- It cannot claim profit or a winning strategy.
- A passing audit is permission only to continue with paper trading; it is not evidence to trade real money.
- The later-period check is a stability check, not a genuine unseen-data test if the strategy was designed after looking at all of the history.

## High-priority work after the brother supplies one exact strategy

1. Obtain the correct historical data for the actual instrument. For options, this means the traded premium, strike, expiry, bid/ask spread, lot size and timestamps - not just Nifty index candles.
2. Freeze one written config before looking at a holdout period. Record a hash of the config and data, then run the holdout once. Do not tune after seeing the result.
3. Add instrument-specific execution constraints: available capital/margin, lot-size validation, tick size, liquidity and conservative partial-fill/rejection assumptions.
4. Run paper trading with the same journal and limits. Compare real alert time, quoted entry, attainable fill, stop behaviour and costs with the backtest assumptions.
5. Do not add live order placement until the paper-trading result and broker/compliance setup are independently confirmed.

## Known modelling limits

- The bar backtester is intraday only.
- It does not model margin/leverage, partial fills, broker rejections or liquidity. Results remain optimistic.
- Stop/target behaviour within an OHLC bar is an approximation.
- The option tool estimates future premium with Black-Scholes; it cannot reproduce an option chain's actual bid/ask or implied-volatility surface.


---

## Merge notes for v0.6.1 (added when this review was merged)

- **What was merged.** The reviewed copy was built on the v0.5 code. Its changes (the actual-ask input for the
  option breakeven tool in the library, the CLI flag `--entry-premium` and the dashboard page; the honest rename
  of the later-period audit check; the tests; the README line) were merged into v0.6, which adds the test lab,
  the fake markets and the practice room. The three-way merge had no conflicts. The reviewed zip's inner copy was
  byte-identical to its outer files, and a scan of the reviewed code found no shell, exec, or unexpected network
  use (the only network code is the read-only OpenAlgo bridge to the address you configure).
- **One correction on top of the review.** The review treats the supplied entry premium as the price paid and still
  adds the whole bid-ask spread. An actual ask already contains the entry half of the spread, so that counted half
  the spread twice (in the cautious direction). v0.6.1 adds only the exit half when an actual ask is given. Both
  routes now agree: an ask equal to the model mid plus half the spread gives exactly the same breakeven as the
  model route (a test checks this), and a dearer real ask raises the hurdle by about the extra cost divided by delta.
- **Test count.** The 239 in the review refers to the v0.5-based copy. The merged v0.6.1 suite has 277 tests, all passing.
- **Still true after the merge.** Nothing here can promise profit. The practice room and test lab use made-up
  prices and cannot show what will make money.
