"""Shared setup for the manual QA scripts: a realistic (fake) Nifty-like data file and one strategy."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import yaml  # noqa: E402

from algobot.data import load_csv  # noqa: E402

CSV = os.path.join(HERE, "realistic_nifty_5min.csv")

RULES = """
indicators:
  - {name: orh, type: opening_range_high, period: 15}
  - {name: orl, type: opening_range_low,  period: 15}
  - {name: vw,  type: vwap}
  - {name: e20, type: ema, period: 20}
  - {name: r14, type: rsi, period: 14}
entry_long:  "close > orh and close_prev <= orh_prev and close > vw and e20 > e20_prev and r14 > 55"
exit_long:   "close < vw"
entry_short: "close < orl and close_prev >= orl_prev and close < vw and e20 < e20_prev and r14 < 45"
exit_short:  "close > vw"
"""

RAW = {
    "name": "orb_vwap_test", "capital": 500000,
    "strategy": {"name": "rules", "params": yaml.safe_load(RULES), "quantity": 75, "allow_short": True,
                 "stop_loss_pct": 0.35, "target_pct": 0.7},
    "risk": {"max_daily_loss": 6000, "max_trades_per_day": 3, "max_position_value": 2500000,
             "trading_start": "09:30", "no_new_entries_after": "14:45", "square_off_time": "15:15"},
    "costs": {"brokerage_pct": 0.03, "brokerage_cap": 20, "stt_buy_pct": 0.0, "stt_sell_pct": 0.025,
              "exchange_txn_pct": 0.003, "sebi_fee_pct": 0.0001, "stamp_buy_pct": 0.003, "gst_pct": 18,
              "slippage_bps": 2},
}


def load_prices():
    return load_csv(CSV)
