"""Execution safety policy.

Live trading is deliberately prohibited in this build. Research, backtests,
paper trading, and Upstox Sandbox may run, but no code path may authorize
real-money execution. This flag must not be changed by the learning system.
"""


LIVE_TRADING_ENABLED = False


def live_trading_allowed() -> bool:
    return False


def require_live_disabled() -> None:
    if LIVE_TRADING_ENABLED:
        raise RuntimeError("Safety policy violation: live trading must remain disabled.")
