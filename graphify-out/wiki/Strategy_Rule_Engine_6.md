# Strategy Rule Engine (6)

> 23 nodes

## Key Concepts

- **lookahead.py** (24 connections) — `algobot/lookahead.py`
- **check_future_scramble()** (14 connections) — `algobot/lookahead.py`
- **run_lookahead_checks()** (14 connections) — `algobot/lookahead.py`
- **check_truncation()** (12 connections) — `algobot/lookahead.py`
- **selftest()** (12 connections) — `algobot/lookahead.py`
- **LeakyStrategy** (11 connections) — `algobot/lookahead.py`
- **check_indicator_columns()** (11 connections) — `algobot/lookahead.py`
- **DataFrame** (9 connections)
- **test_level_indicators_pass_all_lookahead_checks()** (7 connections) — `tests/test_levels.py`
- **Check** (6 connections) — `algobot/lookahead.py`
- **_signals()** (5 connections) — `algobot/lookahead.py`
- **test_every_check_catches_a_strategy_that_peeks_one_bar_ahead()** (5 connections) — `tests/test_explain_lookahead.py`
- **test_honest_strategies_pass_every_check()** (5 connections) — `tests/test_explain_lookahead.py`
- **_alter_future()** (4 connections) — `algobot/lookahead.py`
- **_first_difference()** (3 connections) — `algobot/lookahead.py`
- **.on_bar()** (2 connections) — `algobot/lookahead.py`
- **.prepare()** (2 connections) — `algobot/lookahead.py`
- **parametrize** (1 connections)
- **parametrize** (1 connections)
- **Look-ahead checks. Look-ahead bias means a backtest secretly used information…** (1 connections) — `algobot/lookahead.py`
- **DELIBERATELY BROKEN: buys when the NEXT bar closes higher. For self-test only.** (1 connections) — `algobot/lookahead.py`
- **Run the checks on a strategy that cheats. Every check must FAIL.** (1 connections) — `algobot/lookahead.py`
- **Keep bars [0, k) and replace everything after with a very different future.…** (1 connections) — `algobot/lookahead.py`

## Relationships

- [App Configuration & Settings](App_Configuration_&_Settings.md) (10 shared connections)
- [Pivot Points & Price Levels](Pivot_Points_&_Price_Levels.md) (5 shared connections)
- [CLI Parser & Commands (2)](CLI_Parser_&_Commands_2.md) (5 shared connections)
- [Strategy Lab & Research](Strategy_Lab_&_Research.md) (4 shared connections)
- [Backtesting & Historical Execution (2)](Backtesting_&_Historical_Execution_2.md) (3 shared connections)
- [Strategy Rule Engine (9)](Strategy_Rule_Engine_9.md) (3 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (3 shared connections)
- [Explain Lookahead Module](Explain_Lookahead_Module.md) (2 shared connections)
- [Agent V2 Market Module](Agent_V2_Market_Module.md) (2 shared connections)
- [Backtesting & Historical Execution (3)](Backtesting_&_Historical_Execution_3.md) (2 shared connections)
- [App Configuration & Settings (2)](App_Configuration_&_Settings_2.md) (1 shared connections)
- [Market Data Validation & Feed (2)](Market_Data_Validation_&_Feed_2.md) (1 shared connections)

## Source Files

- `algobot/lookahead.py`
- `tests/test_explain_lookahead.py`
- `tests/test_levels.py`

## Audit Trail

- EXTRACTED: 94 (96%)
- INFERRED: 4 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*