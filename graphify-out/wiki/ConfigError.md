# ConfigError

> God node · 84 connections · `algobot/config.py`

**Community:** [CLI Parser & Commands (2)](CLI_Parser_&_Commands_2.md)

## Connections by Relation

### calls
- [validate_config()](validate_config.md) `EXTRACTED`
- [build_strategy()](build_strategy.md) `EXTRACTED`
- [load_config()](load_config.md) `EXTRACTED`
- add_indicators() `EXTRACTED`
- evaluate_rule() `EXTRACTED`
- cmd_backtest() `EXTRACTED`
- run_dynamic_strike_option_backtest() `EXTRACTED`
- run_tick_strategy() `EXTRACTED`
- generate_synthetic_option_chain() `EXTRACTED`
- cmd_audit() `EXTRACTED`
- cmd_alert() `EXTRACTED`
- cmd_lookahead() `EXTRACTED`
- load_option_chain_csv() `EXTRACTED`
- validate_option_chain() `EXTRACTED`
- cmd_lab() `EXTRACTED`
- contract_columns() `EXTRACTED`
- cmd_size() `EXTRACTED`
- _parse_day() `EXTRACTED`
- _merge() `EXTRACTED`
- parse_time() `EXTRACTED`
- *…and 22 more `calls` connection(s) not listed (lowest-degree first to go)*

### contains
- config.py `EXTRACTED`

### imports
- cli.py `EXTRACTED`
- 5_Backtest.py `EXTRACTED`
- test_indicators_strategy.py `EXTRACTED`
- strategy.py `EXTRACTED`
- 17_Sandbox_Rehearsal.py `EXTRACTED`
- 14_Upstox_Sandbox.py `EXTRACTED`
- indicators.py `EXTRACTED`
- 23_Live_Markets.py `EXTRACTED`
- 16_Paper_Trading.py `EXTRACTED`
- 20_Signal_Alerts.py `EXTRACTED`
- 28_Swarm_Simulation_Lab.py `EXTRACTED`
- dynamic_options.py `EXTRACTED`
- 13_Auto_Tester.py `EXTRACTED`
- 26_Tick_Engine.py `EXTRACTED`
- test_costs_and_config.py `EXTRACTED`
- 25_Dynamic_Options.py `EXTRACTED`
- tick_engine.py `EXTRACTED`
- 7_Test_lab.py `EXTRACTED`
- upstox_bod_instruments.py `EXTRACTED`
- upstox_market_data.py `EXTRACTED`
- *…and 3 more `imports` connection(s) not listed (lowest-degree first to go)*

### inherits
- ValueError `EXTRACTED`

### rationale_for
- Raised when the config file has a problem the user should fix. `EXTRACTED`

### uses
- UpstoxMarketData `INFERRED`
- RuleStrategy `INFERRED`
- main() `INFERRED`
- UpstoxBODResolver `INFERRED`
- UpstoxOptionContracts `INFERRED`
- SmaCrossover `INFERRED`
- NewEraStrategy `INFERRED`
- test_dangerous_or_unsupported_rules_are_rejected() `INFERRED`
- test_bad_values_are_rejected() `INFERRED`
- test_build_strategy_unknown_name() `INFERRED`
- test_indicator_config_errors_are_friendly() `INFERRED`
- test_sma_crossover_validation_and_signals() `INFERRED`
- test_unknown_column_and_non_boolean_rules_are_rejected() `INFERRED`
- test_times_must_be_in_order() `INFERRED`
- test_typo_in_setting_name_is_rejected_with_the_name_in_the_message() `INFERRED`
- test_rules_strategy_needs_at_least_one_rule_and_rejects_typos() `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*