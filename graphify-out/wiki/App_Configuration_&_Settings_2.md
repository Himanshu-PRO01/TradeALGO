# App Configuration & Settings (2)

> 17 nodes

## Key Concepts

- **validate_config()** (69 connections) — `algobot/config.py`
- **_merge()** (6 connections) — `algobot/config.py`
- **parse_time()** (6 connections) — `algobot/config.py`
- **_non_negative()** (4 connections) — `algobot/config.py`
- **_positive_or_none()** (4 connections) — `algobot/config.py`
- **test_times_must_be_in_order()** (3 connections) — `tests/test_costs_and_config.py`
- **test_typo_in_setting_name_is_rejected_with_the_name_in_the_message()** (3 connections) — `tests/test_costs_and_config.py`
- **test_run_lookahead_checks_on_a_validated_config()** (3 connections) — `tests/test_explain_lookahead.py`
- **Any** (3 connections)
- **cfg()** (2 connections) — `tests/test_audit.py`
- **test_empty_config_uses_defaults()** (2 connections) — `tests/test_costs_and_config.py`
- **test_unquoted_yaml_time_still_works()** (2 connections) — `tests/test_costs_and_config.py`
- **_rules_cfg()** (2 connections) — `tests/test_explain_lookahead.py`
- **time** (1 connections)
- **Merge the user's settings over the defaults and check every value.** (1 connections) — `algobot/config.py`
- **Recursively merge `override` into a copy of `base`, rejecting unknown keys.** (1 connections) — `algobot/config.py`
- **Parse "HH:MM" (or HH:MM:SS) into a time. YAML quirk: an unquoted 09:20 is read…** (1 connections) — `algobot/config.py`

## Relationships

- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (14 shared connections)
- [CLI Parser & Commands (2)](CLI_Parser_&_Commands_2.md) (7 shared connections)
- [App Configuration & Settings (3)](App_Configuration_&_Settings_3.md) (6 shared connections)
- [App Configuration & Settings](App_Configuration_&_Settings.md) (6 shared connections)
- [App Configuration & Settings (4)](App_Configuration_&_Settings_4.md) (5 shared connections)
- [Monte Carlo Audit & Risk](Monte_Carlo_Audit_&_Risk.md) (5 shared connections)
- [Strategy Rule Engine (2)](Strategy_Rule_Engine_2.md) (4 shared connections)
- [Agent V2 Market Module](Agent_V2_Market_Module.md) (4 shared connections)
- [Strategy Lab & Research](Strategy_Lab_&_Research.md) (4 shared connections)
- [Backtesting & Historical Execution](Backtesting_&_Historical_Execution.md) (3 shared connections)
- [Agent Market Fetch Module](Agent_Market_Fetch_Module.md) (2 shared connections)
- [Strategy Rule Engine (9)](Strategy_Rule_Engine_9.md) (2 shared connections)

## Source Files

- `algobot/config.py`
- `tests/test_audit.py`
- `tests/test_costs_and_config.py`
- `tests/test_explain_lookahead.py`

## Audit Trail

- EXTRACTED: 92 (98%)
- INFERRED: 2 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*