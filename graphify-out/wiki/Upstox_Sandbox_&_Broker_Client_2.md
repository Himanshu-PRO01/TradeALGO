# Upstox Sandbox & Broker Client (2)

> 18 nodes

## Key Concepts

- **UpstoxBODResolver** (13 connections) — `algobot/upstox_bod_instruments.py`
- **upstox_bod_instruments.py** (13 connections) — `algobot/upstox_bod_instruments.py`
- **._download()** (5 connections) — `algobot/upstox_bod_instruments.py`
- **._expiry()** (5 connections) — `algobot/upstox_bod_instruments.py`
- **.find_options()** (5 connections) — `algobot/upstox_bod_instruments.py`
- **test_upstox_bod_instruments.py** (5 connections) — `tests/test_upstox_bod_instruments.py`
- **.expiries()** (3 connections) — `algobot/upstox_bod_instruments.py`
- **_nifty_option_contracts()** (3 connections) — `pages/14_Upstox_Sandbox.py`
- **_nifty_option_expiries()** (3 connections) — `pages/14_Upstox_Sandbox.py`
- **test_expiry_normalizes_epoch_milliseconds()** (3 connections) — `tests/test_upstox_bod_instruments.py`
- **InstrumentRef** (2 connections) — `algobot/upstox_bod_instruments.py`
- **test_find_options_filters_nifty_contracts()** (2 connections) — `tests/test_upstox_bod_instruments.py`
- **Any** (2 connections)
- **cache_data** (2 connections)
- **unittest_mock** (2 connections)
- **.__init__()** (1 connections) — `algobot/upstox_bod_instruments.py`
- **Read-only Upstox BOD instrument lookup for sandbox order forms. The sandbox…** (1 connections) — `algobot/upstox_bod_instruments.py`
- **gzip** (1 connections)

## Relationships

- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (5 shared connections)
- [CLI Parser & Commands (2)](CLI_Parser_&_Commands_2.md) (4 shared connections)
- [Ai Provider Match Module](Ai_Provider_Match_Module.md) (1 shared connections)
- [Agent Market Fetch Module](Agent_Market_Fetch_Module.md) (1 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (1 shared connections)
- [Execution Live Policy Module](Execution_Live_Policy_Module.md) (1 shared connections)
- [Database & Persistence Layer](Database_&_Persistence_Layer.md) (1 shared connections)
- [Upstox Sandbox & Broker Client](Upstox_Sandbox_&_Broker_Client.md) (1 shared connections)

## Source Files

- `algobot/upstox_bod_instruments.py`
- `pages/14_Upstox_Sandbox.py`
- `tests/test_upstox_bod_instruments.py`

## Audit Trail

- EXTRACTED: 39 (91%)
- INFERRED: 4 (9%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*