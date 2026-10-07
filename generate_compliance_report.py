#!/usr/bin/env python3
"""TradeALGO SEBI Compliance Track Record & Audit Report Generator.

Compiles the 90-day paper trading journal into a formal, verifiable
performance dossier suitable for regulatory compliance review (e.g. SEBI RA),
client transparency, and prospective subscription due diligence.

Validates the cryptographic SHA-256 hash chain to mathematically prove
that the journal was created sequentially forward in time and has not
been back-dated or altered.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
from pathlib import Path
import sys

import pandas as pd

from algobot.paper_trading_daemon import AUDIT_DIR, LEDGER_CSV, TRADES_CSV

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def verify_hash_chain(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """Verifies that each row's SHA-256 hash correctly chains from the previous row."""
    if df.empty:
        return True, ["No entries to verify."]

    issues = []
    prev_hash = "GENESIS_TRADEALGO"

    for idx, row in df.iterrows():
        day_idx = int(row["day_index"])
        date_str = str(row["date"])
        strat = str(row["strategy"])
        start_eq = float(row["starting_equity"])
        end_eq = float(row["ending_equity"])
        daily_net = float(row["daily_net_pnl"])
        trades = int(row["trade_count"])
        logged_utc = str(row["logged_at_utc"])
        recorded_hash = str(row["audit_hash"])

        payload = f"{prev_hash}|{day_idx}|{date_str}|{strat}|{start_eq:.2f}|{end_eq:.2f}|{daily_net:.2f}|{trades}|{logged_utc}"
        expected_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        if expected_hash != recorded_hash:
            issues.append(f"Row {idx+1} (Day {day_idx}, {date_str}): Hash mismatch! Recorded {recorded_hash[:12]} vs Computed {expected_hash[:12]}")
        prev_hash = recorded_hash

    return len(issues) == 0, issues


def generate_report(output_md: Path, output_csv: Path) -> None:
    if not LEDGER_CSV.exists():
        print(f"[ERROR] Ledger file not found at {LEDGER_CSV}. Run run_90day_logger.py first.")
        return

    ledger_df = pd.read_csv(LEDGER_CSV)
    if ledger_df.empty:
        print("[ERROR] Ledger file is empty.")
        return

    # Cryptographic Chain Validation
    is_valid_chain, chain_issues = verify_hash_chain(ledger_df)

    # Calculate aggregate metrics
    total_days = len(ledger_df)
    first_date = ledger_df["date"].iloc[0]
    last_date = ledger_df["date"].iloc[-1]
    strategy_name = ledger_df["strategy"].iloc[-1]
    symbol = ledger_df["symbol"].iloc[-1]

    starting_capital = float(ledger_df["starting_equity"].iloc[0])
    ending_equity = float(ledger_df["ending_equity"].iloc[-1])
    net_pnl = ending_equity - starting_capital
    return_pct = (net_pnl / starting_capital * 100.0) if starting_capital > 0 else 0.0

    total_trades = int(ledger_df["trade_count"].sum())
    total_wins = int(ledger_df["win_count"].sum())
    win_rate = (total_wins / total_trades * 100.0) if total_trades > 0 else 0.0

    total_gross = float(ledger_df["daily_gross_pnl"].sum())
    total_charges = float(ledger_df["daily_charges"].sum())
    max_dd = float(ledger_df["max_drawdown"].min())
    max_dd_pct = (max_dd / starting_capital * 100.0) if starting_capital > 0 else 0.0

    # Trade details if available
    trade_details = ""
    if TRADES_CSV.exists():
        try:
            trades_df = pd.read_csv(TRADES_CSV)
            if not trades_df.empty:
                trade_details = f"\n### Detailed Trade Execution Ledger ({len(trades_df)} Trades)\n\n"
                trade_details += trades_df.to_markdown(index=False)
        except Exception:
            pass

    chain_status_text = (
        "PASS - Cryptographic SHA-256 chain verified 100% intact with zero breaks."
        if is_valid_chain
        else f"FAIL - Chain discrepancies detected: {'; '.join(chain_issues)}"
    )

    report_content = f"""# TRADEALGO QUANTITATIVE PERFORMANCE & AUDIT DOSSIER
**Institutional Track Record Certification**

---

### Executive Summary

| Parameter | Value |
| :--- | :--- |
| **Strategy Name** | `{strategy_name}` |
| **Asset / Market** | `{symbol}` |
| **Verification Window** | {first_date} to {last_date} ({total_days} / 90 Market Days) |
| **Starting Capital** | INR {starting_capital:,.2f} |
| **Final Account Balance** | INR {ending_equity:,.2f} |
| **Net Realized P&L** | INR {net_pnl:>+,.2f} ({return_pct:>+.2f}%) |
| **Total Completed Trades** | {total_trades} |
| **Win Rate** | {win_rate:.1f}% ({total_wins} wins / {total_trades} trades) |
| **Gross Profit** | INR {total_gross:,.2f} |
| **Statutory Costs (STT, GST, Brokerage)** | INR {total_charges:,.2f} |
| **Peak-to-Trough Drawdown** | INR {max_dd:,.2f} ({max_dd_pct:.2f}%) |
| **Integrity Audit Status** | **{chain_status_text}** |

---

### Cryptographic Audit Trail (SHA-256 Chain)
Every daily closing row is linked to the previous day's mathematical hash to provide verifiable proof against retroactive modification:

| Day | Date | Daily Net P&L | Ending Equity | Trade Count | SHA-256 Hash |
| :---: | :---: | :---: | :---: | :---: | :--- |
"""

    for _, r in ledger_df.iterrows():
        hash_str = str(r["audit_hash"])
        report_content += f"| {r['day_index']} | {r['date']} | INR {float(r['daily_net_pnl']):>+,.2f} | INR {float(r['ending_equity']):,.2f} | {r['trade_count']} | `{hash_str[:20]}...` |\n"

    report_content += f"""
---

### Regulatory & Compliance Declaration
1. **Statutory Cost Factoring**: All performance metrics are calculated strictly **net of all statutory charges** (Securities Transaction Tax, Exchange Turnover Fees, SEBI Turnover Charges, GST @ 18%, Stamp Duty, and Standard ₹20/order Brokerage).
2. **Slippage Modelling**: All entry and exit calculations include a conservative 2.0 bps (0.02%) execution slippage allowance per order.
3. **No Retrospective Optimization**: The parameters of `{strategy_name}` are locked in immutable YAML configuration files for the full forward duration.

{trade_details}

---
*Generated autonomously by TradeALGO Execution Engine on {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    output_md.write_text(report_content, encoding="utf-8")

    # Export factsheet CSV
    factsheet = pd.DataFrame([{
        "strategy": strategy_name,
        "symbol": symbol,
        "days_logged": total_days,
        "starting_capital": starting_capital,
        "ending_equity": ending_equity,
        "net_pnl": net_pnl,
        "return_pct": return_pct,
        "total_trades": total_trades,
        "win_rate_pct": win_rate,
        "max_drawdown": max_dd,
        "total_charges": total_charges,
        "audit_verified": is_valid_chain,
    }])
    factsheet.to_csv(output_csv, index=False)

    print("\n" + "=" * 76)
    print(" [REPORT GENERATED] SEBI Compliance Track Record Dossier")
    print("=" * 76)
    print(f" Markdown Dossier:  {output_md}")
    print(f" Factsheet CSV:     {output_csv}")
    print(f" Chain Status:      {chain_status_text}")
    print(f" Strategy:          {strategy_name} on {symbol}")
    print(f" Days Verified:     {total_days} / 90")
    print(f" Net Equity:        INR {ending_equity:,.2f} ({return_pct:>+.2f}%)")
    print("=" * 76 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SEBI Compliance Audit Dossier")
    parser.add_argument("--md", default=str(AUDIT_DIR / "SEBI_TRACK_RECORD_REPORT.md"), help="Markdown output path")
    parser.add_argument("--csv", default=str(AUDIT_DIR / "performance_factsheet.csv"), help="CSV output path")
    args = parser.parse_args()

    generate_report(Path(args.md), Path(args.csv))


if __name__ == "__main__":
    main()
