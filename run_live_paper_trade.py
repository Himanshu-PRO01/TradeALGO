import argparse
import os
import sys
import time
import pandas as pd
from algobot.config import load_config
from algobot.data import load_csv
from algobot.live_data import fetch_ohlc, MARKETS, INTERVALS
from algobot.paper_trading import PaperLog, evaluate, log_new_trades, run_key_for, split_open_and_closed
from algobot.learning import analyze_and_learn_from_trades, load_memory

def run_paper_trading_now(
    config_path="configs/conservative_10k_options.yaml",
    symbol="Nifty 50",
    ticker="^NSEI",
    interval="5m",
    period="1mo",
    replay_path=None,
):
    print("=" * 75)
    print("TRADEALGO PAPER TRADING EXECUTION ENGINE")
    print(f"Config:    {config_path}")
    print(f"Market:    {symbol} ({ticker}) | Timeframe: {interval}")
    print("=" * 75)

    cfg = load_config(config_path)
    if replay_path:
        print(f"Loading replay market data from {replay_path}...")
        df = load_csv(replay_path)
        data_src = f"Replay CSV ({replay_path})"
    else:
        print(f"Fetching real market prices for {symbol} ({ticker})...")
        df = fetch_ohlc(ticker, interval, period)
        data_src = f"Yahoo Finance Live Delayed ({period})"

    latest_ts = df.index[-1]
    latest_close = df['close'].iloc[-1]
    print(f"Data Feed: {data_src}")
    print(f"Candles:   {len(df)} bars (Latest: {latest_ts}, Close: Rs. {latest_close:,.2f})")
    print(f"Account:   Starting Capital: Rs. {cfg['capital']:,.2f} | Lot Size: {cfg['strategy']['quantity']} units")
    print(f"Risk:      Daily Loss Limit: Rs. {cfg['risk']['max_daily_loss']:,} | Max Trades/Day: {cfg['risk']['max_trades_per_day']}")
    print("-" * 75)

    # Run paper evaluation
    result = evaluate(cfg, df)
    open_snapshot, closed = split_open_and_closed(result)
    run_key = run_key_for(cfg, symbol, "5 minutes (intraday)")

    # Log to persistent SQLite paper_trades.db
    db_path = os.environ.get("ALGOBOT_PAPER_LOG", "paper_trades.db")
    log = PaperLog(db_path)
    added = log_new_trades(log, run_key, symbol, closed)
    print(f"Evaluated: {len(result.trades)} total trade(s) detected across market data.")
    print(f"Database:  {added} newly finished trade(s) saved to paper_trades.db.")

    # Check open position right now
    if open_snapshot:
        side = open_snapshot['side']
        entry_p = open_snapshot['entry_price']
        entry_t = open_snapshot['entry_time']
        cur_pnl = open_snapshot.get('net_pnl', 0.0)
        pnl_sign = "+" if cur_pnl >= 0 else ""
        print(f"\n[CURRENT LIVE POSITION] ACTIVE {side} @ Rs. {entry_p:,.2f} (Time: {entry_t})")
        print(f"                        Unrealized Net P&L: {pnl_sign}Rs. {cur_pnl:,.2f}")
    else:
        print("\n[CURRENT LIVE POSITION] Strategy is FLAT (no open position; scanning for signal).")

    # Virtual Account Ledger & Performance Summary
    summary = log.summary(run_key)
    account = log.virtual_ledger(run_key, cfg['capital'], open_snapshot)
    print("\n--- PAPER TRADING ACCOUNT STATEMENT ---")
    print(f"Starting Capital:     Rs. {account['starting_capital']:>12,.2f}")
    print(f"Realized P&L:         Rs. {account['realized_pnl']:>12,.2f}")
    print(f"Unrealized P&L:       Rs. {account['unrealized_pnl']:>12,.2f}")
    print(f"Virtual Account Balance: Rs. {account['virtual_balance']:>10,.2f}")
    print(f"Virtual Total Equity: Rs. {account['virtual_equity']:>12,.2f}")
    print(f"Total Logged Trades:  {summary['trades']}")
    print(f"Win Rate:             {summary['win_rate_pct']:.1f}%" if summary['win_rate_pct'] is not None else "Win Rate: N/A")
    print(f"Best / Worst Trade:   Rs. {summary['best']:,.2f} / Rs. {summary['worst']:,.2f}" if summary['trades'] else "Best / Worst Trade: N/A")

    history = log.all_trades(run_key)
    if not history.empty:
        print("\n--- RECENT COMPLETED PAPER TRADES ---")
        display_cols = ["entry_time", "exit_time", "side", "entry_price", "exit_price", "gross_pnl", "costs", "net_pnl", "exit_reason"]
        print(history[display_cols].tail(5).to_string(index=False))

        # Run automated learning from trades
        lessons = analyze_and_learn_from_trades(history)
        if lessons:
            print(f"\n--- SYSTEM LEARNING & LESSONS ({len(lessons)} extracted) ---")
            for l in lessons:
                print(f"  * [{l.category.upper()}] {l.message}")
                print(f"    Action: {l.action}")
                print(f"    Evidence: {l.evidence}")

    print("=" * 75)
    return account, open_snapshot, summary

def main():
    parser = argparse.ArgumentParser(description="TradeALGO Live Paper Trading Runner")
    parser.add_argument("--config", default="configs/conservative_10k_options.yaml", help="Path to config YAML")
    parser.add_argument("--symbol", default="Nifty 50", help="Market name")
    parser.add_argument("--ticker", default="^NSEI", help="Yahoo Finance ticker")
    parser.add_argument("--interval", default="5m", help="Candle interval (e.g. 5m, 15m)")
    parser.add_argument("--period", default="1mo", help="Lookback period (e.g. 5d, 1mo)")
    parser.add_argument("--replay", default=None, help="Path to historical CSV for replay testing")
    parser.add_argument("--watch", type=int, default=0, help="Run continuously every N seconds (0 = run once)")
    args = parser.parse_args()

    if args.watch > 0:
        print(f"Starting continuous paper trading loop (refreshing every {args.watch}s)... Press Ctrl+C to stop.")
        try:
            while True:
                run_paper_trading_now(
                    config_path=args.config,
                    symbol=args.symbol,
                    ticker=args.ticker,
                    interval=args.interval,
                    period=args.period,
                    replay_path=args.replay,
                )
                print(f"\nSleeping for {args.watch} seconds until next bar poll...\n")
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\nPaper trading watch stopped by user.")
    else:
        run_paper_trading_now(
            config_path=args.config,
            symbol=args.symbol,
            ticker=args.ticker,
            interval=args.interval,
            period=args.period,
            replay_path=args.replay,
        )

if __name__ == "__main__":
    main()

