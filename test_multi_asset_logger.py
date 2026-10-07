"""Test multi-asset paper trading evaluation and logging.

Monitors:
- Nifty 50 (^NSEI)
- Bank Nifty (^NSEBANK)
- Fin Nifty (NIFTY_FIN_SERVICE.NS)
- Reliance (RELIANCE.NS)
- HDFC Bank (HDFCBANK.NS)
"""
import copy
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from algobot.config import load_config
from algobot.live_data import fetch_ohlc, LiveDataError
from algobot.paper_trading import (
    PaperLog,
    evaluate,
    log_new_trades,
    run_key_for,
    split_open_and_closed,
)

CONFIG_PATH = "configs/conservative_pullback.yaml"
DB_PATH = "paper_trades.db"

ASSETS = [
    {"symbol": "Nifty 50", "ticker": "^NSEI", "qty": 25},
    {"symbol": "Bank Nifty", "ticker": "^NSEBANK", "qty": 15},
    {"symbol": "Fin Nifty", "ticker": "NIFTY_FIN_SERVICE.NS", "qty": 25},
    {"symbol": "Reliance", "ticker": "RELIANCE.NS", "qty": 50},
    {"symbol": "HDFC Bank", "ticker": "HDFCBANK.NS", "qty": 100},
]


def test_multi_asset():
    print("=" * 76)
    print("  TRADEALGO MULTI-ASSET LOGGING TEST")
    print("=" * 76)

    cfg = load_config(CONFIG_PATH)
    log = PaperLog(DB_PATH)

    total_closed = 0
    total_added = 0
    results = []

    for a in ASSETS:
        symbol = a["symbol"]
        ticker = a["ticker"]
        qty = a["qty"]

        asset_cfg = copy.deepcopy(cfg)
        asset_cfg["strategy"]["quantity"] = qty

        print(f"\n[SCANNING] {symbol} ({ticker}) [Qty: {qty}]...")
        try:
            df = fetch_ohlc(ticker, "5m", "1mo")
        except LiveDataError as e:
            print(f"  Failed to fetch: {e}")
            continue

        res = evaluate(asset_cfg, df)
        open_snap, closed = split_open_and_closed(res)

        run_key = run_key_for(asset_cfg, symbol, "5 minutes (intraday)")
        added = log_new_trades(log, run_key, symbol, closed)
        summary = log.summary(run_key)

        n_closed = len(closed)
        total_closed += n_closed
        total_added += added

        net_pnl = float(closed["net_pnl"].sum()) if not closed.empty else 0.0
        wins = int((closed["net_pnl"] > 0).sum()) if not closed.empty else 0
        wr = (wins / n_closed * 100.0) if n_closed else 0.0

        pos_str = "FLAT"
        if open_snap:
            pos_str = f"{open_snap.get('side')} @ {open_snap.get('entry_price'):,.2f} (P&L: {open_snap.get('net_pnl'):+,.2f})"

        print(f"  Bars Loaded:       {len(df)}")
        print(f"  Recent Closed:     {n_closed} trades (Wins: {wins}, Net: Rs. {net_pnl:>+,.2f})")
        print(f"  New Logged to DB:  {added}")
        print(f"  All-Time DB Trades:{summary['trades']} (Win Rate: {summary.get('win_rate_pct')}%)")
        print(f"  Current Position:  {pos_str}")

        results.append({
            "symbol": symbol,
            "ticker": ticker,
            "bars": len(df),
            "trades": n_closed,
            "wins": wins,
            "win_rate": wr,
            "net_pnl": net_pnl,
            "position": pos_str,
        })

    print("\n" + "=" * 76)
    print("  MULTI-ASSET PORTFOLIO SUMMARY")
    print("=" * 76)
    print(f"{'Asset':<14} {'Ticker':<22} {'Trades':<8} {'Win Rate':<10} {'Net P&L':<14} {'Position'}")
    print("-" * 76)
    portfolio_net = 0.0
    for r in results:
        portfolio_net += r["net_pnl"]
        print(f"{r['symbol']:<14} {r['ticker']:<22} {r['trades']:<8} {r['win_rate']:>6.1f}%    Rs. {r['net_pnl']:>+9,.2f}  {r['position']}")
    print("-" * 76)
    print(f"Total Multi-Asset P&L: Rs. {portfolio_net:>+,.2f} | New Trades Added to DB: {total_added}")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    test_multi_asset()
