# Market Data Validation & Feed (3)

> 13 nodes

## Key Concepts

- **load_csv()** (23 connections) — `algobot/data.py`
- **test_data_metrics_integration.py** (22 connections) — `tests/test_data_metrics_integration.py`
- **DataError** (15 connections) — `algobot/data.py`
- **test_demo_configs_run_end_to_end_and_the_books_balance()** (6 connections) — `tests/test_data_metrics_integration.py`
- **test_load_csv_rejects_bad_data()** (5 connections) — `tests/test_data_metrics_integration.py`
- **test_load_csv_accepts_common_layout_and_optional_volume()** (3 connections) — `tests/test_data_metrics_integration.py`
- **test_missing_file_gives_friendly_error()** (3 connections) — `tests/test_data_metrics_integration.py`
- **_write()** (3 connections) — `tests/test_data_metrics_integration.py`
- **test_sample_data_is_valid_reproducible_and_intraday()** (2 connections) — `tests/test_data_metrics_integration.py`
- **parametrize** (2 connections)
- **ValueError** (1 connections)
- **Raised when a data file has a problem the user should fix.** (1 connections) — `algobot/data.py`
- **Load OHLCV bars from a CSV file. Needed columns: a time column (datetime /…** (1 connections) — `algobot/data.py`

## Relationships

- [Market Data Validation & Feed (2)](Market_Data_Validation_&_Feed_2.md) (9 shared connections)
- [CLI Parser & Commands (2)](CLI_Parser_&_Commands_2.md) (4 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (4 shared connections)
- [Agent V2 Market Module](Agent_V2_Market_Module.md) (4 shared connections)
- [Strategy Lab & Research](Strategy_Lab_&_Research.md) (3 shared connections)
- [Backtesting & Historical Execution (3)](Backtesting_&_Historical_Execution_3.md) (3 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (3 shared connections)
- [Performance Metrics & Ratios](Performance_Metrics_&_Ratios.md) (3 shared connections)
- [Strategy Rule Engine (9)](Strategy_Rule_Engine_9.md) (2 shared connections)
- [Paper Trading Paperlog Module](Paper_Trading_Paperlog_Module.md) (2 shared connections)
- [Trade Gate & Pre-Check](Trade_Gate_&_Pre-Check.md) (2 shared connections)
- [Openalgo Bridge History Module](Openalgo_Bridge_History_Module.md) (1 shared connections)

## Source Files

- `algobot/data.py`
- `tests/test_data_metrics_integration.py`

## Audit Trail

- EXTRACTED: 62 (94%)
- INFERRED: 4 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*