"""Full strategy validation suite: backtest, paper trade evaluation, and audit check.

Run this to get a complete picture of whether conservative_pullback is working.
"""
import datetime as dt
import sys
from zoneinfo import ZoneInfo

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import pandas as pd

from algobot.config import load_config
from algobot.live_data import fetch_ohlc, LiveDataError
from algobot.paper_trading import PaperLog, evaluate, log_new_trades, run_key_for, split_open_and_closed
from algobot.audit import run_audit, format_audit

IST = ZoneInfo("Asia/Kolkata")
CONFIG = "configs/conservative_pullback.yaml"
SYMBOL = "Nifty 50"
TICKER = "^NSEI"
DB = "paper_trades.db"

SEP = "=" * 72


def section(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def run_backtest_check(cfg, df):
    section("1/3  BACKTEST (last 30 days of 5-min candles)")
    result = evaluate(cfg, df)
    t = result.trades
    if t.empty:
        print("  No trades fired in this window. Strategy is too selective.")
        return result

    closed_t = t[t["exit_reason"] != "end_of_data"]
    total = len(closed_t)
    wins = int((closed_t["net_pnl"] > 0).sum())
    net = float(closed_t["net_pnl"].sum())
    gross = float(closed_t["gross_pnl"].sum())
    costs = float(closed_t["costs"].sum())
    win_rate = wins / total * 100 if total else 0
    best = float(closed_t["net_pnl"].max()) if total else 0
    worst = float(closed_t["net_pnl"].min()) if total else 0

    print(f"  Candles analysed : {len(df)} bars  |  Bar size: 5 minutes")
    print(f"  Trades completed : {total}")
    print(f"  Win rate         : {win_rate:.1f}%  ({wins} wins / {total} trades)")
    print(f"  Gross P&L        : Rs. {gross:>+10,.2f}")
    print(f"  Statutory costs  : Rs. {costs:>10,.2f}  (STT + GST + brokerage + slippage)")
    print(f"  Net P&L          : Rs. {net:>+10,.2f}")
    print(f"  Best trade       : Rs. {best:>+10,.2f}")
    print(f"  Worst trade      : Rs. {worst:>+10,.2f}")

    if total > 0:
        print(f"\n  Last 5 trades:")
        cols = ["entry_time", "exit_time", "side", "entry_price", "exit_price", "net_pnl", "exit_reason"]
        print(closed_t[cols].tail(5).to_string(index=False))

    verdict = "PASS" if net > 0 and win_rate >= 40 else "WARN" if net > 0 else "FAIL"
    print(f"\n  Backtest Verdict: [{verdict}]  Net={net:+,.2f}  WinRate={win_rate:.0f}%")
    return result


def run_paper_trade_check(cfg, df):
    section("2/3  PAPER TRADING (persistent log against live-delayed prices)")
    result = evaluate(cfg, df)
    open_snap, closed = split_open_and_closed(result)
    run_key = run_key_for(cfg, SYMBOL, "5 minutes (intraday)")
    log = PaperLog(DB)
    added = log_new_trades(log, run_key, SYMBOL, closed)
    account = log.virtual_ledger(run_key, cfg["capital"], open_snap)
    summary = log.summary(run_key)

    print(f"  New trades added to DB : {added}")
    print(f"  Starting capital       : Rs. {account['starting_capital']:>10,.2f}")
    print(f"  Realized P&L (logged)  : Rs. {account['realized_pnl']:>+10,.2f}")
    print(f"  Unrealized P&L now     : Rs. {account['unrealized_pnl']:>+10,.2f}")
    print(f"  Virtual account value  : Rs. {account['virtual_equity']:>10,.2f}")
    print(f"  Total trades logged    : {summary['trades']}")
    wr = summary["win_rate_pct"]
    print(f"  Win rate (all-time)    : {wr:.1f}%" if wr is not None else "  Win rate: N/A (no closed trades yet)")

    if open_snap:
        side = open_snap.get("side", "?")
        ep = float(open_snap.get("entry_price", 0))
        pnl = float(open_snap.get("net_pnl", 0))
        print(f"\n  [LIVE POSITION] {side} @ Rs. {ep:,.2f}  |  Unrealized: Rs. {pnl:+,.2f}")
    else:
        print("\n  [LIVE POSITION] FLAT — no open trade right now.")

    return account, summary


def run_audit_check(cfg, df):
    section("3/3  SEBI AUDIT REALITY CHECK (stress tests + random baseline)")
    try:
        report = run_audit(df, cfg)
        print(format_audit(report))
    except Exception as e:
        print(f"  Audit engine error: {e}")



def main():
    print(f"\n{'#'*72}")
    print(f"  TRADEALGO FULL STRATEGY VALIDATION SUITE")
    print(f"  Strategy : {CONFIG}")
    print(f"  Market   : {SYMBOL} ({TICKER})")
    print(f"  Time     : {dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"{'#'*72}")

    cfg = load_config(CONFIG)
    print(f"\n  Loading market data from Yahoo Finance (delayed)...")
    try:
        df = fetch_ohlc(TICKER, "5m", "1mo")
        print(f"  Fetched {len(df)} candles. Latest close: Rs. {df['close'].iloc[-1]:,.2f}")
    except LiveDataError as e:
        print(f"  [ERROR] Could not fetch market data: {e}")
        sys.exit(1)

    run_backtest_check(cfg, df)
    run_paper_trade_check(cfg, df)
    run_audit_check(cfg, df)

    print(f"\n{'#'*72}")
    print("  VALIDATION COMPLETE. See results above.")
    print(f"  90-day logger status: python run_90day_logger.py --status")
    print(f"{'#'*72}\n")


if __name__ == "__main__":
    main()
