# algobot v0.7: our layer on top of OpenAlgo, now with a trading-desk interface

This is the first building block of the algo trading project: a **backtester**
with realistic costs, a **risk manager**, a **strategy system the trader can
edit without coding**, and (new in v0.2) a **dashboard**, a **plain-English
readback**, a **look-ahead checker** and (new in v0.3) tools for trading Nifty options by hand:
**position sizing**, a **trade journal**, a **daily P&L report** and **support/resistance level rules**, and
(new in v0.4) a **reality check** that tries to break a strategy the ways strategies usually break.
It does not place real orders, on purpose.

Everything here is independent of the actual strategy, so it can be built and
tested before the brother's answers arrive. The two strategies included are
**demos to prove the pipeline works. They are not trading advice.**

## Quick start

You need Python 3.9 or newer.

```bash
# 1. (recommended) make a private environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. install the libraries
pip install -r requirements.txt

# 3. make random test data (NOT real market data)
python -m algobot sample-data --out data/sample_5min.csv

# 4. run a demo backtest
python -m algobot backtest configs/demo_sma.yaml
python -m algobot backtest configs/demo_rules.yaml

# 5. run the automatic tests (should say "296 passed")
python -m pytest -q tests
```

### The dashboard (for people who do not code)

```bash
streamlit run Trading_Desk.py
```

It opens in your browser. Pick data, edit the rules in a box, read the
plain-English version of what you wrote, tick "Yes, this is exactly what I
meant", then run a backtest or the look-ahead check. It only runs tests on your
own computer: **never type broker keys or passwords into it.**

### Two safety tools (also available as commands)

```bash
# Say the strategy back in ordinary words. Does it match what you meant?
python -m algobot explain configs/demo_rules.yaml

# Prove the rules cannot secretly use future prices (the classic backtest lie)
python -m algobot lookahead-check configs/demo_rules.yaml

# Prove the checker itself works: it must catch a strategy that cheats
python -m algobot lookahead-check --selftest
```


### Tools for trading Nifty options by hand (new in v0.3)

The dashboard has two extra pages in its left menu, and every tool is also a command:

```bash
# How many lots fit a Rs 1,000 maximum loss? (Nifty lot size default is 65: confirm it, it changes)
python -m algobot size --max-loss 1000 --entry 100 --stop 85 --capital 10000

# Write every trade down (the stop and the reason are what make the journal useful)
python -m algobot journal add --instrument "NIFTY 24500 CE 25-Sep" --side BUY --qty 65 --entry 100 --stop 85 --setup "resistance breakout"
python -m algobot journal close 1 --exit 112 --charges 60 --lessons "waited for the candle close"

# Daily P&L report (add --html report.html to save it) and a review of all closed trades
python -m algobot report --capital 10000 --max-loss-per-trade 1000 --max-trades 2
python -m algobot review
```

The report flags broken rules (a loss beyond the per-trade limit, a trade with no stop,
too many trades in a day). The review shows win rate, average win and loss, profit factor,
average R (result measured in units of the amount risked), longest losing run, and results
by setup. Treat any number as noise until there are roughly 30 to 50 trades.

**Support and resistance in rules.** New indicator types for the `rules` strategy:
`prev_day_high`, `prev_day_low`, `prev_day_close`, `prev_week_high`, `prev_week_low`
(no period needed) and `swing_high`, `swing_low` (period = bars needed on each side to
confirm a swing; a swing only appears that many bars after it happened, so there is no
look-ahead). See `configs/demo_levels.yaml`.



## Working with OpenAlgo (our layer on top of an open-source platform)

[OpenAlgo](https://docs.openalgo.in) is a free, open-source (AGPL-3.0), self-hosted platform. From its
documentation it already provides: a unified API across brokers (Upstox included), live and historical data
(Historify), signals from TradingView and others, a sandbox with Rs 1 crore of test capital, an optional
manual-approval workflow for orders, Telegram notifications, and option chain and Greeks tools. **We do not copy
or rebuild any of that.** This toolkit runs as a separate program and talks to OpenAlgo over its documented
HTTP API. OpenAlgo's own documentation says plainly that it is a tool, not a get-rich-quick scheme: profit
depends on the strategy.

| OpenAlgo does (reuse it) | Our layer adds (what it does not list) |
|---|---|
| Broker login, prices, history, Telegram, TradingView webhooks, sandbox | Strategy audit: does the rule beat luck, costs, random entries, changes over time? |
| Placing orders (not used by us) | Look-ahead proof, experiment log (cherry-picking guard), data quality checks |
| Option chain and Greeks | Breakeven after time decay, spread and IV crush; risk-of-ruin simulation |
| P&L tracker | Trade journal with behaviour checks (stops ignored, revenge trades, overtrading) |
| Alerts when a level is hit | A pre-trade gate: today's limits from the journal plus how many lots fit the loss limit, in the same message |

### Connecting to your OpenAlgo

1. Install and run OpenAlgo by following its own guide (it needs Python 3.12 or newer), connect the broker
   (Upstox), and create an API key on its web page.
2. Copy `.env.example` to `.env` in this folder and paste the key and address into it. `.env` is private and
   is ignored by Git. **Never paste the API key into a chat, a config file or a screenshot.**
3. Use it:

```bash
# Real Nifty candles from your own broker connection, checked and saved for testing and the audit
python -m algobot fetch-history --symbol NIFTY --exchange NSE_INDEX --interval 5m --from 2026-08-01 --to 2026-09-19 --out data/nifty_5m.csv

# Lot size read from OpenAlgo's instrument list instead of a number typed in by hand
python -m algobot size --max-loss 1000 --entry 100 --stop 85 --capital 10000 --symbol NIFTY29SEP2624500CE

# Size a planned trade, check today's limits in the journal, and send the result to Telegram
python -m algobot alert --instrument "NIFTY 24500 CE" --entry 100 --stop 85 --capital 10000 --max-loss 1000 \
    --max-trades 2 --max-daily-loss 1500 --telegram-user brother
```

**Safety by design.** The bridge can read data and send notifications. It has no function that places,
changes or cancels an order (a test checks this), so it cannot send a wrong one. The API key is read only
from the environment and scrubbed from error messages.

**Limits to know.** Brokers usually keep only the last 30 to 90 days of intraday candles, and a strategy
needs 100 or more trades to be judged, so start saving history now (OpenAlgo's Historify) and re-run
`fetch-history` regularly. The bridge is built to OpenAlgo's published API and tested against a local stand-in
server, not against a live OpenAlgo, so expect to fix small differences on first contact. If orders are ever
placed through OpenAlgo, the account holder is responsible for the static IP and the other SEBI
requirements (OpenAlgo's own compliance page says the trader carries these). Alerts only need none of that.



## The interface: a trading desk in the browser

Start it with `streamlit run Trading_Desk.py` (or double-click `run_windows.bat` / `run_mac.command`).
Dark theme, monospace numbers, green for up and profit, red for down and loss, and an always-visible
"NO LIVE ORDERS" badge. The left menu runs in the order a trader uses it:

| Page | What it is |
|---|---|
| Trading Desk | Front page: what each tool is for, a 10-minute tour, what the tool will never do |
| Position size | How many lots fit the loss limit, and are today's limits still open |
| Journal and report | Trade journal, daily P&L report, review with behaviour checks, backup and restore |
| Practice room | Fake-money option trading: candlesticks, order ticket with bid/ask, option chain, blotter, and a review that splits every trade into market move, time decay, spread and charges |
| Option breakeven and ruin | How far Nifty must move to break even (with a profit-vs-move chart), and the chance a losing streak wrecks the account |
| Backtest | Test a rule on past prices: candles with trade markers, equity and drawdown, trade blotter |
| Reality check | The audit, with a pass/warn/fail line for each test |
| Test lab | Many fake markets, plus the cheating test |
| Feedback | The brother writes what to change; copy it to WhatsApp or download it |

**Sharing it.** Two ways, described in `HOSTING.md`: send the zip (he double-clicks the launcher; nothing
leaves his computer), or put it online as a private link on Streamlit Community Cloud (not done for you:
you follow the steps once). For a link, set `hosted = "1"` and a `password` in the app's Secrets. Hosted
mode keeps each visitor's journal only in their own browser session, so visitors can never see each
other's trades, and the Journal page can download and reload a backup. The interface never asks for broker
keys and has no order function, in either mode.

## The test machine: fake markets, fake money, unlimited time

Two tools, both free and instant, both using made-up prices (see "What fake data can and cannot do" below).

**Test lab** (dashboard page, or `python -m algobot lab configs/demo_rules.yaml`). Builds as many fake
worlds as you like in seven personalities (`python -m algobot worlds`): pure noise, trend, mean reversion,
chop, volatile, crash and news shocks. Runs the strategy through each with its real costs and risk rules and
shows where it earns, where it loses and whether its safety rules held (nothing overnight, trade limits,
daily loss). It also runs a **cheating test**: on pure noise with all costs removed, an honest strategy
earns about zero. If it profits from random prices it is peeking at the future or has a bug, and nothing
else it shows can be trusted. (The test is itself tested: it catches a strategy that cheats on purpose.)

**Practice room** (dashboard page). A flight simulator for buying Nifty options with fake money. You see
the fake market up to now and never ahead. Prices come from an option pricing model, so time decay, the
buy-sell spread, charges, stops that gaps jump through and expiry all behave like the real thing, and your
own limits (max trades, max daily loss) can be broken on purpose. The market type is hidden until the end.
When you finish, every trade is split into what the market move earned, what time decay took, and what
spread and charges took, and the journal's behaviour checks run on your session. Start a new market as
often as you like; use "mixed" for a market that changes character every few days.

```bash
python -m algobot worlds                                   # the fake market personalities
python -m algobot lab configs/demo_rules.yaml              # stress lab
python -m algobot make-world --regime mixed --days 30 --seed 7 --out data/mixed.csv   # a fake market to a CSV
```

### What fake data can and cannot do

* **It can:** find bugs, test that risk rules really hold, show which market types a strategy needs, and
  train the habits of the person trading it (patience, stops, size, respecting limits).
* **It cannot:** create a real edge. Fake prices are random. Practising for unlimited time teaches the
  trader; it does not teach the market anything. Tuning a strategy until it wins on made-up prices only
  teaches it to fit noise, which is exactly what the reality check exists to catch.
* **The honest path to a real result:** practice room (learn) then test lab (robustness) then the reality
  check on real history from your broker then paper trading on live prices for a couple of months (OpenAlgo's
  sandbox does this with test money) then start with a tiny amount.

## Why trading software fails to make profit, and what algobot does about it

Software does not create profit; an edge does, and most of what looks like an edge in a backtest is
not one. SEBI's FY26 study of individual F&O traders found 87.7% lost money, options caused about 92% of
the losses, about 97% of traders mostly bought options, about Rs 25,000 crore went on transaction costs,
and among people who lost two years running and kept trading, about 90% lost again. The usual reasons,
and what this toolkit does about each:

| Why it fails | What algobot does | What it cannot fix |
|---|---|---|
| **Look-ahead bias**: the test secretly uses future prices | Decisions fill at the NEXT bar's open. `lookahead-check` proves rules cannot see the future and is itself tested against strategies that cheat | Nothing: this one is closed |
| **Costs and slippage** eat a small edge | Every order pays brokerage, taxes, slippage. The audit reruns at 1.5x and 2x costs | Real fills can still be worse than any model |
| **Overfitting** to one stretch of history | Audit: settings changed by 20%, later-period stability (a stability check, NOT a true holdout), profit concentration | Only new, unseen data (a frozen rule tested once, then paper trading) settles it |
| **Cherry-picking** (trying many variants, keeping the best) | Every backtest is logged; the audit raises its bar with the number of variants tried | It cannot count ideas you tried elsewhere. Raise the number by hand |
| **Too few trades**: luck looks like skill | Audit needs 100+ trades, gives a confidence range, warns below 30 | No shortcut: it takes time |
| **Entry rule adds nothing** | Audit compares against random entries with the same stops, costs and holding time | A strategy can pass and still stop working later |
| **Bad data**: gaps, spikes, frozen feeds | `check-data`; warnings printed after every backtest | Wrong data that looks plausible |
| **Option decay, spread and IV crush** (a right call can still lose) | `breakeven`: how far Nifty must move to break even given time decay, spread, charges, IV change | It is a model; real premiums differ, especially near expiry and around events |
| **Betting too much**: a normal losing streak wrecks a small account | `ruin`, plus the audit's Monte Carlo: chance of losing X% of the account. `size` warns when risk per trade is high | It cannot make a strategy with no edge survive |
| **Human habits**: moved stops, revenge trades, overtrading | Journal review flags stops ignored, trades soon after a loss, too many trades, trades after the daily limit, losers held longer than winners | It only sees what is written in the journal |
| **Edge decay**: markets change | Weekly review of journal statistics against the plan | Not automated yet (see roadmap) |

**How the audit was tested (so you can judge how far to trust it).** A checker nobody has tried to
fool is not evidence. On synthetic data: 8 of 8 datasets with a planted trend edge got "PASSED THESE
CHECKS"; 8 of 8 pure-noise datasets got "NOT READY"; and on 20 datasets of pure noise where the best of 12
zero-cost variants was picked (the classic cherry-pick), 0 passed, 4 were rated "promising but
unproven" and 16 "not ready". Real markets are harder than these tests. A pass is permission to paper
trade, not to trade money.

### The reality check tools

```bash
# Try to break a strategy (takes about a minute). Exit code 1 if any check fails.
python -m algobot audit configs/demo_rules.yaml

# How many variants have you tried on this data? (the audit uses this number automatically)
python -m algobot experiments

# Look for missing bars, spikes, frozen feeds and bad timestamps in a data file
python -m algobot check-data data/sample_5min.csv

# How far must Nifty move for a bought option to break even? (IV, days and prices from the option chain)
# Supply the actual ask when you have it (it already contains the entry half of the spread). Without it, the tool uses a
# Black-Scholes estimate and labels the result accordingly.
python -m algobot breakeven --spot 24500 --strike 24500 --type CE --days 3 --iv 14 --hold 1 --entry-premium 118.5 --spread 0.5 --charges 100

# How likely is a normal losing streak to wreck the account?
python -m algobot ruin --win-rate 45 --reward-r 1.5 --risk-pct 10 --cost-r 0.1

# Behaviour checks on the journal (stops ignored, revenge trades, overtrading, limits)
python -m algobot review --max-loss-per-trade 1000 --max-trades 2 --max-daily-loss 2000
```

The dashboard has matching pages: **Reality check** (uses the strategy and prices from your last
backtest) and **Option breakeven and ruin**.

### Getting an AI to write the rules

```bash
python -m algobot ai-prompt
```

prints a prompt you can paste into any AI chat together with your idea in plain
English. The AI must answer in our strict rule format, and the toolkit
**validates** the answer. The AI never writes code that gets run. After pasting
its answer, read the plain-English readback to check the AI understood you.

Results are saved in `results/<name>/`: `trades.csv` (every trade),
`equity.csv` and `equity.png` (account value over time).

On random data a strategy has no edge, so expect small losses, and notice how
much of the loss is trading costs. That is exactly why costs are in the model.

## Folder map

| Path | What it does |
|---|---|
| `configs/` | Settings files the trader edits (strategy, risk limits, costs) |
| `data/` | Price data (CSV). Put real data here later |
| `algobot/config.py` | Reads and checks the settings, gives friendly errors |
| `algobot/data.py` | Loads and validates price data, makes test data |
| `algobot/indicators.py` | SMA, EMA, RSI, ATR, highest, lowest, VWAP |
| `Trading_Desk.py` | Front page of the browser interface (Streamlit). `dashboard.py` is kept as an alias |
| `algobot/ui.py`, `charts.py`, `palette.py` | The dark trading-desk look: header, ticker strip, candlestick, equity and payoff charts |
| `algobot/appstate.py` | Local or hosted storage, and the optional password screen |
| `algobot/feedback.py` | Suggestions from the brother, savable and shareable |
| `run_windows.bat`, `run_mac.command`, `START_HERE.txt`, `HOSTING.md` | One-click launchers and the guides for sharing |
| `.streamlit/config.toml` | Dark theme settings |
| `algobot/strategy.py` | Strategies: `sma_crossover` and the editable `rules` |
| `algobot/explain.py` | Plain-English readback of a strategy and its limits |
| `algobot/lookahead.py` | Look-ahead checker (and a self-test with a cheating strategy) |
| `pages/` | Extra dashboard pages: position size, journal and report, reality check, option breakeven and ruin, test lab, practice room |
| `algobot/sizing.py` | Options position sizing from a maximum loss |
| `algobot/journal.py` | Trade journal (SQLite), daily report, review statistics |
| `algobot/levels.py` | Previous day/week levels and confirmed swing points |
| `algobot/audit.py` | The reality check: eight tests that try to break a strategy |
| `algobot/experiments.py` | Counts variants tried on the same data (cherry-picking guard) |
| `algobot/options.py` | Black-Scholes model and the option breakeven analysis |
| `algobot/ruin.py` | Risk-of-ruin simulator |
| `algobot/dataquality.py` | Data quality checks |
| `algobot/openalgo_bridge.py` | Read-only OpenAlgo client: history, lot size, Telegram notify (no orders) |
| `algobot/gate.py` | Pre-trade gate and the sized alert message |
| `.env.example`, `.gitignore` | Where the private key goes (never committed) |
| `algobot/worlds.py` | Fake market personalities and a market that changes character |
| `algobot/lab.py` | Stress lab and the cheating (null) test |
| `algobot/practice.py` | The practice room engine: fake-money option trading with decay, spread and rules |
| `algobot/prompt.py` | The prompt that makes an AI write rules in our format |
| `algobot/runner.py` | One-call helpers used by the dashboard |
| `algobot/risk.py` | Trading window, trade limits, daily-loss kill switch |
| `algobot/costs.py` | Brokerage, taxes, charges and slippage |
| `algobot/engine.py` | The bar-by-bar simulator |
| `algobot/metrics.py`, `report.py` | Statistics, printed summary, saved files |
| `tests/` | 296 automatic tests (dashboard pages, cheating strategies, audit discrimination, OpenAlgo bridge against a local server, fake worlds, practice room) |

## How the trader changes the strategy (no Python needed)

Open `configs/demo_rules.yaml`. The strategy is written as indicators plus
plain conditions:

```yaml
strategy:
  name: rules
  params:
    indicators:
      - {name: ema_fast, type: ema, period: 9}
      - {name: ema_slow, type: ema, period: 21}
      - {name: rsi_14,   type: rsi, period: 14}
    entry_long:  "ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev and rsi_14 > 50"
    exit_long:   "ema_fast < ema_slow"
```

* **Indicator types:** `sma`, `ema`, `rsi`, `atr`, `highest`, `lowest`, `vwap`.
  `highest`/`lowest` mean the highest high / lowest low of the *previous* N bars.
* **Columns you can use in a rule:** `open high low close volume`, every
  indicator you named, and `<name>_prev` for the previous bar's value
  (for example `close_prev`). Use `_prev` to detect crossovers.
* **Operators:** `> < >= <= == !=`, `+ - * /`, `and`, `or`, `not`, brackets.
* **Not allowed:** function calls and things like `close.shift(1)`. This keeps
  the config from running code.
* **Rules:** `entry_long`, `exit_long`, `entry_short`, `exit_short`. Shorts only
  happen when `allow_short: true`.
* Put times in quotes, like `"09:20"`.
* Typos are caught: an unknown setting name stops the run with a clear message,
  so a mistyped `stop_loss_pct` can never silently remove a stop-loss.

Check a config without running it: `python -m algobot check-config configs/demo_rules.yaml`

## Using real data

Any CSV with these columns works (volume is optional):

```
datetime,open,high,low,close,volume
2025-01-06 09:15:00,1000.9,1001.1,999.7,1000.1,1123
```

Then set `data.path` in the config, or run with `--data path/to/file.csv`.
Bad rows (missing prices, high below low, and so on) are rejected with a message.

## How the simulator behaves (and what it ignores)

* A decision is made at a bar's **close** and filled at the **next bar's open**
  (no look-ahead). Nothing is held overnight; positions are squared off at
  `risk.square_off_time`.
* Entries, signal exits, stop-losses and square-off pay slippage. Target exits
  are treated as limit orders with none.
* If one bar could have hit both stop and target, the stop is assumed first.
  A gap through a stop fills at the (worse) open.
* Every order pays the configured charges. **The charge rates in the demo
  configs are examples only.** Check your broker's charge calculator.
* **Not modelled yet:** margin and leverage limits, partial fills, broker
  rejections, liquidity. Results are therefore optimistic.

## Roadmap

1. **Done (v0.1 to v0.4):** core, tests, demo strategies, dashboard, readback, look-ahead checker,
   position sizing, journal, daily report, level indicators, reality check, experiment log, data checks,
   option breakeven, risk of ruin, behaviour checks.
2. Load real historical data. For options this means the traded premium, strike, expiry, bid/ask, lot size and
   timestamps, not only Nifty index candles.
2b. **Freeze-and-holdout workflow:** write one exact config, record a hash of the config and the data, then run
   the later period once and never tune after seeing the result. Not built yet (see CODE_REVIEW.md).
3. Turn the brother's strategy into a written spec, then into a `rules` config or a small custom strategy.
4. Paper trading on LIVE prices with fake money through OpenAlgo's sandbox, feeding our journal and
   Telegram alerts. Not built yet.
5. **Alerts (what the brother asked for, instead of automatic orders):** the bridge, the gate and the
   `alert` command are built. Still to do: trigger the gate automatically from a TradingView alert through
   OpenAlgo (its Flow builder or hosted Python strategies), once the brother's levels are written down.
   Reading prices and sending alerts places no orders.
6. **Live health monitor:** compare real journal results with the range the backtest predicted and warn
   when reality is worse than about 95% of simulated futures (edge decay). Not built yet.
7. Swing (multi-day) support in the backtester: today it is intraday only, and options need
   premium data, lot sizes and expiries. Waiting for the brother to say exactly how long he holds.
8. Broker connection for live orders (only if ever wanted), through OpenAlgo, and only after the
   broker confirms the account, API key and static IP setup.

## Design principles

* **The AI never writes code that runs.** It fills in a small strict format
  that this program validates. A wrong (or malicious) answer cannot execute anything.
* **Read it back in words.** A rule such as "RSI under 70" can silently become
  "over 70" and still pass every technical check. The readback is produced by
  this program, not by the AI, so the trader can catch it.
* **Costs are part of the test, not an afterthought.** On random data, most of
  a losing demo's loss is charges. Reports show results before and after costs.
* **A checker nobody has tried to fool is not evidence.** The look-ahead
  checker is tested against strategies that cheat on purpose, including a
  subtle one. (Building it, the first version missed a one-bar peek about half
  the time, which is how the "up / down / noise future" test came about.)
* **Secrets stay out of tools that do not need them.** Nothing here asks for
  broker keys. When a broker is connected later, keys will live in a private
  `.env` file, never in the dashboard, chats or Git.


## Independent review

An outside code review of this project is in [CODE_REVIEW.md](CODE_REVIEW.md): what was verified, a safety
fix to the option breakeven tool (it now accepts the actual ask instead of relying only on a model price), the
claims this project must never make (it cannot promise profit; a passing audit only permits paper trading), and
the work to do once the brother gives one exact strategy. Read it before trusting any number here.

## Important

This software is for learning and testing. Trading can lose money, and no
backtest guarantees future results. Check current SEBI and broker rules before
any live use. This is not financial or legal advice.
