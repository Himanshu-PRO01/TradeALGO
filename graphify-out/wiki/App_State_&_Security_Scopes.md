# App State & Security Scopes

> 30 nodes

## Key Concepts

- **appstate.py** (44 connections) — `algobot/appstate.py`
- **1_Position_size.py** (12 connections) — `pages/1_Position_size.py`
- **6_Reality_check.py** (12 connections) — `pages/6_Reality_check.py`
- **is_hosted()** (10 connections) — `algobot/appstate.py`
- **fix_password_autocomplete()** (8 connections) — `algobot/dom_fixups.py`
- **journal_scope()** (6 connections) — `algobot/appstate.py`
- **paper_scope()** (6 connections) — `algobot/appstate.py`
- **password_gate()** (6 connections) — `algobot/appstate.py`
- **strategies_scope()** (6 connections) — `algobot/appstate.py`
- **experiments_scope()** (5 connections) — `algobot/appstate.py`
- **dom_fixups.py** (5 connections) — `algobot/dom_fixups.py`
- **rehearsal_scope()** (4 connections) — `algobot/appstate.py`
- **test_dom_fixups.py** (4 connections) — `tests/test_dom_fixups.py`
- **configured_password()** (3 connections) — `algobot/appstate.py`
- **_secret()** (3 connections) — `algobot/appstate.py`
- **storage_note()** (3 connections) — `algobot/appstate.py`
- **test_fix_password_autocomplete_runs_without_error()** (3 connections) — `tests/test_dom_fixups.py`
- **Where the app keeps its data, and who may look at it. Two ways to run it: LOCAL…** (1 connections) — `algobot/appstate.py`
- **The journal for this visitor: a file locally, or an in-session store when…** (1 connections) — `algobot/appstate.py`
- **Also global and persistent, like the kill switch: if this state were scoped per…** (1 connections) — `algobot/appstate.py`
- **The paper-trading log for this visitor: a file locally, or an in-session store…** (1 connections) — `algobot/appstate.py`
- **Saved strategy/backtest library: per-user in hosted mode, local file otherwise.** (1 connections) — `algobot/appstate.py`
- **Render the branded TradeALGO login when a hosted secret is configured.** (1 connections) — `algobot/appstate.py`
- **Tiny, dependency-free DOM fixups for things Streamlit's widgets don't expose…** (1 connections) — `algobot/dom_fixups.py`
- **Chrome/Lighthouse flags "Incorrect use of autocomplete attribute" on any <input…** (1 connections) — `algobot/dom_fixups.py`
- *... and 5 more nodes in this community*

## Relationships

- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (20 shared connections)
- [Streamlit UI Components](Streamlit_UI_Components.md) (7 shared connections)
- [Trade Journal & Reporting](Trade_Journal_&_Reporting.md) (6 shared connections)
- [Paper Trading Paperlog Module](Paper_Trading_Paperlog_Module.md) (5 shared connections)
- [Backtesting & Historical Execution (3)](Backtesting_&_Historical_Execution_3.md) (3 shared connections)
- [Database & Persistence Layer](Database_&_Persistence_Layer.md) (3 shared connections)
- [Strategy Rule Engine (8)](Strategy_Rule_Engine_8.md) (3 shared connections)
- [App State & Security Scopes (2)](App_State_&_Security_Scopes_2.md) (3 shared connections)
- [Sizing Size Format Module](Sizing_Size_Format_Module.md) (3 shared connections)
- [Monte Carlo Audit & Risk (2)](Monte_Carlo_Audit_&_Risk_2.md) (3 shared connections)
- [CLI Parser & Commands (6)](CLI_Parser_&_Commands_6.md) (2 shared connections)
- [Interactive Practice Simulator (4)](Interactive_Practice_Simulator_4.md) (2 shared connections)

## Source Files

- `algobot/appstate.py`
- `algobot/dom_fixups.py`
- `pages/1_Position_size.py`
- `pages/6_Reality_check.py`
- `tests/test_dom_fixups.py`

## Audit Trail

- EXTRACTED: 106 (95%)
- INFERRED: 5 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*