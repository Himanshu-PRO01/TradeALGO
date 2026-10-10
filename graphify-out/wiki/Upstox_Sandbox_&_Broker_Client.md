# Upstox Sandbox & Broker Client

> 60 nodes

## Key Concepts

- **26_Tick_Engine.py** (22 connections) — `pages/26_Tick_Engine.py`
- **UpstoxMarketData** (17 connections) — `algobot/upstox_market_data.py`
- **tick_engine.py** (14 connections) — `algobot/tick_engine.py`
- **UpstoxOptionContracts** (13 connections) — `algobot/upstox_option_contracts.py`
- **run_tick_strategy()** (12 connections) — `algobot/tick_engine.py`
- **upstox_market_data.py** (12 connections) — `algobot/upstox_market_data.py`
- **upstox_option_contracts.py** (11 connections) — `algobot/upstox_option_contracts.py`
- **test_upstox_option_contracts.py** (9 connections) — `tests/test_upstox_option_contracts.py`
- **MarketTick** (6 connections) — `algobot/upstox_market_data.py`
- **OptionContractRef** (6 connections) — `algobot/upstox_option_contracts.py`
- **_find_option_columns()** (6 connections) — `algobot/tick_engine.py`
- **load_tick_csv()** (6 connections) — `algobot/tick_engine.py`
- **._extract_tick()** (6 connections) — `algobot/upstox_market_data.py`
- **test_tick_engine.py** (6 connections) — `tests/test_tick_engine.py`
- **TickContract** (4 connections) — `algobot/tick_engine.py`
- **threading** (4 connections)
- **_nearest_strike()** (3 connections) — `algobot/tick_engine.py`
- **._on_message()** (3 connections) — `algobot/upstox_market_data.py`
- **.fetch()** (3 connections) — `algobot/upstox_option_contracts.py`
- **.nearest_strike()** (3 connections) — `algobot/upstox_option_contracts.py`
- **get_upstox_feed()** (3 connections) — `pages/26_Tick_Engine.py`
- **test_tick_engine_selects_pe_independently()** (3 connections) — `tests/test_tick_engine.py`
- **test_tick_trigger_rolls_without_waiting_for_candle_close()** (3 connections) — `tests/test_tick_engine.py`
- **_ticks()** (3 connections) — `tests/test_tick_engine.py`
- **test_by_strike_filters_side()** (3 connections) — `tests/test_upstox_option_contracts.py`
- *... and 35 more nodes in this community*

## Relationships

- [CLI Parser & Commands (2)](CLI_Parser_&_Commands_2.md) (14 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (7 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (7 shared connections)
- [Database & Persistence Layer](Database_&_Persistence_Layer.md) (3 shared connections)
- [Market Data Validation & Feed (2)](Market_Data_Validation_&_Feed_2.md) (2 shared connections)
- [Options Pricing & Greeks (2)](Options_Pricing_&_Greeks_2.md) (2 shared connections)
- [App Configuration & Settings](App_Configuration_&_Settings.md) (1 shared connections)
- [Paper Trading Daemon Module](Paper_Trading_Daemon_Module.md) (1 shared connections)
- [Agent Market Fetch Module](Agent_Market_Fetch_Module.md) (1 shared connections)
- [Execution Live Policy Module](Execution_Live_Policy_Module.md) (1 shared connections)
- [Backtesting & Historical Execution](Backtesting_&_Historical_Execution.md) (1 shared connections)
- [Streamlit UI Components](Streamlit_UI_Components.md) (1 shared connections)

## Source Files

- `algobot/tick_engine.py`
- `algobot/upstox_market_data.py`
- `algobot/upstox_option_contracts.py`
- `pages/26_Tick_Engine.py`
- `tests/test_tick_engine.py`
- `tests/test_upstox_market_data.py`
- `tests/test_upstox_option_contracts.py`

## Audit Trail

- EXTRACTED: 135 (96%)
- INFERRED: 6 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*