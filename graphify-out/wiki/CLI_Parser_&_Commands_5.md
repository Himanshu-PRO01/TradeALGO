# CLI Parser & Commands (5)

> 12 nodes

## Key Concepts

- **live_chart.py** (15 connections) — `algobot/live_chart.py`
- **_fetch()** (7 connections) — `algobot/live_chart.py`
- **fetch_candles()** (7 connections) — `algobot/live_chart.py`
- **openalgo_configured()** (4 connections) — `algobot/live_chart.py`
- **_secret()** (4 connections) — `algobot/live_chart.py`
- **_client()** (3 connections) — `algobot/live_chart.py`
- **DataFrame** (2 connections)
- **cache_data** (1 connections)
- **Real NSE candles for the dashboard's main chart, sourced from the operator's…** (1 connections) — `algobot/live_chart.py`
- **True once the operator has set an OpenAlgo API key (.env locally, or a…** (1 connections) — `algobot/live_chart.py`
- **Cached for a minute so switching timeframes doesn't hammer the broker's API on…** (1 connections) — `algobot/live_chart.py`
- **Real candles for a dashboard symbol/interval, or (None, a human-readable reason…** (1 connections) — `algobot/live_chart.py`

## Relationships

- [CLI Parser & Commands](CLI_Parser_&_Commands.md) (5 shared connections)
- [Openalgo Bridge History Module](Openalgo_Bridge_History_Module.md) (3 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (2 shared connections)
- [Execution Live Policy Module](Execution_Live_Policy_Module.md) (1 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (1 shared connections)
- [Database & Persistence Layer](Database_&_Persistence_Layer.md) (1 shared connections)

## Source Files

- `algobot/live_chart.py`

## Audit Trail

- EXTRACTED: 28 (93%)
- INFERRED: 2 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*