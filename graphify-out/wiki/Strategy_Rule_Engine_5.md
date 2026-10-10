# Strategy Rule Engine (5)

> 25 nodes

## Key Concepts

- **StrategyVersionStore** (16 connections) — `algobot/strategy_versions.py`
- **strategy_versions.py** (12 connections) — `algobot/strategy_versions.py`
- **VersionError** (9 connections) — `algobot/strategy_versions.py`
- **VersionRecord** (9 connections) — `algobot/strategy_versions.py`
- **.get()** (9 connections) — `algobot/strategy_versions.py`
- **.create_original()** (6 connections) — `algobot/strategy_versions.py`
- **_row_to_record()** (5 connections) — `algobot/strategy_versions.py`
- **.create_ai_candidate()** (5 connections) — `algobot/strategy_versions.py`
- **.approve()** (4 connections) — `algobot/strategy_versions.py`
- **.list_versions()** (4 connections) — `algobot/strategy_versions.py`
- **.reject()** (4 connections) — `algobot/strategy_versions.py`
- **_now()** (3 connections) — `algobot/strategy_versions.py`
- **.diff()** (3 connections) — `algobot/strategy_versions.py`
- **.get_active()** (3 connections) — `algobot/strategy_versions.py`
- **.record_backtest()** (3 connections) — `algobot/strategy_versions.py`
- **.get_rewrite_enabled()** (2 connections) — `algobot/strategy_versions.py`
- **._original_label()** (2 connections) — `algobot/strategy_versions.py`
- **.close_db()** (1 connections) — `algobot/strategy_versions.py`
- **.__init__()** (1 connections) — `algobot/strategy_versions.py`
- **.set_rewrite_enabled()** (1 connections) — `algobot/strategy_versions.py`
- **.is_active_candidate()** (1 connections) — `algobot/strategy_versions.py`
- **ValueError** (1 connections)
- **Row** (1 connections)
- **Strategy version history: an original rule set plus AI-drafted candidates. The…** (1 connections) — `algobot/strategy_versions.py`
- **A version-history operation was asked to do something inconsistent.** (1 connections) — `algobot/strategy_versions.py`

## Relationships

- [Strategy Rule Engine](Strategy_Rule_Engine.md) (2 shared connections)
- [Execution Live Policy Module](Execution_Live_Policy_Module.md) (1 shared connections)
- [Ai Provider Match Module](Ai_Provider_Match_Module.md) (1 shared connections)
- [App State & Security Scopes (2)](App_State_&_Security_Scopes_2.md) (1 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (1 shared connections)
- [Database & Persistence Layer](Database_&_Persistence_Layer.md) (1 shared connections)

## Source Files

- `algobot/strategy_versions.py`

## Audit Trail

- EXTRACTED: 57 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*