# Execution Live Policy Module

> 20 nodes

## Key Concepts

- **datetime** (37 connections)
- **live_execution.py** (16 connections) — `algobot/live_execution.py`
- **execution_policy.py** (9 connections) — `algobot/execution_policy.py`
- **kill_switch.py** (9 connections) — `algobot/kill_switch.py`
- **.place()** (7 connections) — `algobot/live_execution.py`
- **risk.py** (7 connections) — `algobot/risk.py`
- **11_Live_Trading.py** (6 connections) — `pages/11_Live_Trading.py`
- **live_trading_allowed()** (5 connections) — `algobot/execution_policy.py`
- **ExecutionRequest** (4 connections) — `algobot/live_execution.py`
- **require_live_disabled()** (4 connections) — `algobot/execution_policy.py`
- **test_execution_policy.py** (4 connections) — `tests/test_execution_policy.py`
- **test_live_trading_is_hard_disabled()** (3 connections) — `tests/test_execution_policy.py`
- **._explicit_live_confirmation()** (2 connections) — `algobot/live_execution.py`
- **datetime** (2 connections)
- **Execution safety policy. Live trading is deliberately prohibited in this build.…** (1 connections) — `algobot/execution_policy.py`
- **A persistent, human-operable kill switch. This is independent of the per-run…** (1 connections) — `algobot/kill_switch.py`
- **Single live-execution boundary for TradeALGO. TradeALGO owns signals and risk;…** (1 connections) — `algobot/live_execution.py`
- **Place exactly one live order request; never retries it.** (1 connections) — `algobot/live_execution.py`
- **Risk rules that sit between the strategy and the market. The strategy can ask…** (1 connections) — `algobot/risk.py`
- **Live trading control page. Execution stays disabled until the system is…** (1 connections) — `pages/11_Live_Trading.py`

## Relationships

- [Execution Live Kill Module](Execution_Live_Kill_Module.md) (13 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (4 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (4 shared connections)
- [Paper Trading Daemon Module](Paper_Trading_Daemon_Module.md) (4 shared connections)
- [CLI Parser & Commands](CLI_Parser_&_Commands.md) (3 shared connections)
- [Trade Journal & Reporting](Trade_Journal_&_Reporting.md) (3 shared connections)
- [App State & Security Scopes (2)](App_State_&_Security_Scopes_2.md) (2 shared connections)
- [App State & Security Scopes](App_State_&_Security_Scopes.md) (2 shared connections)
- [Risk Management & Drawdown](Risk_Management_&_Drawdown.md) (2 shared connections)
- [Openalgo Bridge History Module](Openalgo_Bridge_History_Module.md) (2 shared connections)
- [Database & Persistence Layer](Database_&_Persistence_Layer.md) (2 shared connections)
- [Trade Gate & Pre-Check](Trade_Gate_&_Pre-Check.md) (2 shared connections)

## Source Files

- `algobot/execution_policy.py`
- `algobot/kill_switch.py`
- `algobot/live_execution.py`
- `algobot/risk.py`
- `pages/11_Live_Trading.py`
- `tests/test_execution_policy.py`

## Audit Trail

- EXTRACTED: 92 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*