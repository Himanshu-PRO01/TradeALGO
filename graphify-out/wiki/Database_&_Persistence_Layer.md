# Database & Persistence Layer

> 76 nodes

## Key Concepts

- **typing** (36 connections)
- **upstox_sandbox.py** (22 connections) — `algobot/upstox_sandbox.py`
- **test_sandbox_rehearsal.py** (22 connections) — `tests/test_sandbox_rehearsal.py`
- **UpstoxSandboxError** (18 connections) — `algobot/upstox_sandbox.py`
- **test_upstox_sandbox.py** (18 connections) — `tests/test_upstox_sandbox.py`
- **RehearsalLog** (17 connections) — `algobot/sandbox_rehearsal.py`
- **UpstoxSandboxClient** (16 connections) — `algobot/upstox_sandbox.py`
- **sandbox_rehearsal.py** (14 connections) — `algobot/sandbox_rehearsal.py`
- **step()** (13 connections) — `algobot/sandbox_rehearsal.py`
- **test_concurrent_refreshes_place_exactly_one_entry_order()** (9 connections) — `tests/test_sandbox_rehearsal.py`
- **FakeClient** (8 connections) — `tests/test_sandbox_rehearsal.py`
- **Fake** (8 connections) — `tests/test_upstox_sandbox.py`
- **clean_token()** (8 connections) — `algobot/upstox_sandbox.py`
- **_sdk_order_api()** (8 connections) — `algobot/upstox_sandbox.py`
- **test_rehearsal_does_not_reenter_the_same_still_open_position()** (7 connections) — `tests/test_sandbox_rehearsal.py`
- **test_rehearsal_flips_flat_to_open_on_a_real_entry_signal()** (7 connections) — `tests/test_sandbox_rehearsal.py`
- **SlowFakeClient** (6 connections) — `tests/test_sandbox_rehearsal.py`
- **_post()** (6 connections) — `algobot/upstox_sandbox.py`
- **sandbox_token()** (6 connections) — `algobot/upstox_sandbox.py`
- **_sdk_error()** (6 connections) — `algobot/upstox_sandbox.py`
- **.cancel_order()** (6 connections) — `algobot/upstox_sandbox.py`
- **.modify_order()** (6 connections) — `algobot/upstox_sandbox.py`
- **.place_order()** (6 connections) — `algobot/upstox_sandbox.py`
- **test_rehearsal_stays_flat_with_no_open_signal()** (6 connections) — `tests/test_sandbox_rehearsal.py`
- **client()** (6 connections) — `tests/test_upstox_sandbox.py`
- *... and 51 more nodes in this community*

## Relationships

- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (18 shared connections)
- [Paper Trading Paperlog Module](Paper_Trading_Paperlog_Module.md) (13 shared connections)
- [Interactive Practice Simulator (4)](Interactive_Practice_Simulator_4.md) (5 shared connections)
- [App State & Security Scopes](App_State_&_Security_Scopes.md) (3 shared connections)
- [Whatsapp Alerts Check Module](Whatsapp_Alerts_Check_Module.md) (3 shared connections)
- [Upstox Sandbox & Broker Client](Upstox_Sandbox_&_Broker_Client.md) (3 shared connections)
- [Execution Live Policy Module](Execution_Live_Policy_Module.md) (2 shared connections)
- [App State & Security Scopes (2)](App_State_&_Security_Scopes_2.md) (2 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (2 shared connections)
- [Ai Provider Match Module](Ai_Provider_Match_Module.md) (2 shared connections)
- [Paper Trading Daemon Module](Paper_Trading_Daemon_Module.md) (2 shared connections)
- [Strategy Rule Engine (2)](Strategy_Rule_Engine_2.md) (2 shared connections)

## Source Files

- `algobot/sandbox_rehearsal.py`
- `algobot/upstox_sandbox.py`
- `tests/test_sandbox_rehearsal.py`
- `tests/test_upstox_sandbox.py`

## Audit Trail

- EXTRACTED: 224 (97%)
- INFERRED: 7 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*