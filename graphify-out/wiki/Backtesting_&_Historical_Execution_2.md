# Backtesting & Historical Execution (2)

> 19 nodes

## Key Concepts

- **Strategy** (20 connections) — `algobot/strategy.py`
- **Backtester** (15 connections) — `algobot/engine.py`
- **.run()** (9 connections) — `algobot/engine.py`
- **RandomEntry** (8 connections) — `algobot/audit.py`
- **._execute()** (5 connections) — `algobot/engine.py`
- **.__init__()** (5 connections) — `algobot/engine.py`
- **._exit()** (4 connections) — `algobot/engine.py`
- **.__init__()** (3 connections) — `algobot/audit.py`
- **._check_stop_target()** (3 connections) — `algobot/engine.py`
- **._enter()** (3 connections) — `algobot/engine.py`
- **._reset_state()** (3 connections) — `algobot/engine.py`
- **._try_enter()** (3 connections) — `algobot/engine.py`
- **.on_bar()** (2 connections) — `algobot/audit.py`
- **test_random_entry_benchmark_holds_for_a_fixed_number_of_bars()** (2 connections) — `tests/test_audit.py`
- **DataFrame** (2 connections)
- **.__init__()** (1 connections) — `algobot/strategy.py`
- **Benchmark: enters at random, exits after a fixed number of bars (or at the…** (1 connections) — `algobot/audit.py`
- **Carry out last bar's decision at this bar's open.** (1 connections) — `algobot/engine.py`
- **Base class. Subclass it and register it with @register("name").** (1 connections) — `algobot/strategy.py`

## Relationships

- [Monte Carlo Audit & Risk (2)](Monte_Carlo_Audit_&_Risk_2.md) (7 shared connections)
- [Agent V2 Market Module](Agent_V2_Market_Module.md) (4 shared connections)
- [Strategy Rule Engine (4)](Strategy_Rule_Engine_4.md) (4 shared connections)
- [Risk Management & Drawdown](Risk_Management_&_Drawdown.md) (3 shared connections)
- [Strategy Rule Engine (6)](Strategy_Rule_Engine_6.md) (3 shared connections)
- [Strategy Rule Engine (3)](Strategy_Rule_Engine_3.md) (3 shared connections)
- [Monte Carlo Audit & Risk](Monte_Carlo_Audit_&_Risk.md) (2 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (2 shared connections)
- [App Configuration & Settings (3)](App_Configuration_&_Settings_3.md) (2 shared connections)
- [Engine Helpers Make Module](Engine_Helpers_Make_Module.md) (1 shared connections)
- [Helpers Scripted Module](Helpers_Scripted_Module.md) (1 shared connections)
- [Performance Metrics & Ratios](Performance_Metrics_&_Ratios.md) (1 shared connections)

## Source Files

- `algobot/audit.py`
- `algobot/engine.py`
- `algobot/strategy.py`
- `tests/test_audit.py`

## Audit Trail

- EXTRACTED: 56 (90%)
- INFERRED: 6 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*