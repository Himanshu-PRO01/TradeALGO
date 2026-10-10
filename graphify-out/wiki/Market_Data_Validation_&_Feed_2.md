# Market Data Validation & Feed (2)

> 22 nodes

## Key Concepts

- **generate_sample_data()** (48 connections) — `algobot/data.py`
- **data.py** (26 connections) — `algobot/data.py`
- **15_Strategy_Scanner.py** (22 connections) — `pages/15_Strategy_Scanner.py`
- **test_dataquality.py** (14 connections) — `tests/test_dataquality.py`
- **data_quality_report()** (13 connections) — `algobot/dataquality.py`
- **format_data_quality()** (8 connections) — `algobot/dataquality.py`
- **messages()** (7 connections) — `tests/test_dataquality.py`
- **cmd_check_data()** (5 connections) — `algobot/cli.py`
- **_bar_minutes()** (4 connections) — `algobot/dataquality.py`
- **test_clean_sample_data_has_no_warnings()** (4 connections) — `tests/test_dataquality.py`
- **test_a_bad_tick_spike_is_found()** (3 connections) — `tests/test_dataquality.py`
- **test_a_day_with_far_too_few_bars_is_found()** (3 connections) — `tests/test_dataquality.py`
- **test_a_frozen_feed_is_found()** (3 connections) — `tests/test_dataquality.py`
- **test_bars_outside_the_session_and_on_weekends_are_found()** (3 connections) — `tests/test_dataquality.py`
- **test_missing_bars_inside_a_day_are_found()** (3 connections) — `tests/test_dataquality.py`
- **test_missing_volume_is_noted_not_alarmed()** (3 connections) — `tests/test_dataquality.py`
- **DataFrame** (3 connections)
- **Issue** (2 connections) — `algobot/dataquality.py`
- **time** (1 connections)
- **Market data: loading CSV files and generating synthetic test data. The…** (1 connections) — `algobot/data.py`
- **Random-walk intraday bars (default: 75 five-minute bars, 09:15 to 15:25).…** (1 connections) — `algobot/data.py`
- **Strategy Scanner: run a whole library of strategy templates against real (or…** (1 connections) — `pages/15_Strategy_Scanner.py`

## Relationships

- [CLI Parser & Commands (2)](CLI_Parser_&_Commands_2.md) (11 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (10 shared connections)
- [Market Data Validation & Feed (3)](Market_Data_Validation_&_Feed_3.md) (9 shared connections)
- [Strategy Rule Engine (2)](Strategy_Rule_Engine_2.md) (9 shared connections)
- [Monte Carlo Audit & Risk](Monte_Carlo_Audit_&_Risk.md) (5 shared connections)
- [CLI Parser & Commands (3)](CLI_Parser_&_Commands_3.md) (5 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (5 shared connections)
- [Agent V2 Market Module](Agent_V2_Market_Module.md) (4 shared connections)
- [Strategy Rule Engine (3)](Strategy_Rule_Engine_3.md) (4 shared connections)
- [Technical Indicators Library](Technical_Indicators_Library.md) (4 shared connections)
- [Backtesting & Historical Execution (3)](Backtesting_&_Historical_Execution_3.md) (3 shared connections)
- [Strategy Lab & Research](Strategy_Lab_&_Research.md) (3 shared connections)

## Source Files

- `algobot/cli.py`
- `algobot/data.py`
- `algobot/dataquality.py`
- `pages/15_Strategy_Scanner.py`
- `tests/test_dataquality.py`

## Audit Trail

- EXTRACTED: 134 (99%)
- INFERRED: 1 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*