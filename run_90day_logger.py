#!/usr/bin/env python3
"""TradeALGO 90-Day Paper Trading & SEBI Track Record CLI Runner.

Usage:
  # Run in 24/7 autonomous daemon mode (sleeps outside market hours, wakes up on open):
  python run_90day_logger.py --daemon

  # Run a single immediate evaluation check right now:
  python run_90day_logger.py --once

  # Check current 90-day track record status and ledger:
  python run_90day_logger.py --status
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from algobot.paper_trading_daemon import (
    AUDIT_DIR,
    LEDGER_CSV,
    TRADES_CSV,
    AuditLedger,
    PaperTradingDaemon,
    get_market_session_status,
)


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def print_status(config_path: str, symbol: str) -> None:
    ledger = AuditLedger(LEDGER_CSV)
    days_done = ledger.get_days_logged()
    session = get_market_session_status()

    print("\n" + "=" * 76)
    print(" [STATUS] TRADEALGO 90-DAY AUDIT TRACK RECORD STATUS")
    print("=" * 76)
    print(f" Strategy Config:   {config_path}")
    print(f" Target Market:     {symbol}")
    print(f" Progress:          {days_done} / 90 Market Days Completed ({(days_done/90)*100:.1f}%)")
    print(f" Market Session:    {'[OPEN] (09:15-15:30 IST)' if session.is_open else '[CLOSED]'}")
    print(f" Current IST Time:  {session.now_ist.strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f" Master Ledger:     {LEDGER_CSV}")
    print(f" Trade Audit CSV:   {TRADES_CSV}")

    last = ledger.get_last_entry()
    if last:
        print("\n--- LATEST RECORDED TRADING DAY ---")
        print(f" Date:              {last.get('date')}")
        print(f" Starting Capital:  Rs. {float(last.get('starting_equity', 0)):,.2f}")
        print(f" Ending Equity:     Rs. {float(last.get('ending_equity', 0)):,.2f}")
        print(f" Daily Net P&L:     Rs. {float(last.get('daily_net_pnl', 0)):>+,.2f}")
        print(f" Cumulative P&L:    Rs. {float(last.get('cumulative_net_pnl', 0)):>+,.2f}")
        print(f" Cumulative Return: {float(last.get('cumulative_return_pct', 0)):>+.2f}%")
        print(f" Trades / Wins:     {last.get('trade_count')} / {last.get('win_count')}")
        print(f" SHA-256 Hash:      {str(last.get('audit_hash'))[:24]}...")
    else:
        print("\n * No daily closing rows finalized yet. Start the daemon to record Day 1.")
    print("=" * 76 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TradeALGO 90-Day SEBI-Compliant Paper Trading Logger & 24/7 Daemon"
    )
    parser.add_argument(
        "--config",
        default="configs/stock_pullback.yaml",
        help="Path to strategy config YAML (default: configs/stock_pullback.yaml)",
    )
    parser.add_argument(
        "--symbol",
        default="Reliance",
        help="Display market symbol (default: Reliance)",
    )
    parser.add_argument(
        "--ticker",
        default="RELIANCE.NS",
        help="Market data ticker (default: RELIANCE.NS)",
    )
    parser.add_argument(
        "--interval",
        default="5m",
        help="Candle timeframe interval (default: 5m)",
    )
    parser.add_argument(
        "--period",
        default="1mo",
        help="Historical lookback window (default: 1mo)",
    )
    parser.add_argument(
        "--poll",
        type=int,
        default=60,
        help="Seconds between evaluation ticks during market hours (default: 60)",
    )
    parser.add_argument(
        "--target-days",
        type=int,
        default=90,
        help="Target trading days for compliance certification (default: 90)",
    )
    parser.add_argument(
        "--multi-asset",
        action="store_true",
        help="Monitor winning bluechip portfolio (Reliance, HDFC Bank, ICICI Bank, Nifty 50)",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously 24/7 (sleeps outside market hours, wakes up on open)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single evaluation pass immediately and exit",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current 90-day track record status and exit",
    )

    args = parser.parse_args()

    if args.status:
        print_status(args.config, args.symbol)
        return

    portfolio_assets = None
    if args.multi_asset:
        portfolio_assets = [
            {"symbol": "Reliance", "ticker": "RELIANCE.NS", "qty": 50},
            {"symbol": "HDFC Bank", "ticker": "HDFCBANK.NS", "qty": 100},
            {"symbol": "ICICI Bank", "ticker": "ICICIBANK.NS", "qty": 100},
            {"symbol": "Maruti Suzuki", "ticker": "MARUTI.NS", "qty": 10},
            {"symbol": "M&M", "ticker": "M&M.NS", "qty": 40},
        ]

    daemon = PaperTradingDaemon(
        config_path=args.config,
        symbol=args.symbol,
        ticker=args.ticker,
        interval=args.interval,
        period=args.period,
        poll_interval_seconds=args.poll,
        target_days=args.target_days,
        assets=portfolio_assets,
    )

    if args.once:
        print(f"\n[MANUAL TICK] Evaluating {args.symbol} ({args.ticker}) with {args.config}...")
        account, open_snapshot, summary, status_info = daemon.evaluate_market_tick()
        daemon.print_terminal_banner(account, open_snapshot, summary, status_info)
        session = get_market_session_status()
        if session.now_ist.time() >= dt.time(15, 30) and not session.is_weekend:
            daemon.check_and_finalize_daily_close(session.now_ist)
        daemon.export_trade_audit_csv()
        return

    # Default or --daemon: continuous 24/7 loop
    daemon.run_continuous_loop()


if __name__ == "__main__":
    main()
