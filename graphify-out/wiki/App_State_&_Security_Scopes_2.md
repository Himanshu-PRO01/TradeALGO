# App State & Security Scopes (2)

> 24 nodes

## Key Concepts

- **AlertLog** (16 connections) — `algobot/signal_alerts.py`
- **test_signal_alerts.py** (16 connections) — `tests/test_signal_alerts.py`
- **signal_alerts.py** (13 connections) — `algobot/signal_alerts.py`
- **step()** (11 connections) — `algobot/signal_alerts.py`
- **test_alert_failure_is_logged_but_does_not_raise()** (8 connections) — `tests/test_signal_alerts.py`
- **sqlite3** (8 connections)
- **test_alert_does_not_resend_for_the_same_still_open_position()** (6 connections) — `tests/test_signal_alerts.py`
- **test_alert_flips_flat_to_open_on_a_real_entry_signal()** (6 connections) — `tests/test_signal_alerts.py`
- **test_alert_stays_flat_with_no_open_signal()** (5 connections) — `tests/test_signal_alerts.py`
- **_trending_df()** (5 connections) — `tests/test_signal_alerts.py`
- **alert_scope()** (4 connections) — `algobot/appstate.py`
- **.history()** (2 connections) — `algobot/signal_alerts.py`
- **.reset()** (2 connections) — `algobot/signal_alerts.py`
- **.close_db()** (1 connections) — `algobot/signal_alerts.py`
- **.get_state()** (1 connections) — `algobot/signal_alerts.py`
- **.__init__()** (1 connections) — `algobot/signal_alerts.py`
- **.record_event()** (1 connections) — `algobot/signal_alerts.py`
- **.set_state()** (1 connections) — `algobot/signal_alerts.py`
- **DataFrame** (1 connections)
- **Also global and persistent, like the kill switch and rehearsal log: two browser…** (1 connections) — `algobot/appstate.py`
- **Sends a WhatsApp alert on the same strategy signal Paper Trading and Sandbox…** (1 connections) — `algobot/signal_alerts.py`
- **Forgets local tracking only -- does not un-send any alert already delivered.** (1 connections) — `algobot/signal_alerts.py`
- **Compare the strategy's current open/flat status against what we last alerted…** (1 connections) — `algobot/signal_alerts.py`
- **Flat long enough for both EMAs to warm up equal, then a clean monotonic rally:…** (1 connections) — `tests/test_signal_alerts.py`

## Relationships

- [Paper Trading Paperlog Module](Paper_Trading_Paperlog_Module.md) (12 shared connections)
- [Whatsapp Alerts Check Module](Whatsapp_Alerts_Check_Module.md) (9 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (4 shared connections)
- [App State & Security Scopes](App_State_&_Security_Scopes.md) (3 shared connections)
- [Execution Live Policy Module](Execution_Live_Policy_Module.md) (2 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (2 shared connections)
- [Database & Persistence Layer](Database_&_Persistence_Layer.md) (2 shared connections)
- [App Configuration & Settings (2)](App_Configuration_&_Settings_2.md) (1 shared connections)
- [Monte Carlo Audit & Risk](Monte_Carlo_Audit_&_Risk.md) (1 shared connections)
- [Trade Journal & Reporting](Trade_Journal_&_Reporting.md) (1 shared connections)
- [Strategy Rule Engine (8)](Strategy_Rule_Engine_8.md) (1 shared connections)
- [Strategy Rule Engine (5)](Strategy_Rule_Engine_5.md) (1 shared connections)

## Source Files

- `algobot/appstate.py`
- `algobot/signal_alerts.py`
- `tests/test_signal_alerts.py`

## Audit Trail

- EXTRACTED: 73 (96%)
- INFERRED: 3 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*