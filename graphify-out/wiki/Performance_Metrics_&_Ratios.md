# Performance Metrics & Ratios

> 19 nodes

## Key Concepts

- **compute_metrics()** (16 connections) — `algobot/metrics.py`
- **test_metrics_streaks_and_exposure.py** (11 connections) — `tests/test_metrics_streaks_and_exposure.py`
- **_trades()** (6 connections) — `tests/test_metrics_streaks_and_exposure.py`
- **_exposure_pct()** (5 connections) — `algobot/metrics.py`
- **_flat_equity()** (5 connections) — `tests/test_metrics_streaks_and_exposure.py`
- **_streaks()** (4 connections) — `algobot/metrics.py`
- **test_exposure_pct_is_capped_at_100()** (4 connections) — `tests/test_metrics_streaks_and_exposure.py`
- **test_exposure_pct_is_held_time_over_total_span()** (4 connections) — `tests/test_metrics_streaks_and_exposure.py`
- **test_win_streak_and_loss_streak_are_longest_consecutive_runs()** (4 connections) — `tests/test_metrics_streaks_and_exposure.py`
- **test_zero_pnl_trade_counts_as_a_loss_for_streaks()** (4 connections) — `tests/test_metrics_streaks_and_exposure.py`
- **Series** (3 connections)
- **test_metrics_on_known_trades()** (2 connections) — `tests/test_data_metrics_integration.py`
- **test_metrics_with_no_trades()** (2 connections) — `tests/test_data_metrics_integration.py`
- **test_no_trades_gives_zero_streaks_and_zero_exposure()** (2 connections) — `tests/test_metrics_streaks_and_exposure.py`
- **DataFrame** (2 connections)
- **Longest run of consecutive winning trades, and of consecutive non-winning…** (1 connections) — `algobot/metrics.py`
- **Percentage of the tested time span spent holding a position (either side).…** (1 connections) — `algobot/metrics.py`
- **Tests for the win/loss-streak and exposure additions to compute_metrics().** (1 connections) — `tests/test_metrics_streaks_and_exposure.py`
- **Build a minimal trades frame: one row per net_pnl, each `minutes_held` long,…** (1 connections) — `tests/test_metrics_streaks_and_exposure.py`

## Relationships

- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (6 shared connections)
- [Market Data Validation & Feed (3)](Market_Data_Validation_&_Feed_3.md) (3 shared connections)
- [Backtesting & Historical Execution (2)](Backtesting_&_Historical_Execution_2.md) (1 shared connections)

## Source Files

- `algobot/metrics.py`
- `tests/test_data_metrics_integration.py`
- `tests/test_metrics_streaks_and_exposure.py`

## Audit Trail

- EXTRACTED: 44 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*