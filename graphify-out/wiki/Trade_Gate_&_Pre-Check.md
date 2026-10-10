# Trade Gate & Pre-Check

> 26 nodes

## Key Concepts

- **test_gate_alert.py** (26 connections) — `tests/test_gate_alert.py`
- **gate.py** (17 connections) — `algobot/gate.py`
- **check_gate()** (15 connections) — `algobot/gate.py`
- **build_alert()** (10 connections) — `algobot/gate.py`
- **run()** (7 connections) — `tests/test_gate_alert.py`
- **FakeClient** (6 connections) — `tests/test_gate_alert.py`
- **test_alert_is_blocked_when_the_day_is_over_or_the_trade_does_not_fit()** (5 connections) — `tests/test_gate_alert.py`
- **journal_with_a_losing_morning()** (4 connections) — `tests/test_gate_alert.py`
- **test_alert_text_carries_the_size_the_risk_and_the_verdict()** (4 connections) — `tests/test_gate_alert.py`
- **GateResult** (3 connections) — `algobot/gate.py`
- **fake_client()** (3 connections) — `tests/test_gate_alert.py`
- **test_alert_command_exits_one_and_still_tells_him_when_blocked()** (3 connections) — `tests/test_gate_alert.py`
- **test_fetch_history_command_writes_a_csv_our_tools_can_read()** (3 connections) — `tests/test_gate_alert.py`
- **test_gate_blocks_after_the_trade_limit_or_the_loss_limit()** (3 connections) — `tests/test_gate_alert.py`
- **test_gate_is_open_on_a_fresh_day_and_reports_the_day_so_far()** (3 connections) — `tests/test_gate_alert.py`
- **test_alert_command_sends_to_telegram_and_exits_zero_when_allowed()** (2 connections) — `tests/test_gate_alert.py`
- **test_openalgo_problems_are_reported_as_friendly_errors()** (2 connections) — `tests/test_gate_alert.py`
- **test_size_command_can_read_the_lot_size_from_openalgo()** (2 connections) — `tests/test_gate_alert.py`
- **.history()** (1 connections) — `tests/test_gate_alert.py`
- **.__init__()** (1 connections) — `tests/test_gate_alert.py`
- **.lot_size()** (1 connections) — `tests/test_gate_alert.py`
- **.telegram_notify()** (1 connections) — `tests/test_gate_alert.py`
- **date** (1 connections)
- **fixture** (1 connections)
- **Pre-trade gate and alert message. OpenAlgo (or TradingView) can tell the…** (1 connections) — `algobot/gate.py`
- *... and 1 more nodes in this community*

## Relationships

- [Trade Journal & Reporting](Trade_Journal_&_Reporting.md) (10 shared connections)
- [CLI Parser & Commands (2)](CLI_Parser_&_Commands_2.md) (6 shared connections)
- [Sizing Size Format Module](Sizing_Size_Format_Module.md) (5 shared connections)
- [Interactive Practice Simulator](Interactive_Practice_Simulator.md) (2 shared connections)
- [App State & Security Scopes](App_State_&_Security_Scopes.md) (2 shared connections)
- [Interactive Practice Simulator (4)](Interactive_Practice_Simulator_4.md) (2 shared connections)
- [CLI Parser & Commands (4)](CLI_Parser_&_Commands_4.md) (2 shared connections)
- [Market Data Validation & Feed (3)](Market_Data_Validation_&_Feed_3.md) (2 shared connections)
- [Execution Live Policy Module](Execution_Live_Policy_Module.md) (2 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (2 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (2 shared connections)
- [Interactive Practice Simulator (2)](Interactive_Practice_Simulator_2.md) (1 shared connections)

## Source Files

- `algobot/gate.py`
- `tests/test_gate_alert.py`

## Audit Trail

- EXTRACTED: 81 (98%)
- INFERRED: 2 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*