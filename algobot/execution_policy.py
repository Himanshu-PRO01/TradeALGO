"""Execution safety policy.

Live trading is deliberately prohibited in this build. Research, backtests,
paper trading, and Upstox Sandbox may run, but no code path may authorize
real-money execution. This flag must not be changed by the learning system.

Two independent gates must both be clear before live_trading_allowed() can
ever return True: this file's own ExecutionMode (a deliberate, code-level
decision), and the persistent kill switch (a human-operable emergency stop
that survives restarts). Flipping the flag alone is never enough -- a tripped
kill switch still blocks execution.
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


def get_execution_mode() -> ExecutionMode:
    """Read the current execution mode from the environment.
    
    If the mode is missing, invalid, or ambiguous, fails closed to LIVE_DISABLED.
    """
    mode_str = os.environ.get("TRADEALGO_EXECUTION_MODE", "LIVE_DISABLED").upper()
    try:
        return ExecutionMode(mode_str)
    except ValueError:
        return ExecutionMode.LIVE_DISABLED


def live_trading_allowed(switch: Optional[KillSwitch] = None) -> bool:
    mode = get_execution_mode()
    
    # Fail-closed behavior: Only allow live if mode is explicitly a LIVE mode 
    # (which doesn't exist yet, as LIVE is hard disabled).
    if mode in (ExecutionMode.RESEARCH, ExecutionMode.PAPER, ExecutionMode.SANDBOX, ExecutionMode.LIVE_DISABLED):
        return False
        
    if switch is not None and switch.status()["halted"]:
        return False
        
    return False


def require_live_disabled() -> None:
    if live_trading_allowed():
        raise RuntimeError("Safety policy violation: live trading must remain disabled.")
