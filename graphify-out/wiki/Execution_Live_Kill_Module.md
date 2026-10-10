# Execution Live Kill Module

> 28 nodes

## Key Concepts

- **test_live_execution.py** (23 connections) — `tests/test_live_execution.py`
- **KillSwitch** (20 connections) — `algobot/kill_switch.py`
- **LiveExecutionService** (16 connections) — `algobot/live_execution.py`
- **FakeClient** (10 connections) — `tests/test_live_execution.py`
- **request()** (8 connections) — `tests/test_live_execution.py`
- **risk()** (8 connections) — `tests/test_live_execution.py`
- **test_kill_switch_blocks_order()** (8 connections) — `tests/test_live_execution.py`
- **test_risk_manager_blocks_new_buy()** (8 connections) — `tests/test_live_execution.py`
- **test_risk_rejects_buy_outside_entry_window()** (8 connections) — `tests/test_live_execution.py`
- **enable_test_execution_policy()** (7 connections) — `tests/test_live_execution.py`
- **test_confirmation_is_required()** (7 connections) — `tests/test_live_execution.py`
- **test_sell_exit_is_allowed_after_new_entries_close()** (7 connections) — `tests/test_live_execution.py`
- **test_successful_buy_registers_one_entry()** (7 connections) — `tests/test_live_execution.py`
- **.__init__()** (4 connections) — `algobot/live_execution.py`
- **.history()** (2 connections) — `algobot/kill_switch.py`
- **.status()** (2 connections) — `algobot/kill_switch.py`
- **.close_db()** (1 connections) — `algobot/kill_switch.py`
- **.halt()** (1 connections) — `algobot/kill_switch.py`
- **.__init__()** (1 connections) — `algobot/kill_switch.py`
- **.resume()** (1 connections) — `algobot/kill_switch.py`
- **.execution_enabled()** (1 connections) — `tests/test_live_execution.py`
- **.__init__()** (1 connections) — `tests/test_live_execution.py`
- **.place_order()** (1 connections) — `tests/test_live_execution.py`
- **test_live_policy_remains_disabled_by_default()** (1 connections) — `tests/test_live_execution.py`
- **DataFrame** (1 connections)
- *... and 3 more nodes in this community*

## Relationships

- [Execution Live Policy Module](Execution_Live_Policy_Module.md) (13 shared connections)
- [CLI Parser & Commands](CLI_Parser_&_Commands.md) (8 shared connections)
- [Risk Management & Drawdown](Risk_Management_&_Drawdown.md) (4 shared connections)
- [App State & Security Scopes](App_State_&_Security_Scopes.md) (1 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (1 shared connections)
- [Conftest Synthetic User Module](Conftest_Synthetic_User_Module.md) (1 shared connections)
- [Openalgo Bridge History Module](Openalgo_Bridge_History_Module.md) (1 shared connections)

## Source Files

- `algobot/kill_switch.py`
- `algobot/live_execution.py`
- `tests/test_live_execution.py`

## Audit Trail

- EXTRACTED: 84 (90%)
- INFERRED: 9 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*