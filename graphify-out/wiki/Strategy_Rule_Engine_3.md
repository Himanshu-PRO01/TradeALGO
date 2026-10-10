# Strategy Rule Engine (3)

> 31 nodes

## Key Concepts

- **test_indicators_strategy.py** (47 connections) — `tests/test_indicators_strategy.py`
- **RuleStrategy** (16 connections) — `algobot/strategy.py`
- **evaluate_rule()** (14 connections) — `algobot/strategy.py`
- **add_prev_columns()** (10 connections) — `algobot/indicators.py`
- **normalize_rule_expression()** (10 connections) — `algobot/strategy.py`
- **DataFrame** (9 connections)
- **.prepare()** (5 connections) — `algobot/strategy.py`
- **test_dangerous_or_unsupported_rules_are_rejected()** (5 connections) — `tests/test_indicators_strategy.py`
- **test_evaluate_rule_executes_crossunder_with_cci_80()** (5 connections) — `tests/test_indicators_strategy.py`
- **test_parentheses_after_boolean_operator_do_not_trigger_function_call_error()** (5 connections) — `tests/test_indicators_strategy.py`
- **test_rule_expression_detects_a_crossover_with_prev_columns()** (5 connections) — `tests/test_indicators_strategy.py`
- **test_build_strategy_unknown_name()** (4 connections) — `tests/test_indicators_strategy.py`
- **test_unknown_column_and_non_boolean_rules_are_rejected()** (4 connections) — `tests/test_indicators_strategy.py`
- **.on_bar()** (3 connections) — `algobot/strategy.py`
- **.prepare()** (3 connections) — `algobot/strategy.py`
- **test_prev_columns_are_shifted_by_one_bar()** (3 connections) — `tests/test_indicators_strategy.py`
- **test_rules_strategy_needs_at_least_one_rule_and_rejects_typos()** (3 connections) — `tests/test_indicators_strategy.py`
- **test_rules_strategy_signals_follow_position_state()** (3 connections) — `tests/test_indicators_strategy.py`
- **test_strategy_signals_do_not_change_when_future_bars_are_added()** (3 connections) — `tests/test_indicators_strategy.py`
- **.on_bar()** (2 connections) — `algobot/strategy.py`
- **test_crossover_and_crossunder_syntax_normalization()** (2 connections) — `tests/test_indicators_strategy.py`
- **_cross_sub()** (1 connections) — `algobot/strategy.py`
- **_crossover_sub()** (1 connections) — `algobot/strategy.py`
- **_crossunder_sub()** (1 connections) — `algobot/strategy.py`
- **parametrize** (1 connections)
- *... and 6 more nodes in this community*

## Relationships

- [Technical Indicators Library](Technical_Indicators_Library.md) (22 shared connections)
- [Strategy Rule Engine (4)](Strategy_Rule_Engine_4.md) (17 shared connections)
- [Engine Helpers Make Module](Engine_Helpers_Make_Module.md) (10 shared connections)
- [CLI Parser & Commands (2)](CLI_Parser_&_Commands_2.md) (7 shared connections)
- [Market Data Validation & Feed (2)](Market_Data_Validation_&_Feed_2.md) (4 shared connections)
- [Backtesting & Historical Execution (2)](Backtesting_&_Historical_Execution_2.md) (3 shared connections)
- [Pivot Points & Price Levels](Pivot_Points_&_Price_Levels.md) (2 shared connections)
- [Agent V2 Market Module](Agent_V2_Market_Module.md) (2 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (2 shared connections)
- [App Configuration & Settings](App_Configuration_&_Settings.md) (1 shared connections)
- [Strategy Rule Engine (6)](Strategy_Rule_Engine_6.md) (1 shared connections)
- [Ai Provider Generate Module (2)](Ai_Provider_Generate_Module_2.md) (1 shared connections)

## Source Files

- `algobot/indicators.py`
- `algobot/strategy.py`
- `tests/test_indicators_strategy.py`

## Audit Trail

- EXTRACTED: 114 (93%)
- INFERRED: 9 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*