"""Compare 3 strategy variants on live Nifty 50 data.

Variant A: RSI5 < 35 (relaxed threshold, same fast RSI)
Variant B: RSI14 < 40 (standard RSI, well-suited for indices)
Variant C: EMA20 > EMA50 crossover (trend-following, fires more often)
"""
import sys
import copy

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from algobot.config import load_config
from algobot.live_data import fetch_ohlc, LiveDataError
from algobot.paper_trading import evaluate, split_open_and_closed
from algobot.audit import run_audit, format_audit

BASE_CONFIG = "configs/conservative_pullback.yaml"
TICKER = "^NSEI"
SYMBOL = "Nifty 50"
SEP = "=" * 70

VARIANTS = {
    "A: RSI5 < 35 (relaxed pullback)": {
        "indicators": [
            {"name": "rsi5", "type": "rsi", "period": 5},
            {"name": "e20",  "type": "ema", "period": 20},
            {"name": "e50",  "type": "ema", "period": 50},
        ],
        "entry_long":  "rsi5 < 35 and close > open and close > e50",
        "exit_long":   "rsi5 > 60",
        "entry_short": "rsi5 > 65 and close < open and close < e50",
        "exit_short":  "rsi5 < 40",
    },
    "B: RSI14 < 40 (standard RSI)": {
        "indicators": [
            {"name": "rsi14", "type": "rsi", "period": 14},
            {"name": "e20",   "type": "ema", "period": 20},
            {"name": "e50",   "type": "ema", "period": 50},
        ],
        "entry_long":  "rsi14 < 40 and close > e20",
        "exit_long":   "rsi14 > 65",
        "entry_short": "rsi14 > 60 and close < e20",
        "exit_short":  "rsi14 < 35",
    },
    "C: EMA20/EMA50 crossover (trend)": {
        "indicators": [
            {"name": "e20", "type": "ema", "period": 20},
            {"name": "e50", "type": "ema", "period": 50},
            {"name": "rsi14", "type": "rsi", "period": 14},
        ],
        "entry_long":  "e20 > e50 and rsi14 < 60",
        "exit_long":   "e20 < e50",
        "entry_short": "e20 < e50 and rsi14 > 40",
        "exit_short":  "e20 > e50",
    },
}


def score_variant(name, cfg, df):
    result = evaluate(cfg, df)
    _, closed = split_open_and_closed(result)
    if closed.empty:
        print(f"\n  {name}")
        print(f"  >>> NO TRADES FIRED in this window. Entry rules too tight.")
        return {"trades": 0, "net": 0, "win_rate": 0}

    total = len(closed)
    wins = int((closed["net_pnl"] > 0).sum())
    net = float(closed["net_pnl"].sum())
    win_rate = wins / total * 100 if total else 0
    best = float(closed["net_pnl"].max())
    worst = float(closed["net_pnl"].min())

    print(f"\n  [{name}]")
    print(f"  Trades: {total}  |  Wins: {wins}  |  Win Rate: {win_rate:.1f}%")
    print(f"  Net P&L: Rs. {net:>+,.2f}  |  Best: Rs. {best:>+,.2f}  |  Worst: Rs. {worst:>+,.2f}")
    verdict = "GOOD" if net > 0 and win_rate >= 45 else "WEAK" if net > 0 else "LOSING"
    print(f"  Quick Verdict: [{verdict}]")
    return {"name": name, "trades": total, "net": net, "win_rate": win_rate}


def main():
    base_cfg = load_config(BASE_CONFIG)

    print("\nFetching Nifty 50 data (1 month of 5-min candles)...")
    try:
        df = fetch_ohlc(TICKER, "5m", "1mo")
        print(f"Loaded {len(df)} candles. Latest close: Rs. {df['close'].iloc[-1]:,.2f}")
    except LiveDataError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print(f"\n{SEP}")
    print("  STRATEGY VARIANT COMPARISON")
    print(f"{SEP}")

    results = []
    for vname, params in VARIANTS.items():
        cfg = copy.deepcopy(base_cfg)
        cfg["strategy"]["params"] = params
        r = score_variant(vname, cfg, df)
        r["name"] = vname
        results.append(r)

    # Rank by net P&L
    ranked = sorted(results, key=lambda x: x["net"], reverse=True)

    print(f"\n{SEP}")
    print("  RANKING (best to worst by net P&L)")
    print(f"{SEP}")
    for i, r in enumerate(ranked, 1):
        print(f"  #{i}  {r['name']}")
        print(f"       Net: Rs. {r['net']:>+,.2f}  |  Win Rate: {r['win_rate']:.1f}%  |  Trades: {r['trades']}")

    best = ranked[0]
    print(f"\n  >>> WINNER: {best['name']}")
    if best["trades"] == 0:
        print("  WARNING: No variant fired any trades in the last 30 days.")
        print("  This likely means NSE was calm/trending and none of the pullback/RSI extremes triggered.")
        print("  Try running on a more volatile period or consider a trend-following entry instead.")
    else:
        print(f"  Net P&L: Rs. {best['net']:>+,.2f}  |  Win Rate: {best['win_rate']:.1f}%  |  Trades: {best['trades']}")
        print(f"\nNow running full SEBI Audit on the winner...")
        winner_cfg = copy.deepcopy(base_cfg)
        winner_cfg["strategy"]["params"] = VARIANTS[best["name"]]
        report = run_audit(df, winner_cfg)
        print(format_audit(report))

    print(f"\n{SEP}")
    print("  To apply the winning variant, update configs/conservative_pullback.yaml")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
