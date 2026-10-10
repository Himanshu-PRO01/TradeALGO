# Risk Management & Drawdown

> 10 nodes

## Key Concepts

- **RiskManager** (15 connections) — `algobot/risk.py`
- **.can_enter()** (3 connections) — `algobot/risk.py`
- **.check_daily_loss()** (2 connections) — `algobot/risk.py`
- **.new_day()** (2 connections) — `algobot/risk.py`
- **.__init__()** (1 connections) — `algobot/risk.py`
- **.register_entry()** (1 connections) — `algobot/risk.py`
- **time** (1 connections)
- **Reset the daily counters and lift any daily halt.** (1 connections) — `algobot/risk.py`
- **May a NEW position be opened now? Returns (allowed, reason if not).** (1 connections) — `algobot/risk.py`
- **Kill switch. day_pnl includes open profit/loss. True if it just tripped.** (1 connections) — `algobot/risk.py`

## Relationships

- [Execution Live Kill Module](Execution_Live_Kill_Module.md) (4 shared connections)
- [Backtesting & Historical Execution (2)](Backtesting_&_Historical_Execution_2.md) (3 shared connections)
- [Execution Live Policy Module](Execution_Live_Policy_Module.md) (2 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (1 shared connections)

## Source Files

- `algobot/risk.py`

## Audit Trail

- EXTRACTED: 17 (89%)
- INFERRED: 2 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*