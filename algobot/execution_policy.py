"""Execution safety policy.

Live trading is deliberately prohibited in this build. Research, backtests,
paper trading, and Upstox Sandbox may run, but no code path may authorize
real-money execution. This flag must not be changed by the learning system.

Two independent gates must both be clear before live_trading_allowed() can
ever return True: this file's own LIVE_TRADING_ENABLED flag (a deliberate,
code-level decision), and the persistent kill switch (a human-operable
emergency stop that survives restarts). Flipping the flag alone is never
enough -- a tripped kill switch still blocks execution.
"""
from .kill_switch import KillSwitch

LIVE_TRADING_ENABLED = False


def live_trading_allowed(switch: "KillSwitch | None" = None) -> bool:
    if not LIVE_TRADING_ENABLED:
        return False
    if switch is not None and switch.status()["halted"]:
        return False
    return True


def require_live_disabled() -> None:
    if LIVE_TRADING_ENABLED:
        raise RuntimeError("Safety policy violation: live trading must remain disabled.")
