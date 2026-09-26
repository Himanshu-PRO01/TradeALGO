"""Tests for PaperLog's virtual-capital views, and a standing safety check that
Paper Trading (Forward Testing with virtual capital) cannot place a real or
sandbox order -- it should not even import anything that can."""
import ast
import inspect

import algobot.paper_trading as paper_trading
from algobot.paper_trading import PaperLog


def _log_with_trades():
    log = PaperLog(":memory:")
    log.add_trades("k", "NIFTY", [
        {"entry_time": "2025-01-06 09:15", "exit_time": "2025-01-06 09:45",
         "side": "LONG", "qty": 10, "entry_price": 100.0, "exit_price": 102.0,
         "gross_pnl": 20.0, "costs": 2.0, "net_pnl": 18.0, "exit_reason": "signal",
         "logged_at": "2025-01-06T10:00:00"},
        {"entry_time": "2025-01-06 10:00", "exit_time": "2025-01-06 10:30",
         "side": "LONG", "qty": 10, "entry_price": 102.0, "exit_price": 99.0,
         "gross_pnl": -30.0, "costs": 2.0, "net_pnl": -32.0, "exit_reason": "stop",
         "logged_at": "2025-01-06T10:30:00"},
    ])
    return log


def test_virtual_ledger_reflects_only_realized_pnl_when_flat():
    log = _log_with_trades()
    ledger = log.virtual_ledger("k", starting_capital=100000.0)
    assert ledger["starting_capital"] == 100000.0
    assert ledger["realized_pnl"] == -14.0
    assert ledger["unrealized_pnl"] == 0.0
    assert ledger["virtual_balance"] == 99986.0
    assert ledger["available_capital"] == 99986.0
    assert ledger["virtual_equity"] == 99986.0


def test_virtual_ledger_adds_unrealized_pnl_of_an_open_snapshot():
    log = _log_with_trades()
    open_snapshot = {"net_pnl": 7.5}
    ledger = log.virtual_ledger("k", starting_capital=100000.0, open_snapshot=open_snapshot)
    assert ledger["realized_pnl"] == -14.0
    assert ledger["unrealized_pnl"] == 7.5
    assert ledger["virtual_balance"] == 99986.0
    assert ledger["virtual_equity"] == 99993.5


def test_virtual_ledger_with_no_trades_yet_is_just_starting_capital():
    log = PaperLog(":memory:")
    ledger = log.virtual_ledger("empty_key", starting_capital=50000.0)
    assert ledger == {
        "starting_capital": 50000.0, "realized_pnl": 0.0, "unrealized_pnl": 0.0,
        "virtual_balance": 50000.0, "available_capital": 50000.0, "virtual_equity": 50000.0,
    }


def test_equity_curve_is_cumulative_and_tracks_its_own_drawdown():
    log = _log_with_trades()
    curve = log.equity_curve("k", starting_capital=100000.0)
    assert list(curve["equity"]) == [100018.0, 99986.0]
    assert curve["drawdown"].iloc[0] == 0.0
    assert curve["drawdown"].iloc[1] == 99986.0 - 100018.0


def test_equity_curve_empty_when_nothing_logged():
    log = PaperLog(":memory:")
    curve = log.equity_curve("nope", starting_capital=100000.0)
    assert curve.empty
    assert list(curve.columns) == ["exit_time", "equity", "drawdown"]


def test_daily_pnl_groups_by_calendar_date_of_exit():
    log = _log_with_trades()
    daily = log.daily_pnl("k")
    assert len(daily) == 1
    assert daily.iloc[0]["net_pnl"] == -14.0


def test_reset_clears_the_ledger_back_to_starting_capital():
    log = _log_with_trades()
    log.reset("k")
    ledger = log.virtual_ledger("k", starting_capital=100000.0)
    assert ledger["realized_pnl"] == 0.0
    assert ledger["virtual_balance"] == 100000.0
    assert log.equity_curve("k", 100000.0).empty


def test_paper_trading_module_cannot_send_a_live_or_sandbox_order():
    """Static guarantee: Forward Testing must not import live/sandbox execution
    code or call a broker place_order function."""
    tree = ast.parse(inspect.getsource(paper_trading))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[-1])
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)

    forbidden_imports = {"UpstoxSandboxClient", "upstox_sandbox", "execution_policy"}
    bad_imports = forbidden_imports & imported
    assert not bad_imports, f"paper_trading.py imports live/sandbox execution code: {bad_imports}"

    call_names = {
        n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", None)
        for n in ast.walk(tree) if isinstance(n, ast.Call)
    }
    assert "place_order" not in call_names, "paper_trading.py must never call place_order"
