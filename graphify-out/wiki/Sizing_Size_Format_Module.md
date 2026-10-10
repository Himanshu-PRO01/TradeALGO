# Sizing Size Format Module

> 18 nodes

## Key Concepts

- **option_position_size()** (20 connections) — `algobot/sizing.py`
- **test_sizing.py** (14 connections) — `tests/test_sizing.py`
- **sizing.py** (13 connections) — `algobot/sizing.py`
- **format_size()** (7 connections) — `algobot/sizing.py`
- **SizeResult** (5 connections) — `algobot/sizing.py`
- **test_bad_inputs_are_rejected()** (3 connections) — `tests/test_sizing.py`
- **test_format_is_readable()** (3 connections) — `tests/test_sizing.py`
- **test_charges_reduce_the_loss_budget()** (2 connections) — `tests/test_sizing.py`
- **test_heavy_use_of_capital_is_flagged()** (2 connections) — `tests/test_sizing.py`
- **test_high_risk_percentage_is_flagged_with_simple_arithmetic()** (2 connections) — `tests/test_sizing.py`
- **test_lots_limited_by_capital_and_it_says_so()** (2 connections) — `tests/test_sizing.py`
- **test_lots_limited_by_the_loss_limit()** (2 connections) — `tests/test_sizing.py`
- **test_zero_lots_when_one_lot_costs_more_than_capital()** (2 connections) — `tests/test_sizing.py`
- **test_zero_lots_when_stop_is_too_wide_and_the_message_gives_the_fix()** (2 connections) — `tests/test_sizing.py`
- **test_default_nifty_lot_size_is_65()** (1 connections) — `tests/test_sizing.py`
- **parametrize** (1 connections)
- **Position sizing for BOUGHT options, from a maximum loss per trade. The question…** (1 connections) — `algobot/sizing.py`
- **Lots allowed for a bought option. est_charges: your broker's estimate of round-…** (1 connections) — `algobot/sizing.py`

## Relationships

- [Trade Gate & Pre-Check](Trade_Gate_&_Pre-Check.md) (5 shared connections)
- [CLI Parser & Commands (2)](CLI_Parser_&_Commands_2.md) (5 shared connections)
- [App State & Security Scopes](App_State_&_Security_Scopes.md) (3 shared connections)
- [Interactive Practice Simulator](Interactive_Practice_Simulator.md) (2 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (2 shared connections)
- [Interactive Practice Simulator (2)](Interactive_Practice_Simulator_2.md) (1 shared connections)
- [Interactive Practice Simulator (4)](Interactive_Practice_Simulator_4.md) (1 shared connections)
- [Options Pricing & Greeks](Options_Pricing_&_Greeks.md) (1 shared connections)
- [Conftest Synthetic User Module](Conftest_Synthetic_User_Module.md) (1 shared connections)

## Source Files

- `algobot/sizing.py`
- `tests/test_sizing.py`

## Audit Trail

- EXTRACTED: 51 (98%)
- INFERRED: 1 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*