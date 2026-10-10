# Graph Report - TradeALGO-main  (2026-10-10)

## Corpus Check
- 210 files · ~201,681 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 15 file(s) not represented in the graph (top: .csv 6, (none) 3, .example 1)

## Summary
- 2385 nodes · 5816 edges · 126 communities (117 shown, 9 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 169 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Database & Persistence Layer
- Options Pricing & Greeks
- Strategy Rule Engine
- Paper Trading Daemon Module
- Upstox Sandbox & Broker Client
- Market Data Validation & Feed
- Market Live Livemarkethub Module
- Streamlit UI Components
- Strategy Rule Engine (2)
- Paper Trading Paperlog Module
- Trade Journal & Reporting
- Whatsapp Alerts Check Module
- CLI Parser & Commands
- Monte Carlo Audit & Risk
- Value Area Breakout Module
- CLI Parser & Commands (2)
- Strategy Lab & Research
- Technical Indicators Library
- Site Integrity Paper Module
- Strategy Rule Engine (3)
- Pivot Points & Price Levels
- Interactive Practice Simulator
- App State & Security Scopes
- Options Pricing & Greeks (2)
- Interactive Practice Simulator (2)
- Agent Market Fetch Module
- Execution Live Kill Module
- Ai Provider Generate Module
- Backtesting & Historical Execution
- Trade Gate & Pre-Check
- Strategy Rule Engine (4)
- Learning Experiments Lesson Module
- Openalgo Bridge Fake Module
- Streamlit UI Components (2)
- Strategy Rule Engine (5)
- App State & Security Scopes (2)
- Mirofish Sim Graph Module
- Engine Helpers Make Module
- Strategy Rule Engine (6)
- Agent V2 Market Module
- Monte Carlo Audit & Risk (2)
- Market Data Validation & Feed (2)
- Swarm Synthetic Memory Module
- Ai Provider Match Module
- Architecture Specifications
- Ai Provider Get Module
- Execution Live Policy Module
- Strategy Rule Engine (7)
- CLI Parser & Commands (3)
- Interactive Practice Simulator (3)
- Backtesting & Historical Execution (2)
- Performance Metrics & Ratios
- Dashboard Fresh Own Module
- App Configuration & Settings
- Sizing Size Format Module
- Upstox Sandbox & Broker Client (2)
- Deployment Track Record Module
- Backtesting & Historical Execution (3)
- App Configuration & Settings (2)
- Streamlit UI Components (3)
- Research Agent Run Module
- App Configuration & Settings (3)
- Database & Persistence Layer (2)
- System Documentation
- Trade Journal & Reporting (2)
- Strategy Rule Engine (8)
- Ai Provider Generate Module (2)
- Market Data Validation & Feed (3)
- Activity Log Chatgpt Module
- App Configuration & Settings (4)
- CLI Parser & Commands (4)
- CLI Parser & Commands (5)
- Openalgo Bridge History Module
- Strategy Rule Engine (9)
- CLI Parser & Commands (6)
- Market Data Validation & Feed (4)
- Trade Journal & Reporting (3)
- Risk Management & Drawdown
- Interactive Practice Simulator (4)
- Conftest Synthetic User Module
- Strategy Rule Engine (10)
- Web Dashboard & Server
- Saas Launch Plan Module
- Page Position Module
- Web Dashboard & Server (2)
- Profitability Engine Monte Module
- Activity Chatgpt Log Module
- Interactive Practice Simulator (5)
- Prompt Component
- Activity Chatgpt Log Module (2)
- Activity Chatgpt Log Module (3)
- Activity Chatgpt Log Module (4)
- Activity Chatgpt Log Module (5)
- Activity Chatgpt Log Module (6)
- Activity Chatgpt Log Module (7)
- Activity Chatgpt Log Module (8)
- Interactive Practice Simulator (6)
- Strategy Rule Engine (11)
- Activity Chatgpt Log Module (9)
- Monte Carlo Audit & Risk (3)
- Activity Chatgpt Log Module (10)
- Activity Chatgpt Log Module (11)
- Activity Chatgpt Log Module (12)
- Activity Chatgpt Log Module (13)
- Activity Chatgpt Log Module (14)
- Hosting On Own Module
- Readme How To Module
- Architecture Specifications (2)
- Architecture Specifications (3)
- Architecture Specifications (4)
- Streamlit UI Components (4)
- Streamlit UI Components (5)
- Architecture Specifications (5)
- Architecture Specifications (6)
- Architecture Specifications (7)
- Openalgo Bridge Handler Module
- Database & Persistence Layer (3)
- Helpers Scripted Module
- Interactive Practice Simulator (7)
- Architecture Specifications (8)
- Dashboard Runpy Module
- Explain Lookahead Module
- Architecture Specifications (9)
- Architecture Specifications (10)
- Dashboard Component

## God Nodes (most connected - your core abstractions)
1. `ConfigError` - 84 edges
2. `validate_config()` - 69 edges
3. `Journal` - 51 edges
4. `generate_sample_data()` - 48 edges
5. `OpenAlgoError` - 46 edges
6. `OpenAlgoClient` - 41 edges
7. `build_strategy()` - 41 edges
8. `load_config()` - 40 edges
9. `run_backtest()` - 39 edges
10. `make_bars()` - 37 edges

## Surprising Connections (you probably didn't know these)
- `ProviderError` --uses--> `ProviderError`  [INFERRED]
  pages/5_Backtest.py → algobot/ai_provider.py
- `read_strategy_image()` --uses--> `ProviderError`  [INFERRED]
  pages/5_Backtest.py → algobot/ai_provider.py
- `gemini_fail()` --calls--> `ProviderError`  [EXTRACTED]
  tests/test_ai_provider.py → algobot/ai_provider.py
- `test_dual_provider_fallback_when_both_configured()` --uses--> `FallbackProvider`  [INFERRED]
  tests/test_ai_provider.py → algobot/ai_provider.py
- `test_grok_is_preferred_when_configured()` --uses--> `GrokProvider`  [INFERRED]
  tests/test_ai_provider.py → algobot/ai_provider.py

## Import Cycles
- None detected.

## Communities (126 total, 9 thin omitted)

### Community 0 - "Database & Persistence Layer"
Cohesion: 0.05
Nodes (52): DataFrame, Connects a strategy's own signal (the same one Paper Trading evaluates) to real…, Compare the strategy's current open/flat status against what we last acted on,…, Forgets local tracking only. It does NOT cancel any order already sent to…, RehearsalLog, step(), clean_token(), extract_order_id() (+44 more)

### Community 1 - "Options Pricing & Greeks"
Cohesion: 0.06
Nodes (67): analyse(), _ema(), _fast_breakeven(), format_idea(), DataFrame, Series, AI Trade Advisor for the Practice Room. Uses real-time market snapshot (spot,…, Index points the market must move for the option to reach `cost` (break even). (+59 more)

### Community 2 - "Strategy Rule Engine"
Cohesion: 0.06
Nodes (44): AgentError, AgentResult, _cite(), _guard(), _parse(), ValueError, StrategyAgent, _texts() (+36 more)

### Community 3 - "Paper Trading Daemon Module"
Cohesion: 0.05
Nodes (46): IndiaCostModel, IndiaMarketProfile, is_regular_session(), datetime, India-first market calendar and cost assumptions for research simulations., Research approximation; broker/exchange charges must be refreshed before…, AuditLedger, get_market_session_status() (+38 more)

### Community 4 - "Upstox Sandbox & Broker Client"
Cohesion: 0.05
Nodes (32): _find_option_columns(), load_tick_csv(), _nearest_strike(), DataFrame, Tick-driven CE/PE strategy engine for research and paper rehearsal. The engine…, Run a tick-by-tick dynamic-strike long CE/PE strategy. Trigger evaluation…, Load underlying ticks plus wide option last-price columns. Required:…, run_tick_strategy() (+24 more)

### Community 5 - "Market Data Validation & Feed"
Cohesion: 0.08
Nodes (39): algobot, kill_switch_scope(), The kill switch is intentionally global and persistent, not scoped per visitor…, load_config(), Config loading and validation. The config is a YAML file that the trader (not…, Read a YAML file and return the validated config., fetch_ohlc(), LiveDataError (+31 more)

### Community 6 - "Market Live Livemarkethub Module"
Cohesion: 0.06
Nodes (30): _as_dict(), _authorize_market_feed(), _decode_market_feed_message(), get_market_hub(), LiveMarketHub, on_error(), on_message(), market_data_token() (+22 more)

### Community 7 - "Streamlit UI Components"
Cohesion: 0.06
Nodes (47): _apply_theme_from_toggle(), card(), check_row(), header(), inr(), is_dark_mode(), is_hinglish(), language_toggle() (+39 more)

### Community 8 - "Strategy Rule Engine (2)"
Cohesion: 0.07
Nodes (31): build_candidate_grid(), build_period_values(), build_scanner_candidates(), estimate_candidate_count(), estimate_scanner_count(), make_candidate(), rank_scanner_rows(), Pure helpers for the Auto Tester research page. (+23 more)

### Community 9 - "Paper Trading Paperlog Module"
Cohesion: 0.10
Nodes (30): Fetches current delayed OHLCV candles, checks strategy rules, and updates…, evaluate(), log_new_trades(), PaperLog, DataFrame, Paper trading: run a saved strategy against real (delayed) market prices and…, A virtual-capital view built only from what is actually on record: the stated…, Virtual equity after each logged closed trade (indexed by exit time), with its… (+22 more)

### Community 10 - "Trade Journal & Reporting"
Cohesion: 0.11
Nodes (31): behavior_flags(), build_daily_report(), format_daily_report_html(), format_daily_report_text(), format_review(), Journal, Trade journal, daily P&L report and review statistics. Why a journal: the…, Look for the habits that, more than any strategy, drain small accounts. A… (+23 more)

### Community 11 - "Whatsapp Alerts Check Module"
Cohesion: 0.10
Nodes (34): _http_get(), load_recipients(), RuntimeError, WhatsApp alerts via the free CallMeBot API (personal use only). This module…, Send `message` to every configured recipient. Returns one short result note per…, Something a person can fix: no recipients configured, an unreachable endpoint,…, Parse '+91XXXXXXXXXX:key1,+91YYYYYYYYYY:key2' from the environment (or…, Recipient (+26 more)

### Community 12 - "CLI Parser & Commands"
Cohesion: 0.10
Nodes (18): OpenAlgoClient, OpenAlgoError, RuntimeError, Lot size straight from OpenAlgo's instrument list, so it never goes stale here., Return True only when the user explicitly enables OpenAlgo execution., Check that OpenAlgo is reachable and its API key is accepted., Read the current quote through OpenAlgo. No order side effect., Route one order through OpenAlgo after the explicit execution gate is enabled.… (+10 more)

### Community 13 - "Monte Carlo Audit & Risk"
Cohesion: 0.09
Nodes (31): monte_carlo(), parameter_variants(), ndarray, One-at-a-time changes of about +/-20% to every numeric setting we can safely…, Resample the trades (with replacement) into many possible futures., Copy of the config with every charge and the slippage multiplied., scale_costs(), config_hash() (+23 more)

### Community 14 - "Value Area Breakout Module"
Cohesion: 0.15
Nodes (34): build(), day_bars(), test_index_data_without_volume_is_refused(), test_levels_use_only_the_previous_day(), test_low_volume_filter_blocks_high_volume_breakouts(), test_no_trade_without_return_to_zone(), test_stop_checked_first_when_a_bar_touches_both(), test_summarize_empty() (+26 more)

### Community 15 - "CLI Parser & Commands (2)"
Cohesion: 0.14
Nodes (34): build_parser(), cmd_ai_prompt(), cmd_alert(), cmd_audit(), cmd_breakeven(), cmd_check_config(), cmd_experiments(), cmd_explain() (+26 more)

### Community 16 - "Strategy Lab & Research"
Cohesion: 0.12
Nodes (32): DataFrame, Check that price bars are clean. Bad data quietly ruins backtests., validate_bars(), format_lab(), LabReport, null_test(), Stress lab: meet many kinds of market, instantly. For each market personality…, Pure noise, zero costs: the average result must be about zero. Anything else… (+24 more)

### Community 17 - "Technical Indicators Library"
Cohesion: 0.10
Nodes (33): add_indicators(), atr(), cci(), highest(), hma(), lowest(), mfi(), DataFrame (+25 more)

### Community 18 - "Site Integrity Paper Module"
Cohesion: 0.09
Nodes (28): ast, inspect, _log_with_trades(), Tests for PaperLog's virtual-capital views, and a standing safety check that…, Static guarantee: Forward Testing must not import live/sandbox execution code…, test_daily_pnl_groups_by_calendar_date_of_exit(), test_equity_curve_empty_when_nothing_logged(), test_equity_curve_is_cumulative_and_tracks_its_own_drawdown() (+20 more)

### Community 19 - "Strategy Rule Engine (3)"
Cohesion: 0.10
Nodes (23): add_prev_columns(), Add <column>_prev (the previous bar's value) for every column. This is how…, evaluate_rule(), normalize_rule_expression(), DataFrame, Pre-processes common trading syntax (e.g. crossover / crossunder / cross) into…, Evaluate a rule over all bars. Missing values (indicator warm-up) count as…, Entry and exit rules written as expressions in the config file. params:… (+15 more)

### Community 20 - "Pivot Points & Price Levels"
Cohesion: 0.15
Nodes (29): compute_level(), opening_range(), pivot_points(), prev_day(), prev_week(), _previous_period(), DataFrame, Series (+21 more)

### Community 21 - "Interactive Practice Simulator"
Cohesion: 0.15
Nodes (27): format_practice_report(), PracticeBlocked, PracticeError, PracticeSettings, ValueError, Practice room: trade Nifty options with fake money, for as long as you like.…, Something the player should fix: not enough money, no position, expired option., The player's own rules say no. Buying anyway needs override=True. (+19 more)

### Community 22 - "App State & Security Scopes"
Cohesion: 0.10
Nodes (25): configured_password(), experiments_scope(), is_hosted(), journal_scope(), paper_scope(), password_gate(), Where the app keeps its data, and who may look at it. Two ways to run it: LOCAL…, The journal for this visitor: a file locally, or an in-session store when… (+17 more)

### Community 23 - "Options Pricing & Greeks (2)"
Cohesion: 0.16
Nodes (26): _column_candidates(), contract_columns(), discover_contracts(), generate_synthetic_option_chain(), _load_long_option_chain(), load_option_chain_csv(), _nearest_strike(), _norm_contract() (+18 more)

### Community 24 - "Interactive Practice Simulator (2)"
Cohesion: 0.12
Nodes (8): _kind(), PracticeSession, Series, (bid, ask). You buy at the ask and sell at the bid., Index level between a and b at which the option's fair price equals target_mid., Reveal the next bar. Returns False at the end of the fake market., End the session: close any open position and build the review., Timestamp

### Community 25 - "Agent Market Fetch Module"
Cohesion: 0.14
Nodes (26): AgentReport, _base_config(), candidate_strategies(), CandidateResult, consensus_label(), fetch_news(), fetch_openalgo(), fetch_yfinance() (+18 more)

### Community 26 - "Execution Live Kill Module"
Cohesion: 0.17
Nodes (16): KillSwitch, DataFrame, Current state, decided purely by whichever event happened last., LiveExecutionService, The only programmatic path TradeALGO should use for live orders., enable_test_execution_policy(), FakeClient, Enable only the module-local gate for unit-testing downstream guards. (+8 more)

### Community 27 - "Ai Provider Generate Module"
Cohesion: 0.12
Nodes (13): AnthropicProvider, _chat_completion(), GeminiProvider, GrokProvider, OpenAIProvider, ProviderError, RuntimeError, xAI Grok Chat Completions and Multimodal Vision provider. (+5 more)

### Community 28 - "Backtesting & Historical Execution"
Cohesion: 0.11
Nodes (19): build_strategy_evidence(), MiroFishStrategyReport, _page_path(), Path, Full MiroFish-style, safety-bounded QA and strategy orchestration for…, Create an adversarial MiroFish-style evidence world from independent regimes., Execute synthetic-user journeys through Streamlit AppTest on research pages…, run_website_swarm() (+11 more)

### Community 29 - "Trade Gate & Pre-Check"
Cohesion: 0.13
Nodes (20): build_alert(), check_gate(), GateResult, date, Pre-trade gate and alert message. OpenAlgo (or TradingView) can tell the…, Returns (message, may_take_trade, sizing)., fake_client(), FakeClient (+12 more)

### Community 30 - "Strategy Rule Engine (4)"
Cohesion: 0.11
Nodes (14): ema(), sma(), _cci(), check_expression(), NewEraStrategy, Series, Strategies. A strategy looks at the bars up to and including the CURRENT bar…, Deterministic translation of the supplied TradingView New Era Strategy 1.0. The… (+6 more)

### Community 31 - "Learning Experiments Lesson Module"
Cohesion: 0.17
Nodes (24): analyze_and_learn_from_trades(), _default_path(), experiments_for_ai(), learning_summary(), Lesson, list_experiments(), load_memory(), _now() (+16 more)

### Community 32 - "Openalgo Bridge Fake Module"
Cohesion: 0.18
Nodes (23): http_server, client(), Fake, fake_server(), fixture, A stand-in for the network. Records every request; answers by path., test_a_missing_key_is_explained(), test_bad_arguments_are_refused_before_anything_is_sent() (+15 more)

### Community 33 - "Streamlit UI Components (2)"
Cohesion: 0.13
Nodes (23): candlestick(), equity_drawdown(), order_flow_chart(), payoff_chart(), pnl_bars(), premium_line(), DataFrame, Series (+15 more)

### Community 34 - "Strategy Rule Engine (5)"
Cohesion: 0.17
Nodes (9): _now(), ValueError, Strategy version history: an original rule set plus AI-drafted candidates. The…, A version-history operation was asked to do something inconsistent., _row_to_record(), StrategyVersionStore, VersionError, VersionRecord (+1 more)

### Community 35 - "App State & Security Scopes (2)"
Cohesion: 0.13
Nodes (15): alert_scope(), Also global and persistent, like the kill switch and rehearsal log: two browser…, AlertLog, DataFrame, Sends a WhatsApp alert on the same strategy signal Paper Trading and Sandbox…, Forgets local tracking only -- does not un-send any alert already delivered., Compare the strategy's current open/flat status against what we last alerted…, step() (+7 more)

### Community 36 - "Mirofish Sim Graph Module"
Cohesion: 0.16
Nodes (17): Agent, agent_chat(), AgentMemory, AgentPersona, build_world(), Graph, _initial_agents(), MarketEvent (+9 more)

### Community 37 - "Engine Helpers Make Module"
Cohesion: 0.28
Nodes (22): flat_rows(), make_bars(), make_cfg(), Shared helpers for building tiny, fully controlled test scenarios., rows: list of (open, high, low, close) tuples., run(), test_accounting_identity_end_equity_equals_capital_plus_trade_pnl(), test_costs_are_charged_on_both_sides() (+14 more)

### Community 38 - "Strategy Rule Engine (6)"
Cohesion: 0.21
Nodes (20): _alter_future(), Check, check_future_scramble(), check_indicator_columns(), check_truncation(), _first_difference(), LeakyStrategy, DataFrame (+12 more)

### Community 39 - "Agent V2 Market Module"
Cohesion: 0.18
Nodes (19): eval_df(), run_backtest(), Market Research Agent v2: bounded parameter search, official-source adapters…, ResearchV2, run_v2(), score(), source_check(), variants() (+11 more)

### Community 40 - "Monte Carlo Audit & Risk (2)"
Cohesion: 0.27
Nodes (20): AuditCheck, AuditReport, check_concentration(), check_costs(), check_out_of_sample(), check_parameters(), check_random_entries(), check_ruin() (+12 more)

### Community 41 - "Market Data Validation & Feed (2)"
Cohesion: 0.19
Nodes (19): cmd_check_data(), generate_sample_data(), Market data: loading CSV files and generating synthetic test data. The…, Random-walk intraday bars (default: 75 five-minute bars, 09:15 to 15:25).…, _bar_minutes(), data_quality_report(), format_data_quality(), Issue (+11 more)

### Community 42 - "Swarm Synthetic Memory Module"
Cohesion: 0.17
Nodes (18): JourneyResult, MarketEpisode, Memory, Persona, plan_journey(), Adaptive, bounded MiroFish-style synthetic-user swarm for TradeALGO., Run adaptive synthetic traders through changing fake worlds., _risk_ok() (+10 more)

### Community 43 - "Ai Provider Match Module"
Cohesion: 0.18
Nodes (20): _find_grok_key(), _find_groq_key(), _find_openai_key(), _get_candidate_secret_files(), _match_gemini_val(), _match_grok_val(), _match_groq_val(), _match_openai_val() (+12 more)

### Community 44 - "Architecture Specifications"
Cohesion: 0.10
Nodes (20): 10. Risk and Safety Architecture, 12. Page Architecture, 13. Shared UI Architecture, 14. External Integration Boundaries, 15. Testing Architecture, 16. Deployment Architecture, 17. Configuration and Secrets, 1. System Overview (+12 more)

### Community 45 - "Ai Provider Get Module"
Cohesion: 0.18
Nodes (17): _find_gemini_key(), get_ai_status(), get_provider(), GroqProvider, Any, Inspects credentials and returns active AI engine connection state., Groq's OpenAI-compatible Chat Completions provider., test_cross_key_collision_protection() (+9 more)

### Community 46 - "Execution Live Policy Module"
Cohesion: 0.15
Nodes (12): live_trading_allowed(), Execution safety policy. Live trading is deliberately prohibited in this build.…, require_live_disabled(), A persistent, human-operable kill switch. This is independent of the per-run…, ExecutionRequest, datetime, Single live-execution boundary for TradeALGO. TradeALGO owns signals and risk;…, Place exactly one live order request; never retries it. (+4 more)

### Community 47 - "Strategy Rule Engine (7)"
Cohesion: 0.10
Nodes (19): 10. Rules for Future Agents, 11. Current Handoff Goal, 1. Current Product Direction, 2. Major Work Already Completed, 3. Important Reality: Strategy Is NOT Proven Profitable, 4. Current Trading Desk UI, 5. Latest Relevant Commits, 6. Live Browser Test Status (+11 more)

### Community 48 - "CLI Parser & Commands (3)"
Cohesion: 0.17
Nodes (18): page(), fixture, run(), small_data(), start_practice(), test_backtest_logs_variants_and_audit_uses_the_count(), test_breakeven_and_ruin_commands(), test_check_data_command() (+10 more)

### Community 49 - "Interactive Practice Simulator (3)"
Cohesion: 0.15
Nodes (14): _bars(), fake_hub(), fixture, Practice Room's Live mode can stream real ticks from the shared Upstox market-…, Right after Start, a live tick can arrive before the one-time official-OHLC…, The single most important regression check here: an earlier version of this…, algobot.live_market.LiveMarketHub.snapshot() returns only the official, REST-…, st_session_source() (+6 more)

### Community 50 - "Backtesting & Historical Execution (2)"
Cohesion: 0.16
Nodes (8): RandomEntry, Benchmark: enters at random, exits after a fixed number of bars (or at the…, Backtester, DataFrame, Carry out last bar's decision at this bar's open., Base class. Subclass it and register it with @register("name")., Strategy, test_random_entry_benchmark_holds_for_a_fixed_number_of_bars()

### Community 51 - "Performance Metrics & Ratios"
Cohesion: 0.20
Nodes (18): compute_metrics(), _exposure_pct(), DataFrame, Series, Longest run of consecutive winning trades, and of consecutive non-winning…, Percentage of the tested time span spent holding a position (either side).…, _streaks(), test_metrics_on_known_trades() (+10 more)

### Community 52 - "Dashboard Fresh Own Module"
Cohesion: 0.20
Nodes (17): fresh(), own_rules(), High-priced data (like Nifty ~ 23,000) with the default 10 units / Rs 50,000…, Switch the page to 'Write my own rules', where the rules box and the confirm…, EMA + RSI was removed as a ready-made choice; HMA is now first/default., test_a_backtest_shows_results_without_any_extra_ticking(), test_a_bad_rule_gives_a_friendly_error_not_a_crash(), test_bad_time_and_bad_yaml_are_reported() (+9 more)

### Community 53 - "App Configuration & Settings"
Cohesion: 0.19
Nodes (16): describe_indicator(), explain_config(), expression_to_english(), Plain-English readback of a strategy config. Why this exists: when an AI (or a…, Turn a rule like "ema_fast > ema_slow and rsi_14 < 30" into words., Describe a VALIDATED config (see config.validate_config) in plain words., _rupees(), re (+8 more)

### Community 54 - "Sizing Size Format Module"
Cohesion: 0.20
Nodes (15): format_size(), option_position_size(), Position sizing for BOUGHT options, from a maximum loss per trade. The question…, Lots allowed for a bought option. est_charges: your broker's estimate of round-…, SizeResult, parametrize, test_bad_inputs_are_rejected(), test_charges_reduce_the_loss_budget() (+7 more)

### Community 55 - "Upstox Sandbox & Broker Client (2)"
Cohesion: 0.18
Nodes (11): InstrumentRef, Any, Read-only Upstox BOD instrument lookup for sandbox order forms. The sandbox…, UpstoxBODResolver, gzip, _nifty_option_contracts(), _nifty_option_expiries(), cache_data (+3 more)

### Community 56 - "Deployment Track Record Module"
Cohesion: 0.11
Nodes (17): 1. Check Track Record Progress Anytime, 1. Launch a Cloud VM, 1. Setup Python & Clone Repo, 24/7 Cloud Deployment & 90-Day SEBI Track Record Guide, 2. Connect via SSH & Install Docker, 2. Enable Systemd Background Service, 2. Generate SEBI Compliance Dossier, 3. Back Up Your Track Record to GitHub (+9 more)

### Community 57 - "Backtesting & Historical Execution (3)"
Cohesion: 0.12
Nodes (10): glob, html, importlib, load_prices(), ProviderError, cache_data, RuntimeError, Backtest: see how a trading idea would have done on past prices, with pretend… (+2 more)

### Community 58 - "App Configuration & Settings (2)"
Cohesion: 0.13
Nodes (17): _merge(), _non_negative(), parse_time(), _positive_or_none(), Any, time, Merge the user's settings over the defaults and check every value., Recursively merge `override` into a copy of `base`, rejecting unknown keys. (+9 more)

### Community 59 - "Streamlit UI Components (3)"
Cohesion: 0.20
Nodes (15): journal_rows_from_csv(), journal_to_csv(), Every trade as CSV text, for backup or to send to someone., Parse CSV text made by journal_to_csv into rows for Journal.import_rows., app(), test_bad_journal_files_are_refused_with_a_reason(), test_every_page_in_the_menu_loads_with_no_exception(), test_feedback_page_saves_and_offers_the_text_to_send() (+7 more)

### Community 60 - "Research Agent Run Module"
Cohesion: 0.27
Nodes (14): CandidateScore, _evaluate(), _mutate(), _pf(), Autonomous synthetic research agents for TradeALGO. Agents are researchers, not…, Let bounded synthetic agents perform an actual research loop. Every candidate…, Autonomous research on supplied Indian-market historical OHLCV. The agents…, ResearchAgent (+6 more)

### Community 61 - "App Configuration & Settings (3)"
Cohesion: 0.17
Nodes (12): CostModel, Trading costs and slippage. Costs are the most common reason a strategy that…, Price after adverse slippage: buyers pay more, sellers receive less., Total charges in rupees for one order (one side of a trade)., parametrize, test_all_repo_configs_validate(), test_bad_side_rejected(), test_bad_values_are_rejected() (+4 more)

### Community 62 - "Database & Persistence Layer (2)"
Cohesion: 0.19
Nodes (10): FeedbackError, FeedbackItem, FeedbackStore, ValueError, Suggestions from the brother (or anyone) about what to change. Feedback is…, A spreadsheet treats a cell starting with = + - @ as a formula. Defuse that., A message that reads well on WhatsApp., _safe_cell() (+2 more)

### Community 63 - "System Documentation"
Cohesion: 0.13
Nodes (14): 1. 📊 Deterministic Backtester & Cost Modeling, 2. 📸 AI Photo-to-Strategy Vision Reader, 3. 🐟 MiroFish Multi-Agent Swarm Strategy Audit, 4. 📝 90-Day Paper Trading Daemon & Daily Audit Ledger, 5. 🛡️ Safety & Execution Boundary (OpenAlgo Integration), ⚠️ Disclaimer, Installation, ⚡ Key Capabilities (+6 more)

### Community 64 - "Trade Journal & Reporting (2)"
Cohesion: 0.20
Nodes (3): date, Net result measured in units of the amount risked (1R = the planned loss)., Trade

### Community 65 - "Strategy Rule Engine (8)"
Cohesion: 0.16
Nodes (4): Saved strategy and backtest-result library., SavedStrategyLibrary, test_saved_strategy_library_round_trip_and_count(), uuid

### Community 66 - "Ai Provider Generate Module (2)"
Cohesion: 0.17
Nodes (6): AIProvider, FallbackProvider, Reads a strategy photo/screenshot and extracts strict TradeALGO rules YAML., Executes requests using primary provider and seamlessly fails over to backup on…, read_strategy_image(), test_read_strategy_image_parses_rules_cleanly()

### Community 67 - "Market Data Validation & Feed (3)"
Cohesion: 0.27
Nodes (12): DataError, load_csv(), ValueError, Raised when a data file has a problem the user should fix., Load OHLCV bars from a CSV file. Needed columns: a time column (datetime /…, parametrize, test_demo_configs_run_end_to_end_and_the_books_balance(), test_load_csv_accepts_common_layout_and_optional_volume() (+4 more)

### Community 68 - "Activity Log Chatgpt Module"
Cohesion: 0.15
Nodes (12): Activity: GitHub Repository Inspection, Activity: Merge origin/main (live-trading revert) with local WhatsApp alerts/kill-switch/Backtest/guide work, Brother's Legacy Python Code: Review Notes, ChatGPT Activity Log, Current Repository, Handover Instructions for Future Agents, Important Existing Project Context, Last Updated (+4 more)

### Community 69 - "App Configuration & Settings (4)"
Cohesion: 0.35
Nodes (10): _agent_config(), AgentProfile, AgentResult, MiroFish-style synthetic-user simulation for TradeALGO. This is intentionally…, Run bounded synthetic users through existing fake-market infrastructure. Agent…, simulate_agents(), SimulationReport, cfg() (+2 more)

### Community 70 - "CLI Parser & Commands (4)"
Cohesion: 0.27
Nodes (10): main(), db(), fixture, run(), test_bad_inputs_are_friendly(), test_html_report_file_is_written(), test_journal_report_and_review_flow(), test_missing_stop_is_called_out() (+2 more)

### Community 71 - "CLI Parser & Commands (5)"
Cohesion: 0.26
Nodes (11): _client(), _fetch(), fetch_candles(), openalgo_configured(), cache_data, DataFrame, Real NSE candles for the dashboard's main chart, sourced from the operator's…, True once the operator has set an OpenAlgo API key (.env locally, or a… (+3 more)

### Community 72 - "Openalgo Bridge History Module"
Cohesion: 0.20
Nodes (10): _check_date(), fetch_history_range(), _http_post(), load_env(), DataFrame, Bridge to a self-hosted OpenAlgo instance. OpenAlgo (open source, AGPL-3.0)…, Candles as a DataFrame in this toolkit's format (naive India time,…, Fetch a long range in pieces and stitch it together (duplicates removed,… (+2 more)

### Community 73 - "Strategy Rule Engine (9)"
Cohesion: 0.24
Nodes (8): load_prices(), Shared setup for the manual QA scripts: a realistic (fake) Nifty-like data file…, main(), Manual QA: drive the real Backtest page, then the Reality check page, with the…, main(), Manual QA: run a realistic (fake) opening-range-breakout strategy through the…, warnings, yaml

### Community 74 - "CLI Parser & Commands (6)"
Cohesion: 0.24
Nodes (7): cmd_backtest(), ExperimentLog, _money(), _num(), Turn a BacktestResult into a readable summary and saved files., save_outputs(), summary_text()

### Community 75 - "Market Data Validation & Feed (4)"
Cohesion: 0.27
Nodes (7): Data quality checks. Bad data quietly produces beautiful backtests: a missing…, Backtest engine. Rules of the simulation (kept deliberately conservative): * A…, Performance metrics computed from the trade list and equity curve., dataclasses, math, numpy, pandas

### Community 76 - "Trade Journal & Reporting (3)"
Cohesion: 0.29
Nodes (5): JournalError, _parse_time(), ValueError, Add trades from exported rows, through the same checks as typing them in.…, Raised for input the user should correct.

### Community 77 - "Risk Management & Drawdown"
Cohesion: 0.20
Nodes (5): time, Reset the daily counters and lift any daily halt., May a NEW position be opened now? Returns (allowed, reason if not)., Kill switch. day_pnl includes open profit/loss. True if it just tripped., RiskManager

### Community 78 - "Interactive Practice Simulator (4)"
Cohesion: 0.27
Nodes (7): _build_session(), _cached_real_bars(), _live_bars(), cache_data, DataFrame, Practice room — LIVE DATA edition. Now has three modes: 1. Fake (synthetic) —…, Fetch bars — cached for 60 s so Live mode auto-refreshes cleanly.

### Community 79 - "Conftest Synthetic User Module"
Cohesion: 0.20
Nodes (8): pytest, streamlit_testing_v1, _isolate_state(), fixture, No test may touch the real journal or experiment log., parametrize, Synthetic-user website smoke tests. These are deterministic fake users, not…, test_synthetic_user_can_open_safe_workflow()

### Community 80 - "Strategy Rule Engine (10)"
Cohesion: 0.20
Nodes (9): Assumptions I had to make (the description was ambiguous), Data requirements, Not financial advice, Phase 2: only if it passes, add to TradeALGO, Rules, Strategy spec: Prior-Day Value Area Breakout (long only), Task for the coding agent (paste this), Test protocol (+1 more)

### Community 81 - "Web Dashboard & Server"
Cohesion: 0.22
Nodes (9): Activity: Website test strategy, site integrity tests, live-site health check, Commit, Files changed, Known issues found (not fixed here, by design), Notes / follow-up, Safety, Tests, What changed (+1 more)

### Community 82 - "Saas Launch Plan Module"
Cohesion: 0.22
Nodes (8): Notes, SEBI License (Do Later — After Graduation), Status Tracker, Step 1 — Deploy (10 minutes), Step 2 — Collect Payment (No Code Needed), Step 3 — Pricing Tiers, Step 4 — Legal Disclaimer (paste on homepage / landing page), TradeALGO SaaS Launch Plan

### Community 83 - "Page Position Module"
Cohesion: 0.42
Nodes (8): page(), test_journal_page_full_flow(), test_journal_page_shows_friendly_errors(), test_position_size_page_defaults_match_the_brothers_numbers(), test_position_size_page_explains_a_trade_that_does_not_fit(), test_position_size_page_rejects_a_stop_above_the_entry(), test_position_size_page_shows_the_gate_from_the_journal(), test_strategy_scanner_page_runs_end_to_end_on_sample_data()

### Community 84 - "Web Dashboard & Server (2)"
Cohesion: 0.22
Nodes (8): 10-minute manual checklist, Expected failures vs real failures, Known issues found while reading the code, One-time setup for the automatic check, Routine, The five layers, TradeALGO: how to check the website works, What was and was not verified when this was written

### Community 85 - "Profitability Engine Monte Module"
Cohesion: 0.36
Nodes (6): evaluate_trades(), max_drawdown(), monte_carlo_trade_paths(), India-first robustness scoring for strategy research; no live execution., RobustnessResult, statistics

### Community 86 - "Activity Chatgpt Log Module"
Cohesion: 0.25
Nodes (8): Activity: Real-Market TradingView Chart Page, Commits, Files changed, Notes, Safety, Tests, What changed, Why

### Community 87 - "Interactive Practice Simulator (5)"
Cohesion: 0.25
Nodes (3): FakeHub, DataFrame, Stands in for algobot.live_market.LiveMarketHub: an in-memory feed with no…

### Community 88 - "Prompt Component"
Cohesion: 0.29
Nodes (5): The prompt a trader can give to any AI chat assistant to turn an idea written…, The reverse mistake would be worse: the AI could invent a plausible-sounding…, Caught a real bug: the prompt's list had fallen behind indicators.py (missing…, test_prompt_does_not_list_a_type_the_engine_does_not_support(), test_prompt_lists_every_indicator_type_the_engine_actually_supports()

### Community 89 - "Activity Chatgpt Log Module (2)"
Cohesion: 0.29
Nodes (7): Activity: Deployment Status Menu Page, Commit, Files changed, Notes / follow-up, Tests, What changed, Why

### Community 90 - "Activity Chatgpt Log Module (3)"
Cohesion: 0.29
Nodes (7): Activity: Fix Deployment Detection, Commit, Files changed, Notes / follow-up, Tests, What changed, Why

### Community 91 - "Activity Chatgpt Log Module (4)"
Cohesion: 0.29
Nodes (7): Activity: Fix deprecated st.components.v1.html, add WhatsApp Signal Alerts, Commits, Files changed, Notes / follow-up, Tests, What changed, Why the project owner was NOT given a live-order-placement feature today

### Community 92 - "Activity Chatgpt Log Module (5)"
Cohesion: 0.29
Nodes (7): Activity: Fix UI CSS NameError, Commit, Files changed, Notes / follow-up, Tests, What changed, Why

### Community 93 - "Activity Chatgpt Log Module (6)"
Cohesion: 0.29
Nodes (7): Activity: Force sidebar routing fix into a fresh deployment, Commit, Files changed, Notes / follow-up, Tests, What changed, Why

### Community 94 - "Activity Chatgpt Log Module (7)"
Cohesion: 0.29
Nodes (7): Activity: Make Practice Market Start Action Visible, Commit, Files changed, Notes / follow-up, Tests, What changed, Why

### Community 95 - "Activity Chatgpt Log Module (8)"
Cohesion: 0.29
Nodes (7): Activity: Move Backtest settings onto the page, Commit, Files changed, Notes, Tests, What changed, Why

### Community 96 - "Interactive Practice Simulator (6)"
Cohesion: 0.29
Nodes (7): Activity: Practice Room Efficiency Pass — Step 1, Commit, Files changed, Notes / follow-up, Tests, What changed, Why

### Community 97 - "Strategy Rule Engine (11)"
Cohesion: 0.29
Nodes (7): Activity: Strategy Builder + Locked Live Trading Controls, Commits, Files changed, Notes / follow-up, Tests, What changed, Why

### Community 98 - "Activity Chatgpt Log Module (9)"
Cohesion: 0.29
Nodes (7): Activity: Trader-Friendly Menu UI, Commit, Files changed, Notes / follow-up, Tests, What changed, Why

### Community 99 - "Monte Carlo Audit & Risk (3)"
Cohesion: 0.33
Nodes (5): Cryptographic Audit Trail (SHA-256 Chain), Detailed Trade Execution Ledger (3 Trades), Executive Summary, Regulatory & Compliance Declaration, TRADEALGO QUANTITATIVE PERFORMANCE & AUDIT DOSSIER

### Community 100 - "Activity Chatgpt Log Module (10)"
Cohesion: 0.33
Nodes (6): Activity: Efficiency Pass — Step 2 (Practice option-pricing cache), Commit, Files changed, Safety, Tests, What changed

### Community 101 - "Activity Chatgpt Log Module (11)"
Cohesion: 0.33
Nodes (6): Activity: Fix Market Charts Syntax Error, Commit, Files changed, Notes, Tests, What changed

### Community 102 - "Activity Chatgpt Log Module (12)"
Cohesion: 0.33
Nodes (6): Activity: Fix Sidebar Page Routing Error, Commits, Files changed, Notes, Tests, What changed

### Community 103 - "Activity Chatgpt Log Module (13)"
Cohesion: 0.33
Nodes (6): Activity: Fix split kill switch (critical), real market data in Backtest, strategy guide page, Commits, Critical bug found and fixed: the kill switch had split into two disconnected instances, Other changes, Still not done (unchanged from before), Tests

### Community 104 - "Activity Chatgpt Log Module (14)"
Cohesion: 0.33
Nodes (6): Activity: Tested and Removed Fake Smoke Test Strategy, Commit, Files changed, Tests, What changed, Why

### Community 105 - "Hosting On Own Module"
Cohesion: 0.33
Nodes (5): A. On his own computer (most private, simplest), B. As a link (he opens it in any browser, even on a phone), Rules for a hosted copy, Running it hosted on your own computer (to test the password screen), Sharing the trading desk with your brother

### Community 106 - "Readme How To Module"
Cohesion: 0.33
Nodes (5): How to use this folder, Important, Integration rule, Recommended organization, TradeALGO UI Components

### Community 107 - "Architecture Specifications (2)"
Cohesion: 0.40
Nodes (5): 18. Failure and Recovery Principles, AI failure, Broker uncertainty, Market feed failure, OpenAlgo failure

### Community 108 - "Architecture Specifications (3)"
Cohesion: 0.40
Nodes (5): 22. Architectural Trade-offs, AI as an analysis layer, OpenAlgo as execution boundary, Shared live market hub, Streamlit

### Community 109 - "Architecture Specifications (4)"
Cohesion: 0.40
Nodes (5): 23. Current End-to-End Workflows, Live Market → AI Analysis, Live Market → Paper Trading, Research → Backtest, Signal → OpenAlgo

### Community 110 - "Streamlit UI Components (4)"
Cohesion: 0.40
Nodes (5): Activity: UI Polish Commit #1, Commit, File changed, Follow-up correction, Intended change

### Community 111 - "Streamlit UI Components (5)"
Cohesion: 0.40
Nodes (5): Activity: UI Polish Commit #2 / Correction, Change, Commit, File changed, Testing status

### Community 112 - "Architecture Specifications (5)"
Cohesion: 0.50
Nodes (4): 11. Data and Persistence, External services, Local / application storage, Session state

### Community 113 - "Architecture Specifications (6)"
Cohesion: 0.50
Nodes (4): 3.1 Presentation Layer, 3.2 Application / State Layer, 3.3 Market Data Layer, 3. Architectural Boundaries

### Community 114 - "Architecture Specifications (7)"
Cohesion: 0.50
Nodes (4): 9. OpenAlgo Execution Architecture, Execution flow, Execution gate, Supported bridge responsibilities

### Community 116 - "Database & Persistence Layer (3)"
Cohesion: 0.50
Nodes (4): Activity: Feedback System Added, Changes made, Current repository status, Important test note

### Community 119 - "Architecture Specifications (8)"
Cohesion: 0.67
Nodes (3): 19. Concurrency Model, Market-data concurrency, User/session concurrency

## Knowledge Gaps
- **239 isolated node(s):** `WebsiteAgent`, `AgentPersona`, `1. System Overview`, `2. High-Level Architecture`, `3.1 Presentation Layer` (+234 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 874 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ConfigError` connect `CLI Parser & Commands (2)` to `Upstox Sandbox & Broker Client`, `Market Data Validation & Feed`, `CLI Parser & Commands (4)`, `Agent V2 Market Module`, `Paper Trading Paperlog Module`, `CLI Parser & Commands (6)`, `Technical Indicators Library`, `Strategy Rule Engine (3)`, `Upstox Sandbox & Broker Client (2)`, `App State & Security Scopes`, `Options Pricing & Greeks (2)`, `Backtesting & Historical Execution (3)`, `App Configuration & Settings (2)`, `App Configuration & Settings (3)`, `Strategy Rule Engine (4)`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `validate_config()` connect `App Configuration & Settings (2)` to `Database & Persistence Layer`, `Market Data Validation & Feed`, `Strategy Rule Engine (2)`, `Paper Trading Paperlog Module`, `Monte Carlo Audit & Risk`, `CLI Parser & Commands (2)`, `Strategy Lab & Research`, `App State & Security Scopes`, `Agent Market Fetch Module`, `Backtesting & Historical Execution`, `App State & Security Scopes (2)`, `Engine Helpers Make Module`, `Agent V2 Market Module`, `Monte Carlo Audit & Risk (2)`, `Market Data Validation & Feed (2)`, `Swarm Synthetic Memory Module`, `App Configuration & Settings`, `Backtesting & Historical Execution (3)`, `App Configuration & Settings (3)`, `App Configuration & Settings (4)`, `Strategy Rule Engine (9)`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `ConfigError` (e.g. with `main()` and `NewEraStrategy`) actually correct?**
  _`ConfigError` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `Journal` (e.g. with `journal_scope()` and `check_gate()`) actually correct?**
  _`Journal` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `WebsiteAgent`, `AgentPersona`, `1. System Overview` to the rest of the system?**
  _239 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Database & Persistence Layer` be split into smaller, more focused modules?**
  _Cohesion score 0.05157894736842105 - nodes in this community are weakly interconnected._
- **Should `Options Pricing & Greeks` be split into smaller, more focused modules?**
  _Cohesion score 0.05707762557077625 - nodes in this community are weakly interconnected._