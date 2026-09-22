import numpy as np
import pandas as pd
import pytest

from algobot.audit import (FAIL, PASS, SKIP, WARN, RandomEntry, check_concentration, check_out_of_sample,
                           check_ruin, check_sample_size, check_significance, format_audit, monte_carlo,
                           parameter_variants, run_audit, scale_costs)
from algobot.config import validate_config
from algobot.data import generate_sample_data
from algobot.engine import run_backtest
from algobot.experiments import ExperimentLog, config_hash, fingerprint_df, required_t_stat
from algobot.strategy import build_strategy


def trades_with(nets):
    n = len(nets)
    idx = pd.date_range("2025-01-06 10:00", periods=n, freq="30min")
    return pd.DataFrame({"entry_time": idx, "exit_time": idx + pd.Timedelta(minutes=5),
                         "net_pnl": np.asarray(nets, dtype=float)})


def exact_normal(n, mean, std, seed=0):
    z = np.random.default_rng(seed).normal(size=n)
    return (z - z.mean()) / z.std(ddof=1) * std + mean


MOMENTUM = {
    "name": "momentum_demo", "capital": 100000,
    "strategy": {"name": "rules", "quantity": 10, "allow_short": True, "stop_loss_pct": 0.6, "target_pct": 1.2,
                 "params": {"indicators": [],
                            "entry_long": "close > open and close_prev > open_prev", "exit_long": "close < open",
                            "entry_short": "close < open and close_prev < open_prev", "exit_short": "close > open"}},
    "risk": {"max_daily_loss": 3000},
}


# -------------------------------------------------------------- the pieces
def test_required_t_stat_rises_with_the_number_of_tries():
    assert required_t_stat(1) == 2.0
    assert required_t_stat(10) == pytest.approx(2.146, abs=0.01)
    assert required_t_stat(100) == pytest.approx(3.035, abs=0.01)      # the ~3.0 bar academics ask for
    assert required_t_stat(1000) > required_t_stat(100)


@pytest.mark.parametrize("n, status", [(10, FAIL), (29, FAIL), (30, WARN), (99, WARN), (100, PASS)])
def test_sample_size_thresholds(n, status):
    assert check_sample_size(trades_with(np.ones(n))).status == status


def test_same_result_passes_alone_but_not_after_many_tries():
    trades = trades_with(exact_normal(100, mean=10, std=40))        # t-statistic is exactly 2.5
    assert check_significance(trades, trials=1, seed=1).status == PASS
    assert check_significance(trades, trials=100, seed=1).status == WARN   # bar is now about 3.0


def test_losing_and_flat_results_fail_or_skip():
    assert check_significance(trades_with(exact_normal(100, -5, 40)), 1, 1).status == FAIL
    assert check_significance(trades_with(np.full(50, 3.0)), 1, 1).status == SKIP
    assert check_significance(trades_with([5.0]), 1, 1).status == SKIP


def test_concentration_flags_a_lucky_streak():
    lucky = np.concatenate([[5000.0], np.full(99, -10.0)])           # one trade carries everything
    assert check_concentration(trades_with(lucky)).status == FAIL
    spread = exact_normal(100, mean=20, std=15)
    assert check_concentration(trades_with(spread)).status == PASS
    assert check_concentration(trades_with(np.full(100, -1.0))).status == SKIP


def test_out_of_sample_catches_a_strategy_that_stopped_working():
    df = generate_sample_data(days=10, seed=1)
    entry = pd.date_range(df.index[0], df.index[-1], periods=60)
    good_then_bad = np.concatenate([np.full(30, 40.0), np.full(30, -40.0)])
    trades = pd.DataFrame({"entry_time": entry, "exit_time": entry, "net_pnl": good_then_bad})
    assert check_out_of_sample(df, trades, 0.5).status == FAIL


def test_scale_costs_multiplies_charges_but_not_rates_that_apply_to_fees():
    cfg = validate_config({"costs": {"brokerage_pct": 0.03, "brokerage_cap": 20, "slippage_bps": 2, "gst_pct": 18}})
    scaled = scale_costs(cfg, 2.0)
    assert scaled["costs"]["brokerage_pct"] == pytest.approx(0.06)
    assert scaled["costs"]["brokerage_cap"] == 40 and scaled["costs"]["slippage_bps"] == 4
    assert scaled["costs"]["gst_pct"] == 18 and scaled["costs"]["brokerage_flat"] is None
    assert cfg["costs"]["brokerage_pct"] == 0.03                       # original untouched


def test_random_entry_benchmark_holds_for_a_fixed_number_of_bars():
    st = RandomEntry(prob=1.0, hold_bars=3, allow_short=False, seed=1)
    assert st.on_bar(0, None, 0) == "BUY"
    assert [st.on_bar(i, None, 1) for i in (1, 2, 3)] == [None, None, "EXIT"]
    assert RandomEntry(0.0, 3, False, 1).on_bar(0, None, 0) is None


def test_monte_carlo_extremes():
    winners = monte_carlo(np.full(50, 100.0), capital=10000, ruin_pct=30, n_paths=200, seed=1)
    assert winners["p_ruin"] == 0 and winners["p_loss"] == 0
    losers = monte_carlo(np.full(50, -1000.0), capital=10000, ruin_pct=30, n_paths=200, seed=1)
    assert losers["p_ruin"] == 1.0 and losers["final_median"] < 0


def test_ruin_check_reflects_a_small_account_with_big_losses():
    # Same trades, small account: a 3-loss streak of Rs 1,000 wipes out 30% of Rs 10,000.
    nets = np.concatenate([np.full(40, -1000.0), np.full(60, 700.0)])
    assert check_ruin(trades_with(nets), capital=10000, ruin_pct=30, paths=500, seed=1).status == FAIL
    assert check_ruin(trades_with(nets), capital=1_000_000, ruin_pct=30, paths=500, seed=1).status == PASS


def test_parameter_variants_cover_every_numeric_setting():
    cfg = validate_config({"strategy": {"name": "sma_crossover", "params": {"fast": 10, "slow": 30},
                                        "stop_loss_pct": 0.5, "target_pct": 1.0}})
    labels = [label for label, _ in parameter_variants(cfg)]
    assert labels == ["fast 10 -> 8", "fast 10 -> 12", "slow 30 -> 24", "slow 30 -> 36",
                      "stop_loss_pct 0.5 -> 0.4", "stop_loss_pct 0.5 -> 0.6",
                      "target_pct 1 -> 0.8", "target_pct 1 -> 1.2"]
    rules = validate_config({"strategy": {"name": "rules", "params": {
        "indicators": [{"name": "a", "type": "ema", "period": 9}, {"name": "v", "type": "vwap"}],
        "entry_long": "close > a"}}})
    assert [label for label, _ in parameter_variants(rules)] == ["a period 9 -> 7", "a period 9 -> 11"]


# ------------------------------------------------- experiment log (cherry-picking counter)
def test_experiment_log_counts_distinct_variants_per_dataset():
    df1, df2 = generate_sample_data(days=3, seed=1), generate_sample_data(days=3, seed=2)
    log = ExperimentLog()
    base = validate_config({"strategy": {"name": "sma_crossover", "params": {"fast": 5, "slow": 20}}})
    other = validate_config({"strategy": {"name": "sma_crossover", "params": {"fast": 6, "slow": 20}}})
    res = run_backtest(df1, base, build_strategy(base))
    log.record(df1, base, res)
    log.record(df1, base, res)                       # same setup again is NOT a new variant
    log.record(df1, other, run_backtest(df1, other, build_strategy(other)))
    log.record(df2, base, res)
    assert log.count_trials(df1) == 2 and log.count_trials(df2) == 1
    assert fingerprint_df(df1) != fingerprint_df(df2) and config_hash(base) != config_hash(other)
    renamed = {**base, "name": "another name"}
    assert config_hash(renamed) == config_hash(base)   # a new label is not a new idea


# ---------------------------------------------- the whole audit, tried on things that should and should not pass
def test_audit_rejects_pure_noise():
    for seed in (1, 2):
        df = generate_sample_data(days=20, seed=seed)
        report = run_audit(df, validate_config(MOMENTUM), n_random=20, n_mc=200)
        assert report.failed and report.verdict.startswith("NOT READY")


def test_audit_recognises_a_real_edge():
    for seed in (1, 2):
        df = generate_sample_data(days=20, seed=seed, autocorr=0.6, vol_per_bar=0.003)
        report = run_audit(df, validate_config(MOMENTUM), n_random=20, n_mc=200)
        assert not report.failed, format_audit(report)
        assert all(c.status == PASS for c in report.checks), format_audit(report)


def test_audit_is_not_fooled_by_the_best_of_many_noise_variants():
    zero = dict(brokerage_pct=0, brokerage_cap=None, stt_sell_pct=0, exchange_txn_pct=0, sebi_fee_pct=0,
                stamp_buy_pct=0, gst_pct=0, slippage_bps=0)

    def cfg(fast, slow):
        return validate_config({"name": "x", "capital": 100000, "costs": zero, "risk": {"max_daily_loss": 3000},
                                "strategy": {"name": "sma_crossover", "quantity": 10, "allow_short": True,
                                             "stop_loss_pct": 0.6, "target_pct": 1.2,
                                             "params": {"fast": fast, "slow": slow}}})
    grid = [(f, s) for f in (3, 5, 8) for s in (15, 25, 40, 60)]
    for seed in (100, 101, 102):
        df = generate_sample_data(days=20, seed=seed)
        best = max((run_backtest(df, cfg(f, s), build_strategy(cfg(f, s))).metrics["net_pnl"], f, s) for f, s in grid)
        report = run_audit(df, cfg(best[1], best[2]), trials=len(grid), n_random=30, n_mc=200)
        assert not report.verdict.startswith("PASSED"), format_audit(report)


def test_audit_report_text_is_readable():
    df = generate_sample_data(days=10, seed=3)
    text = format_audit(run_audit(df, validate_config(MOMENTUM), n_random=10, n_mc=100))
    assert text.startswith("REALITY CHECK") and "VERDICT:" in text and "[FAIL]" in text
    assert "Passing does not prove" in text
