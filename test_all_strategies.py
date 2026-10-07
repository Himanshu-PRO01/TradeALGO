"""Live Market Strategy Numbers Test.

Runs all strategy configs across their target instruments on live 1-month 5m candles.
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from algobot.config import load_config
from algobot.live_data import fetch_ohlc, LiveDataError
from algobot.paper_trading import evaluate, split_open_and_closed

TEST_MATRIX = [
    ("Stock Pullback (Reliance)", "configs/stock_pullback.yaml", "RELIANCE.NS", 50),
    ("Stock Pullback (HDFC Bank)", "configs/stock_pullback.yaml", "HDFCBANK.NS", 100),
    ("Stock Pullback (ICICI Bank)", "configs/stock_pullback.yaml", "ICICIBANK.NS", 100),
    ("Conservative Pullback (Nifty 50)", "configs/conservative_pullback.yaml", "^NSEI", 25),
    ("Bank Nifty Momentum", "configs/banknifty_momentum.yaml", "^NSEBANK", 15),
    ("Nifty Pivot S1/R1 Bounce", "configs/nifty_pivot_bounce.yaml", "^NSEI", 25),
]


def main():
    print("=" * 84)
    print("  LIVE MARKET STRATEGY NUMBERS TEST (Last 30 Days of 5-Min Candles)")
    print("=" * 84)
    header = f"{'Strategy / Asset':<34} {'Trades':<8} {'Wins':<6} {'WinRate':<9} {'Gross PnL':<13} {'Net PnL'}"
    print(header)
    print("-" * 84)

    total_trades = 0
    total_wins = 0
    total_net = 0.0

    for name, cfg_file, ticker, qty in TEST_MATRIX:
        cfg = load_config(cfg_file)
        cfg["strategy"]["quantity"] = qty
        try:
            df = fetch_ohlc(ticker, "5m", "1mo")
            res = evaluate(cfg, df)
            _, closed = split_open_and_closed(res)
            n = len(closed)
            w = int((closed["net_pnl"] > 0).sum()) if n else 0
            wr = (w / n * 100.0) if n else 0.0
            gross = float(closed["gross_pnl"].sum()) if n else 0.0
            net = float(closed["net_pnl"].sum()) if n else 0.0

            total_trades += n
            total_wins += w
            total_net += net

            print(f"{name:<34} {n:<8} {w:<6} {wr:>5.1f}%    Rs.{gross:>+10,.2f}  Rs.{net:>+10,.2f}")
        except Exception as e:
            print(f"{name:<34} ERROR: {e}")

    print("-" * 84)
    overall_wr = (total_wins / total_trades * 100.0) if total_trades else 0.0
    print(f"{'COMBINED PORTFOLIO':<34} {total_trades:<8} {total_wins:<6} {overall_wr:>5.1f}%    {'':<13} Rs.{total_net:>+10,.2f}")
    print("=" * 84 + "\n")


if __name__ == "__main__":
    main()
