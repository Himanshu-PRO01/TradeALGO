"""Unit tests for the 24/7 Paper Trading Daemon and 90-Day SEBI Audit Logger."""
import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from algobot.paper_trading_daemon import (
    AuditLedger,
    MarketSessionStatus,
    get_market_session_status,
)
from generate_compliance_report import verify_hash_chain

IST = ZoneInfo("Asia/Kolkata")


def test_market_session_status_during_market_hours():
    # Tuesday at 10:30 AM IST (regular market hours)
    tuesday_open = dt.datetime(2026, 10, 6, 10, 30, tzinfo=IST)
    status = get_market_session_status(tuesday_open)

    assert status.is_open is True
    assert status.is_weekend is False
    assert status.seconds_until_open == 0


def test_market_session_status_outside_market_hours():
    # Tuesday at 18:00 IST (market closed, next open is Wednesday 09:15)
    tuesday_night = dt.datetime(2026, 10, 6, 18, 0, tzinfo=IST)
    status = get_market_session_status(tuesday_night)

    assert status.is_open is False
    assert status.is_weekend is False
    # Next open is tomorrow at 09:15 IST (15 hours and 15 minutes away = 54,900 seconds)
    assert status.seconds_until_open == 15 * 3600 + 15 * 60


def test_market_session_status_on_weekend():
    # Saturday at 12:00 PM IST (weekend, next open is Monday 09:15)
    saturday_noon = dt.datetime(2026, 10, 10, 12, 0, tzinfo=IST)
    status = get_market_session_status(saturday_noon)

    assert status.is_open is False
    assert status.is_weekend is True
    assert status.seconds_until_open > 0


def test_audit_ledger_sha256_cryptographic_chain(tmp_path: Path):
    ledger_file = tmp_path / "test_ledger.csv"
    ledger = AuditLedger(ledger_file)

    # Record Day 1
    d1 = ledger.record_day(
        strategy_name="conservative_pullback",
        symbol="Nifty 50",
        date_str="2026-10-06",
        starting_equity=10000.0,
        ending_equity=10450.0,
        daily_gross=500.0,
        daily_charges=50.0,
        daily_net=450.0,
        trade_count=2,
        win_count=2,
        cumulative_net=450.0,
        cumulative_return_pct=4.5,
        max_drawdown=0.0,
    )

    assert d1["day_index"] == 1
    assert "audit_hash" in d1
    assert len(d1["audit_hash"]) == 64  # SHA-256 is 64 hex characters

    # Record Day 2
    d2 = ledger.record_day(
        strategy_name="conservative_pullback",
        symbol="Nifty 50",
        date_str="2026-10-07",
        starting_equity=10000.0,
        ending_equity=10300.0,
        daily_gross=-100.0,
        daily_charges=50.0,
        daily_net=-150.0,
        trade_count=1,
        win_count=0,
        cumulative_net=300.0,
        cumulative_return_pct=3.0,
        max_drawdown=-150.0,
    )

    assert d2["day_index"] == 2
    assert d2["audit_hash"] != d1["audit_hash"]

    # Verify cryptographic chain
    df = pd.read_csv(ledger_file)
    is_valid, issues = verify_hash_chain(df)
    assert is_valid is True
    assert len(issues) == 0

    # Tamper test: Altering any historical number must immediately break the hash chain
    df.loc[0, "daily_net_pnl"] = 999.0
    is_valid_tampered, issues_tampered = verify_hash_chain(df)
    assert is_valid_tampered is False
    assert len(issues_tampered) > 0
