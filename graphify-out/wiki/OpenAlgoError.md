# OpenAlgoError

> God node · 46 connections · `algobot/openalgo_bridge.py`

**Community:** [CLI Parser & Commands](CLI_Parser_&_Commands.md)

## Connections by Relation

### calls
- ._post() `EXTRACTED`
- fetch_history_range() `EXTRACTED`
- .place() `EXTRACTED`
- .history() `EXTRACTED`
- test_the_api_key_is_never_shown_in_an_error() `EXTRACTED`
- .place_order() `EXTRACTED`
- .smart_order() `EXTRACTED`
- _check_date() `EXTRACTED`
- .cancel_order() `EXTRACTED`
- .lot_size() `EXTRACTED`
- .modify_order() `EXTRACTED`
- .quote() `EXTRACTED`
- .telegram_notify() `EXTRACTED`
- test_order_calls_are_never_retried() `EXTRACTED`
- .order_status() `EXTRACTED`
- _http_post() `EXTRACTED`
- .__init__() `EXTRACTED`
- fail() `EXTRACTED`
- leaky() `EXTRACTED`

### contains
- openalgo_bridge.py `EXTRACTED`

### imports
- cli.py `EXTRACTED`
- test_openalgo_bridge.py `EXTRACTED`
- test_live_execution.py `EXTRACTED`
- live_execution.py `EXTRACTED`
- live_chart.py `EXTRACTED`
- 24_OpenAlgo_Execution.py `EXTRACTED`

### inherits
- RuntimeError `EXTRACTED`

### rationale_for
- Something a person can fix: OpenAlgo not running, wrong key, bad request. `EXTRACTED`

### uses
- LiveExecutionService `INFERRED`
- main() `INFERRED`
- test_kill_switch_blocks_order() `INFERRED`
- test_risk_manager_blocks_new_buy() `INFERRED`
- test_risk_rejects_buy_outside_entry_window() `INFERRED`
- fetch_candles() `INFERRED`
- test_confirmation_is_required() `INFERRED`
- test_empty_answer_explains_the_history_limit_and_bad_ranges_are_refused() `INFERRED`
- test_a_missing_key_is_explained() `INFERRED`
- test_bad_arguments_are_refused_before_anything_is_sent() `INFERRED`
- test_db_source_is_sent_only_when_asked_and_broker_is_refused() `INFERRED`
- test_lot_size_comes_from_openalgo_and_the_request_is_exact() `INFERRED`
- test_openalgo_error_answers_become_readable_errors() `INFERRED`
- test_order_placement_is_gated_and_uses_openalgo() `INFERRED`
- test_prices_that_fail_the_checks_are_refused() `INFERRED`
- test_telegram_notify_sends_the_documented_fields_and_needs_both_arguments() `INFERRED`
- test_openalgo_not_running_is_explained() `INFERRED`
- test_real_http_errors_are_friendly_and_do_not_leak_the_key() `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*