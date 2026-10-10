# Strategy Rule Engine (9)

> 12 nodes

## Key Concepts

- **run_page_qa.py** (12 connections) — `qa/run_page_qa.py`
- **run_strategy_qa.py** (12 connections) — `qa/run_strategy_qa.py`
- **_common.py** (9 connections) — `qa/_common.py`
- **yaml** (7 connections)
- **load_prices()** (6 connections) — `qa/_common.py`
- **main()** (6 connections) — `qa/run_strategy_qa.py`
- **main()** (3 connections) — `qa/run_page_qa.py`
- **chk()** (1 connections) — `qa/run_strategy_qa.py`
- **Shared setup for the manual QA scripts: a realistic (fake) Nifty-like data file…** (1 connections) — `qa/_common.py`
- **Manual QA: drive the real Backtest page, then the Reality check page, with the…** (1 connections) — `qa/run_page_qa.py`
- **Manual QA: run a realistic (fake) opening-range-breakout strategy through the…** (1 connections) — `qa/run_strategy_qa.py`
- **warnings** (1 connections)

## Relationships

- [Agent V2 Market Module](Agent_V2_Market_Module.md) (6 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (5 shared connections)
- [Strategy Rule Engine (6)](Strategy_Rule_Engine_6.md) (3 shared connections)
- [Paper Trading Paperlog Module](Paper_Trading_Paperlog_Module.md) (3 shared connections)
- [Market Data Validation & Feed (3)](Market_Data_Validation_&_Feed_3.md) (2 shared connections)
- [App Configuration & Settings (2)](App_Configuration_&_Settings_2.md) (2 shared connections)
- [Market Data Validation & Feed (2)](Market_Data_Validation_&_Feed_2.md) (2 shared connections)
- [Conftest Synthetic User Module](Conftest_Synthetic_User_Module.md) (1 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (1 shared connections)
- [Backtesting & Historical Execution (3)](Backtesting_&_Historical_Execution_3.md) (1 shared connections)
- [App Configuration & Settings (3)](App_Configuration_&_Settings_3.md) (1 shared connections)
- [Backtesting & Historical Execution](Backtesting_&_Historical_Execution.md) (1 shared connections)

## Source Files

- `qa/_common.py`
- `qa/run_page_qa.py`
- `qa/run_strategy_qa.py`

## Audit Trail

- EXTRACTED: 44 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*