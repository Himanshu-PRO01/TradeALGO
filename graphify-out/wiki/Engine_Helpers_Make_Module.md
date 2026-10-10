# Engine Helpers Make Module

> 24 nodes

## Key Concepts

- **make_bars()** (37 connections) — `tests/helpers.py`
- **test_engine.py** (25 connections) — `tests/test_engine.py`
- **run()** (21 connections) — `tests/helpers.py`
- **flat_rows()** (18 connections) — `tests/helpers.py`
- **helpers.py** (16 connections) — `tests/helpers.py`
- **make_cfg()** (6 connections) — `tests/helpers.py`
- **test_costs_are_charged_on_both_sides()** (5 connections) — `tests/test_engine.py`
- **test_accounting_identity_end_equity_equals_capital_plus_trade_pnl()** (4 connections) — `tests/test_engine.py`
- **test_decision_is_filled_at_next_bar_open_not_signal_close()** (4 connections) — `tests/test_engine.py`
- **test_decision_on_last_bar_of_day_is_not_carried_overnight()** (4 connections) — `tests/test_engine.py`
- **test_gap_through_stop_fills_at_the_worse_open()** (4 connections) — `tests/test_engine.py`
- **test_kill_switch_exits_and_blocks_the_day_then_resets_next_day()** (4 connections) — `tests/test_engine.py`
- **test_max_trades_per_day()** (4 connections) — `tests/test_engine.py`
- **test_new_entry_after_last_entry_time_is_blocked()** (4 connections) — `tests/test_engine.py`
- **test_open_position_is_closed_if_a_days_data_ends_early()** (4 connections) — `tests/test_engine.py`
- **test_position_size_limit()** (4 connections) — `tests/test_engine.py`
- **test_short_signal_ignored_when_shorting_not_allowed()** (4 connections) — `tests/test_engine.py`
- **test_short_trade_profit()** (4 connections) — `tests/test_engine.py`
- **test_square_off_closes_at_the_open_of_the_square_off_bar()** (4 connections) — `tests/test_engine.py`
- **test_stop_loss_fills_at_stop_price()** (4 connections) — `tests/test_engine.py`
- **test_stop_wins_when_stop_and_target_are_both_inside_one_bar()** (4 connections) — `tests/test_engine.py`
- **test_target_has_no_slippage_but_stop_does()** (4 connections) — `tests/test_engine.py`
- **Shared helpers for building tiny, fully controlled test scenarios.** (1 connections) — `tests/helpers.py`
- **rows: list of (open, high, low, close) tuples.** (1 connections) — `tests/helpers.py`

## Relationships

- [Strategy Rule Engine (3)](Strategy_Rule_Engine_3.md) (10 shared connections)
- [Pivot Points & Price Levels](Pivot_Points_&_Price_Levels.md) (8 shared connections)
- [Technical Indicators Library](Technical_Indicators_Library.md) (3 shared connections)
- [App Configuration & Settings (3)](App_Configuration_&_Settings_3.md) (3 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (3 shared connections)
- [Strategy Rule Engine (4)](Strategy_Rule_Engine_4.md) (2 shared connections)
- [App Configuration & Settings (2)](App_Configuration_&_Settings_2.md) (2 shared connections)
- [Agent V2 Market Module](Agent_V2_Market_Module.md) (2 shared connections)
- [Helpers Scripted Module](Helpers_Scripted_Module.md) (2 shared connections)
- [Backtesting & Historical Execution (2)](Backtesting_&_Historical_Execution_2.md) (1 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (1 shared connections)
- [Conftest Synthetic User Module](Conftest_Synthetic_User_Module.md) (1 shared connections)

## Source Files

- `tests/helpers.py`
- `tests/test_engine.py`

## Audit Trail

- EXTRACTED: 114 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*