"""Command line interface.

  python -m algobot sample-data --out data/sample_5min.csv
  python -m algobot check-config configs/demo_sma.yaml
  python -m algobot backtest configs/demo_sma.yaml
  python -m algobot explain configs/demo_rules.yaml
  python -m algobot lookahead-check configs/demo_rules.yaml
"""
from __future__ import annotations

import argparse
import os
import sys

from .audit import format_audit, run_audit
from .config import ConfigError, load_config
from .data import DataError, generate_sample_data, load_csv
from .dataquality import data_quality_report, format_data_quality
from .engine import run_backtest
import datetime as dt

from .experiments import ExperimentLog
from .explain import explain_config
from .lab import format_lab, run_lab
from .journal import (Journal, JournalError, behavior_flags, build_daily_report, format_daily_report_html,
                      format_daily_report_text, format_review, review_stats)
from .lookahead import run_lookahead_checks, selftest
from .gate import build_alert, check_gate
from .openalgo_bridge import INTERVALS, OpenAlgoClient, OpenAlgoError, fetch_history_range, load_env
from .options import breakeven_analysis, format_breakeven
from .prompt import AI_STRATEGY_PROMPT
from .ruin import format_ruin, simulate_ruin
from .runner import check_strategy
from .sizing import NIFTY_LOT_SIZE, format_size, option_position_size
from .report import save_outputs, summary_text
from .strategy import build_strategy
from .worlds import REGIMES, generate_mixed_world, generate_world


def cmd_sample_data(args) -> int:
    df = generate_sample_data(days=args.days, seed=args.seed, start_price=args.start_price)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    df.to_csv(args.out)
    print(f"Wrote {len(df):,} synthetic bars to {args.out}")
    print("This is random-walk test data. It says nothing about real markets.")
    return 0


def cmd_check_config(args) -> int:
    cfg = load_config(args.config)
    check_strategy(cfg)
    print(f"Config OK: {cfg['name']} (strategy: {cfg['strategy']['name']})")
    return 0


def cmd_backtest(args) -> int:
    cfg = load_config(args.config)
    data_path = args.data or cfg["data"]["path"]
    if not data_path:
        raise ConfigError("No data file given. Set data.path in the config or use --data.")
    df = load_csv(data_path)
    strategy = build_strategy(cfg)
    result = run_backtest(df, cfg, strategy)
    print(summary_text(result))
    warnings = [i for i in data_quality_report(df) if i.severity == "WARN"]
    if warnings:
        print(f"Data notes: {len(warnings)} possible problem(s) in the price data. "
              f"Run: python -m algobot check-data {data_path}")
    if not args.no_log:
        log = ExperimentLog(_experiments_path(args))
        try:
            log.record(df, cfg, result)
            print(f"Variants tried on this data so far: {log.count_trials(df)} "
                  "(the more you try, the more a good-looking result can be luck; see: audit)")
        finally:
            log.close_db()
    if not args.no_save:
        outdir = args.out or os.path.join("results", cfg["name"])
        saved = save_outputs(result, outdir, plot=not args.no_plot)
        print("Saved: " + ", ".join(saved))
    return 0


def cmd_explain(args) -> int:
    cfg = load_config(args.config)
    check_strategy(cfg)
    print(f"Plain-English readback of: {cfg['name']}\n")
    print(explain_config(cfg))
    print("\nDoes this match what you meant? If not, fix the config before trusting any result.")
    return 0


def _print_checks(checks) -> bool:
    ok = True
    for c in checks:
        print(f"[{'PASS' if c.passed else 'FAIL'}] {c.name}\n       {c.detail}")
        ok = ok and c.passed
    return ok


def cmd_lookahead(args) -> int:
    if args.selftest:
        df = generate_sample_data(days=30, seed=11)
        checks = selftest(df)
        print("Self-test: checking a strategy that deliberately peeks at the future.")
        print("Every check below MUST fail. If any passes, the checker is broken.\n")
        caught = all(not c.passed for c in checks)
        _print_checks(checks)
        print("\nSelf-test", "OK: the cheat was caught by every check." if caught else "FAILED: the cheat slipped through.")
        return 0 if caught else 1
    if not args.config:
        raise ConfigError("Give a config file, or use --selftest.")
    cfg = load_config(args.config)
    data_path = args.data or cfg["data"]["path"]
    if not data_path:
        raise ConfigError("No data file given. Set data.path in the config or use --data.")
    df = load_csv(data_path)
    print(f"Look-ahead checks for: {cfg['name']}\n")
    ok = _print_checks(run_lookahead_checks(cfg, df))
    print("\nAll clear." if ok else "\nProblem found: do not trust backtests of this strategy until it is fixed.")
    return 0 if ok else 1


def cmd_ai_prompt(args) -> int:
    print(AI_STRATEGY_PROMPT)
    return 0


def cmd_lab(args) -> int:
    cfg = load_config(args.config)
    check_strategy(cfg)
    regimes = [r.strip() for r in args.regimes.split(",")] if args.regimes else None
    for name in regimes or []:
        if name not in REGIMES:
            raise ConfigError(f"Unknown market '{name}'. Choose from: {', '.join(REGIMES)}")
    print(f"Running {args.worlds} fake worlds per market type, {args.days} days each, plus the cheating test...\n")
    print(format_lab(run_lab(cfg, regimes, args.worlds, args.days, args.seed, args.control_worlds)))
    return 0


def cmd_worlds(args) -> int:
    print("Fake market personalities (use with: lab, make-world):\n")
    for r in REGIMES.values():
        print(f"  {r.name:<15} {r.description}")
    print(f"  {'mixed':<15} Changes personality every few days, like a real market (make-world only).")
    return 0


def cmd_make_world(args) -> int:
    if args.regime == "mixed":
        df, segments = generate_mixed_world(args.days, args.seed, args.start_price)
        for name, first, last in segments:
            print(f"  {first:%Y-%m-%d} to {last:%Y-%m-%d}: {name}")
    else:
        if args.regime not in REGIMES:
            raise ConfigError(f"Unknown market '{args.regime}'. Choose from: {', '.join(REGIMES)}, mixed")
        df = generate_world(args.regime, args.days, args.seed, args.start_price)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    df.to_csv(args.out)
    print(f"Wrote {len(df):,} made-up bars to {args.out}. Prices are not real: for testing and practice only.")
    return 0


def _experiments_path(args) -> str:
    return getattr(args, "experiments", None) or os.environ.get("ALGOBOT_EXPERIMENTS", "experiments.db")


def cmd_audit(args) -> int:
    cfg = load_config(args.config)
    data_path = args.data or cfg["data"]["path"]
    if not data_path:
        raise ConfigError("No data file given. Set data.path in the config or use --data.")
    df = load_csv(data_path)
    check_strategy(cfg)
    trials = args.trials
    if trials is None:
        log = ExperimentLog(_experiments_path(args))
        try:
            trials = max(log.count_trials(df), 1)
        finally:
            log.close_db()
    print(f"Running the reality check ({trials} variant(s) tried on this data; "
          f"{args.random_runs} random-entry runs, {args.mc_paths} simulated futures). This can take a minute.\n")
    report = run_audit(df, cfg, trials=trials, n_random=args.random_runs, n_mc=args.mc_paths,
                       ruin_pct=args.ruin_pct)
    print(format_audit(report))
    return 1 if report.failed else 0


def cmd_experiments(args) -> int:
    log = ExperimentLog(_experiments_path(args))
    try:
        runs = log.all_runs()
    finally:
        log.close_db()
    if not runs:
        print("No backtests have been logged yet.")
        return 0
    per_data: dict = {}
    for ts, name, fp, trades, net in runs:
        per_data.setdefault(fp, []).append((ts, name, trades, net))
    for fp, rows in per_data.items():
        print(f"Data {fp}: {len(rows)} run(s)")
        for ts, name, trades, net in rows[-10:]:
            print(f"  {ts}  {name}: {trades} trades, net Rs {net:,.2f}")
    print("\nEvery variant you keep trying on the same data makes the best-looking one more likely to be luck.")
    return 0


def cmd_check_data(args) -> int:
    df = load_csv(args.data)
    issues = data_quality_report(df)
    print(format_data_quality(issues, df))
    return 1 if any(i.severity == "WARN" for i in issues) else 0


def cmd_breakeven(args) -> int:
    try:
        res = breakeven_analysis(
            spot=args.spot, strike=args.strike, days_to_expiry=args.days, iv_pct=args.iv, kind=args.type,
            holding_days=args.hold, lot_size=args.lot_size, spread_per_unit=args.spread,
            charges_round_trip=args.charges, iv_change_pct=args.iv_change, entry_premium=args.entry_premium,
        )
    except ValueError as exc:
        raise ConfigError(str(exc))
    print(format_breakeven(res, args.type, args.lot_size))
    return 0


def cmd_ruin(args) -> int:
    try:
        res = simulate_ruin(
            win_rate=args.win_rate / 100.0, reward_r=args.reward_r, risk_pct=args.risk_pct, n_trades=args.trades,
            ruin_loss_pct=args.ruin_pct, cost_r=args.cost_r, fixed_rupee=not args.compounding,
        )
    except ValueError as exc:
        raise ConfigError(str(exc))
    print(format_ruin(res, args.win_rate / 100.0, args.reward_r, args.risk_pct, args.trades, args.ruin_pct))
    return 0


def _open_journal(args) -> Journal:
    return Journal(args.db or os.environ.get("ALGOBOT_JOURNAL", "journal.db"))


def _make_client() -> OpenAlgoClient:
    """A client for your own OpenAlgo (reads OPENALGO_API_KEY and OPENALGO_HOST from the environment)."""
    return OpenAlgoClient()


def _lot_size(args) -> int:
    if getattr(args, "symbol", None):
        lot = _make_client().lot_size(args.symbol, args.exchange)
        print(f"Lot size from OpenAlgo for {args.symbol}: {lot}")
        return lot
    return args.lot_size


def cmd_size(args) -> int:
    lot_size = _lot_size(args)
    try:
        result = option_position_size(
            max_loss=args.max_loss, entry_premium=args.entry, stop_premium=args.stop,
            lot_size=lot_size, capital=args.capital, est_charges=args.charges,
        )
    except ValueError as exc:
        raise ConfigError(str(exc))
    print(format_size(result, lot_size))
    if not getattr(args, "symbol", None):
        print("\nCheck the lot size on NSE's contract file or your broker: it changes over time. "
              "Or use --symbol to read it from your OpenAlgo.")
    return 0


def cmd_fetch_history(args) -> int:
    df = fetch_history_range(_make_client(), args.symbol, args.exchange, args.interval, args.start, args.end,
                             source=args.source, chunk_days=args.chunk_days)
    parent = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(parent, exist_ok=True)
    df.to_csv(args.out)
    print(f"Saved {len(df):,} bars ({df.index[0]} to {df.index[-1]}) to {args.out}\n")
    print(format_data_quality(data_quality_report(df), df))
    if args.interval not in ("D", "W", "M", "Q", "Y"):
        print("\nNote: brokers usually keep only the last 30 to 90 days of intraday candles. A strategy needs "
              "100+ trades to be judged, so start saving data now (for example with OpenAlgo's Historify) "
              "and re-run this command regularly to build a longer history.")
    return 0


def cmd_alert(args) -> int:
    day = _parse_day(args.date)
    lot_size = _lot_size(args)
    journal = _open_journal(args)
    try:
        gate = check_gate(journal, day, args.max_trades, args.max_daily_loss)
    finally:
        journal.close_db()
    try:
        text, takeable, _ = build_alert(args.instrument, args.entry, args.stop, lot_size, args.capital, args.max_loss,
                                        gate, args.charges, args.max_trades, args.max_daily_loss)
    except ValueError as exc:
        raise ConfigError(str(exc))
    print(text)
    if args.telegram_user:
        _make_client().telegram_notify(args.telegram_user, text)
        print(f"\nSent to Telegram user {args.telegram_user} through OpenAlgo (queued, not confirmed delivered).")
    return 0 if takeable else 1


def cmd_journal(args) -> int:
    j = _open_journal(args)
    try:
        if args.action == "add":
            trade_id = j.add_trade(
                args.instrument, args.side, args.qty, args.entry, opened_at=args.opened_at,
                stop_price=args.stop, target_price=args.target, setup=args.setup or "", notes=args.notes or "",
            )
            print(f"Trade #{trade_id} recorded.")
            if args.stop is None:
                print("Note: no stop-loss was recorded. Trades without a stop are flagged in the daily report.")
        elif args.action == "close":
            t = j.close_trade(args.id, args.exit, closed_at=args.closed_at, charges=args.charges,
                              lessons=args.lessons or "")
            r = "" if t.r_multiple is None else f", {t.r_multiple:+.2f}R"
            print(f"Trade #{t.id} closed. Net Rs {t.net_pnl:,.2f}{r}.")
        else:
            trades = j.all_trades()
            if not trades:
                print("The journal is empty.")
            for t in trades:
                state = f"net {t.net_pnl:,.2f}" if t.is_closed else "OPEN"
                print(f"#{t.id} {t.opened_at} {t.side} {t.qty} {t.instrument} @ {t.entry_price:g}  [{state}]  {t.setup}")
    except JournalError as exc:
        raise ConfigError(str(exc))
    finally:
        j.close_db()
    return 0


def _parse_day(text: str | None) -> dt.date:
    if not text:
        return dt.date.today()
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        raise ConfigError(f"--date must look like 2026-09-21 (got {text!r}).")


def cmd_report(args) -> int:
    day = _parse_day(args.date)
    j = _open_journal(args)
    try:
        rep = build_daily_report(j, day, capital=args.capital, max_loss_per_trade=args.max_loss_per_trade,
                                 max_daily_loss=args.max_daily_loss, max_trades_per_day=args.max_trades)
    finally:
        j.close_db()
    print(format_daily_report_text(rep))
    if args.html:
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(format_daily_report_html(rep))
        print(f"\nHTML report saved to {args.html}")
    return 0


def cmd_review(args) -> int:
    start = _parse_day(args.start) if args.start else None
    end = _parse_day(args.end) if args.end else None
    j = _open_journal(args)
    try:
        trades = j.closed_between(start, end)
    finally:
        j.close_db()
    flags = None
    if any(v is not None for v in (args.max_loss_per_trade, args.max_trades, args.max_daily_loss)):
        flags = behavior_flags(trades, max_loss_per_trade=args.max_loss_per_trade,
                               max_trades_per_day=args.max_trades, max_daily_loss=args.max_daily_loss)
    print(format_review(review_stats(trades), flags))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="algobot", description="Algo trading toolkit (backtesting core).")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("sample-data", help="write synthetic test data (random walk)")
    s.add_argument("--out", default="data/sample_5min.csv")
    s.add_argument("--days", type=int, default=60)
    s.add_argument("--seed", type=int, default=42)
    s.add_argument("--start-price", type=float, default=1000.0)
    s.set_defaults(func=cmd_sample_data)

    c = sub.add_parser("check-config", help="validate a config file without running anything")
    c.add_argument("config")
    c.set_defaults(func=cmd_check_config)

    ap = sub.add_parser("ai-prompt", help="print the prompt that makes an AI write rules in our format")
    ap.set_defaults(func=cmd_ai_prompt)

    e = sub.add_parser("explain", help="print the strategy and limits in plain English")
    e.add_argument("config")
    e.set_defaults(func=cmd_explain)

    la = sub.add_parser("lookahead-check", help="prove a strategy cannot see the future")
    la.add_argument("config", nargs="?")
    la.add_argument("--data", help="CSV file (overrides data.path in the config)")
    la.add_argument("--selftest", action="store_true", help="test the checker itself on a cheating strategy")
    la.set_defaults(func=cmd_lookahead)

    db_parent = argparse.ArgumentParser(add_help=False)
    db_parent.add_argument("--db", help="journal file (default: journal.db, or $ALGOBOT_JOURNAL)")

    sz = sub.add_parser("size", help="how many option lots fit a maximum loss per trade")
    sz.add_argument("--max-loss", type=float, required=True, help="most you accept losing on this trade (Rs)")
    sz.add_argument("--entry", type=float, required=True, help="option premium you plan to buy at")
    sz.add_argument("--stop", type=float, required=True, help="option premium where you exit if wrong")
    sz.add_argument("--lot-size", type=int, default=NIFTY_LOT_SIZE, help="units per lot (default: Nifty 50 = %d)" % NIFTY_LOT_SIZE)
    sz.add_argument("--capital", type=float, help="account size (Rs), to check affordability")
    sz.add_argument("--charges", type=float, default=0.0, help="estimated round-trip charges (Rs) from your broker")
    sz.add_argument("--symbol", help="read the lot size from your OpenAlgo, for example NIFTY28MAR2420800CE")
    sz.add_argument("--exchange", default="NFO", help="exchange for --symbol (default NFO)")
    sz.set_defaults(func=cmd_size)

    fh = sub.add_parser("fetch-history", help="download candles from YOUR OpenAlgo into a CSV for testing")
    fh.add_argument("--symbol", required=True, help="OpenAlgo symbol, for example NIFTY")
    fh.add_argument("--exchange", required=True, help="for example NSE_INDEX for Nifty, NSE for stocks")
    fh.add_argument("--interval", required=True, choices=INTERVALS)
    fh.add_argument("--from", dest="start", required=True, help="first day, like 2026-08-01")
    fh.add_argument("--to", dest="end", required=True, help="last day")
    fh.add_argument("--out", required=True, help="CSV file to write, for example data/nifty_5m.csv")
    fh.add_argument("--source", choices=["api", "db"], default="api",
                    help="api = from the broker, db = OpenAlgo's stored history (Historify)")
    fh.add_argument("--chunk-days", type=int, help="days per request (default depends on the interval)")
    fh.set_defaults(func=cmd_fetch_history)

    al = sub.add_parser("alert", parents=[db_parent], help="size a planned trade, check today's limits, optionally send to Telegram")
    al.add_argument("--instrument", required=True, help='label for the message, for example "NIFTY 24500 CE"')
    al.add_argument("--entry", type=float, required=True, help="option premium you plan to buy at")
    al.add_argument("--stop", type=float, required=True, help="premium where you exit if wrong")
    al.add_argument("--capital", type=float, required=True)
    al.add_argument("--max-loss", type=float, required=True, help="most you accept losing on this trade (Rs)")
    al.add_argument("--max-trades", type=int, help="planned maximum trades per day")
    al.add_argument("--max-daily-loss", type=float, help="daily loss limit (Rs)")
    al.add_argument("--lot-size", type=int, default=NIFTY_LOT_SIZE)
    al.add_argument("--symbol", help="read the lot size from your OpenAlgo")
    al.add_argument("--exchange", default="NFO")
    al.add_argument("--charges", type=float, default=0.0)
    al.add_argument("--date", help="day to check limits for (default: today)")
    al.add_argument("--telegram-user", help="send the message to this Telegram user through your OpenAlgo")
    al.set_defaults(func=cmd_alert)

    jr = sub.add_parser("journal", parents=[db_parent], help="record trades: add, close, list")
    jsub = jr.add_subparsers(dest="action", required=True)
    ja = jsub.add_parser("add", parents=[db_parent], help="record a new trade")
    ja.add_argument("--instrument", required=True, help='for example "NIFTY 24500 CE 25-Sep"')
    ja.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    ja.add_argument("--qty", type=int, required=True, help="units (lots x lot size)")
    ja.add_argument("--entry", type=float, required=True)
    ja.add_argument("--stop", type=float)
    ja.add_argument("--target", type=float)
    ja.add_argument("--setup", help='why, in a few words (for example "resistance breakout")')
    ja.add_argument("--notes")
    ja.add_argument("--opened-at", help="2026-09-21 10:15 (default: now)")
    jc = jsub.add_parser("close", parents=[db_parent], help="close a trade")
    jc.add_argument("id", type=int)
    jc.add_argument("--exit", type=float, required=True)
    jc.add_argument("--charges", type=float, default=0.0, help="total charges for the trade (Rs)")
    jc.add_argument("--lessons", help="what you learned")
    jc.add_argument("--closed-at", help="2026-09-21 14:40 (default: now)")
    jsub.add_parser("list", parents=[db_parent], help="show every trade")
    jr.set_defaults(func=cmd_journal)

    rp = sub.add_parser("report", parents=[db_parent], help="daily P&L report")
    rp.add_argument("--date", help="day to report on, like 2026-09-21 (default: today)")
    rp.add_argument("--capital", type=float)
    rp.add_argument("--max-loss-per-trade", type=float)
    rp.add_argument("--max-daily-loss", type=float)
    rp.add_argument("--max-trades", type=int, help="planned maximum trades per day")
    rp.add_argument("--html", help="also save the report as an HTML file")
    rp.set_defaults(func=cmd_report)

    rv = sub.add_parser("review", parents=[db_parent], help="statistics over closed trades")
    rv.add_argument("--from", dest="start", help="first day, like 2026-09-01")
    rv.add_argument("--to", dest="end", help="last day")
    rv.add_argument("--max-loss-per-trade", type=float, help="your per-trade limit (enables behaviour checks)")
    rv.add_argument("--max-trades", type=int, help="planned maximum trades per day (enables behaviour checks)")
    rv.add_argument("--max-daily-loss", type=float, help="your daily loss limit (enables behaviour checks)")
    rv.set_defaults(func=cmd_review)

    lb = sub.add_parser("lab", help="stress lab: test a strategy across many kinds of fake market, instantly")
    lb.add_argument("config")
    lb.add_argument("--worlds", type=int, default=8, help="fake worlds per market type (default 8)")
    lb.add_argument("--days", type=int, default=15, help="days per world (default 15)")
    lb.add_argument("--seed", type=int, default=100)
    lb.add_argument("--regimes", help="comma list, for example trend,chop,crash (default: all)")
    lb.add_argument("--control-worlds", type=int, default=30, help="worlds for the cheating test (0 to skip)")
    lb.set_defaults(func=cmd_lab)

    wl = sub.add_parser("worlds", help="list the fake market personalities")
    wl.set_defaults(func=cmd_worlds)

    mw = sub.add_parser("make-world", help="write a fake market to a CSV (for practice or testing)")
    mw.add_argument("--regime", required=True, help="one of the worlds, or mixed")
    mw.add_argument("--days", type=int, default=20)
    mw.add_argument("--seed", type=int, default=1)
    mw.add_argument("--start-price", type=float, default=24500.0)
    mw.add_argument("--out", required=True)
    mw.set_defaults(func=cmd_make_world)

    au = sub.add_parser("audit", help="reality check: try to break a strategy before real money does")
    au.add_argument("config")
    au.add_argument("--data", help="CSV file (overrides data.path in the config)")
    au.add_argument("--trials", type=int, help="variants tried on this data (default: taken from the experiment log)")
    au.add_argument("--random-runs", type=int, default=100, help="random-entry benchmark runs (default 100)")
    au.add_argument("--mc-paths", type=int, default=1000, help="simulated futures for the ruin check (default 1000)")
    au.add_argument("--ruin-pct", type=float, default=30.0, help="account loss counted as ruin (default 30)")
    au.add_argument("--experiments", help="experiment log file (default: experiments.db)")
    au.set_defaults(func=cmd_audit)

    ex = sub.add_parser("experiments", help="show how many variants have been tried on each dataset")
    ex.add_argument("--experiments", help="experiment log file (default: experiments.db)")
    ex.set_defaults(func=cmd_experiments)

    cd = sub.add_parser("check-data", help="look for missing bars, spikes, frozen feeds and bad timestamps")
    cd.add_argument("data", help="CSV file")
    cd.set_defaults(func=cmd_check_data)

    be = sub.add_parser("breakeven", help="how far must Nifty move for a bought option to break even?")
    be.add_argument("--spot", type=float, required=True, help="index level now")
    be.add_argument("--strike", type=float, required=True)
    be.add_argument("--type", required=True, choices=["CE", "PE", "ce", "pe"])
    be.add_argument("--days", type=float, required=True, help="calendar days to expiry")
    be.add_argument("--iv", type=float, required=True, help="implied volatility in percent, from the option chain")
    be.add_argument("--hold", type=float, required=True, help="days you plan to hold")
    be.add_argument("--entry-premium", type=float,
                    help="the actual ASK you expect to pay per unit (from the option chain); safer than the model price")
    be.add_argument("--lot-size", type=int, default=NIFTY_LOT_SIZE)
    be.add_argument("--spread", type=float, default=0.0, help="bid-ask gap in premium points")
    be.add_argument("--charges", type=float, default=0.0, help="round-trip charges in Rs for one lot")
    be.add_argument("--iv-change", type=float, default=0.0, help="expected IV change in points (negative = IV crush)")
    be.set_defaults(func=cmd_breakeven)

    ru = sub.add_parser("ruin", help="risk of ruin: how likely is a losing streak to wreck the account?")
    ru.add_argument("--win-rate", type=float, required=True, help="percent of trades that win, for example 45")
    ru.add_argument("--reward-r", type=float, required=True, help="average win as a multiple of the amount risked")
    ru.add_argument("--risk-pct", type=float, required=True, help="percent of capital risked per trade")
    ru.add_argument("--trades", type=int, default=100)
    ru.add_argument("--ruin-pct", type=float, default=50.0, help="account loss counted as ruin (default 50)")
    ru.add_argument("--cost-r", type=float, default=0.0, help="charges per trade in units of the amount risked")
    ru.add_argument("--compounding", action="store_true", help="risk a share of the CURRENT account, not the starting one")
    ru.set_defaults(func=cmd_ruin)

    b = sub.add_parser("backtest", help="run a backtest from a config file")
    b.add_argument("config")
    b.add_argument("--data", help="CSV file (overrides data.path in the config)")
    b.add_argument("--out", help="folder for results (default: results/<name>)")
    b.add_argument("--no-plot", action="store_true", help="skip the equity chart")
    b.add_argument("--no-save", action="store_true", help="only print the summary")
    b.add_argument("--no-log", action="store_true", help="do not record this run in the experiment log")
    b.add_argument("--experiments", help="experiment log file (default: experiments.db)")
    b.set_defaults(func=cmd_backtest)
    return p


def main(argv=None) -> int:
    if not os.environ.get("ALGOBOT_NO_ENV"):
        load_env()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, DataError, OpenAlgoError) as exc:
        print(f"Problem: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
