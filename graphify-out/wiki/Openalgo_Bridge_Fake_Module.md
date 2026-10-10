# Openalgo Bridge Fake Module

> 26 nodes

## Key Concepts

- **test_openalgo_bridge.py** (36 connections) — `tests/test_openalgo_bridge.py`
- **Fake** (20 connections) — `tests/test_openalgo_bridge.py`
- **client()** (17 connections) — `tests/test_openalgo_bridge.py`
- **test_the_api_key_is_never_shown_in_an_error()** (6 connections) — `tests/test_openalgo_bridge.py`
- **test_empty_answer_explains_the_history_limit_and_bad_ranges_are_refused()** (5 connections) — `tests/test_openalgo_bridge.py`
- **test_long_ranges_are_fetched_in_pieces_and_stitched()** (5 connections) — `tests/test_openalgo_bridge.py`
- **test_a_missing_key_is_explained()** (4 connections) — `tests/test_openalgo_bridge.py`
- **test_bad_arguments_are_refused_before_anything_is_sent()** (4 connections) — `tests/test_openalgo_bridge.py`
- **test_db_source_is_sent_only_when_asked_and_broker_is_refused()** (4 connections) — `tests/test_openalgo_bridge.py`
- **test_default_piece_size_depends_on_the_interval()** (4 connections) — `tests/test_openalgo_bridge.py`
- **test_lot_size_comes_from_openalgo_and_the_request_is_exact()** (4 connections) — `tests/test_openalgo_bridge.py`
- **test_openalgo_error_answers_become_readable_errors()** (4 connections) — `tests/test_openalgo_bridge.py`
- **test_order_placement_is_gated_and_uses_openalgo()** (4 connections) — `tests/test_openalgo_bridge.py`
- **test_prices_that_fail_the_checks_are_refused()** (4 connections) — `tests/test_openalgo_bridge.py`
- **test_telegram_notify_sends_the_documented_fields_and_needs_both_arguments()** (4 connections) — `tests/test_openalgo_bridge.py`
- **test_daily_candles_are_dated_by_day_whatever_the_time_of_day()** (3 connections) — `tests/test_openalgo_bridge.py`
- **test_history_converts_epoch_seconds_to_india_time_in_our_format()** (3 connections) — `tests/test_openalgo_bridge.py`
- **test_history_request_uses_exactly_the_documented_fields()** (3 connections) — `tests/test_openalgo_bridge.py`
- **test_history_sorts_and_removes_duplicate_candles()** (3 connections) — `tests/test_openalgo_bridge.py`
- **.__call__()** (2 connections) — `tests/test_openalgo_bridge.py`
- **fake_server()** (2 connections) — `tests/test_openalgo_bridge.py`
- **answer()** (2 connections) — `tests/test_openalgo_bridge.py`
- **.__init__()** (1 connections) — `tests/test_openalgo_bridge.py`
- **fixture** (1 connections)
- **A stand-in for the network. Records every request; answers by path.** (1 connections) — `tests/test_openalgo_bridge.py`
- *... and 1 more nodes in this community*

## Relationships

- [CLI Parser & Commands](CLI_Parser_&_Commands.md) (20 shared connections)
- [Openalgo Bridge History Module](Openalgo_Bridge_History_Module.md) (7 shared connections)
- [Execution Live Policy Module](Execution_Live_Policy_Module.md) (1 shared connections)
- [Ai Provider Match Module](Ai_Provider_Match_Module.md) (1 shared connections)
- [Upstox Sandbox & Broker Client](Upstox_Sandbox_&_Broker_Client.md) (1 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (1 shared connections)
- [Conftest Synthetic User Module](Conftest_Synthetic_User_Module.md) (1 shared connections)
- [Openalgo Bridge Handler Module](Openalgo_Bridge_Handler_Module.md) (1 shared connections)

## Source Files

- `tests/test_openalgo_bridge.py`

## Audit Trail

- EXTRACTED: 79 (88%)
- INFERRED: 11 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*