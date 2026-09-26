"""Explicit execution policy for research, paper, sandbox and live modes.

Live execution is available only when the operator deliberately sets
TRADEALGO_EXECUTION_MODE=LIVE. The persistent kill switch remains a second,
independent gate. The learning layer cannot change this policy.
"""
import os
from enum import Enum
from typing import Optional

from .kill_switch import KillSwitch


class ExecutionMode(Enum):
    RESEARCH = "RESEARCH"
    PAPER = "PAPER"
    SANDBOX = "SANDBOX"
    LIVE_DISABLED = "LIVE_DISABLED"
    LIVE = "LIVE"


def get_execution_mode() -> ExecutionMode:
    """Read the execution mode; missing/invalid values fail closed."""
    mode_str = os.environ.get("TRADEALGO_EXECUTION_MODE", "LIVE_DISABLED").upper()
    try:
        return ExecutionMode(mode_str)
    except ValueError:
        return ExecutionMode.LIVE_DISABLED


def _default_kill_switch() -> KillSwitch:
    path = os.environ.get("TRADEALGO_KILL_SWITCH_DB", os.path.join("data", "kill_switch.sqlite"))
    return KillSwitch(path=path)


def live_trading_allowed(switch: Optional[KillSwitch] = None) -> bool:
    """Return True only for explicit LIVE mode with no active kill switch."""
    if get_execution_mode() is not ExecutionMode.LIVE:
        return False
    if switch is not None:
        return not switch.status()["halted"]
    owned = _default_kill_switch()
    try:
        return not owned.status()["halted"]
    finally:
        owned.close_db()


def require_live_enabled(switch: Optional[KillSwitch] = None) -> None:
    if not live_trading_allowed(switch):
        raise RuntimeError(
            "Live execution is blocked. Set TRADEALGO_EXECUTION_MODE=LIVE "
            "and make sure the persistent kill switch is not halted."
        )


def require_live_disabled() -> None:
    """Backward-compatible guard used by older callers; now means 'not live'."""
    if live_trading_allowed():
        raise RuntimeError("Live execution is enabled; this caller requires non-live mode.")
