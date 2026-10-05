"""Single live-execution boundary for TradeALGO.

TradeALGO owns signals and risk; OpenAlgo owns broker authentication/routing.
This service adds the missing final guard so every programmatic live order
passes the same explicit gates before it reaches OpenAlgo.
"""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass

from .execution_policy import live_trading_allowed
from .kill_switch import KillSwitch
from .openalgo_bridge import OpenAlgoClient, OpenAlgoError
from .risk import RiskManager


@dataclass(frozen=True)
class ExecutionRequest:
    strategy: str
    symbol: str
    exchange: str
    action: str
    quantity: int
    pricetype: str = "MARKET"
    product: str = "MIS"
    price: float = 0.0
    trigger_price: float = 0.0
    disclosed_quantity: int = 0
    notional: float = 0.0


class LiveExecutionService:
    """The only programmatic path TradeALGO should use for live orders."""

    def __init__(
        self,
        client: OpenAlgoClient,
        kill_switch: KillSwitch,
        risk: RiskManager,
        *,
        confirm_live: bool = False,
    ):
        self.client = client
        self.kill_switch = kill_switch
        self.risk = risk
        self.confirm_live = confirm_live

    @staticmethod
    def _explicit_live_confirmation() -> bool:
        return os.environ.get("TRADEALGO_LIVE_CONFIRM", "").strip().upper() == "I_UNDERSTAND_LIVE_TRADING"

    def place(self, request: ExecutionRequest, *, now: dt.datetime | None = None) -> dict:
        """Place exactly one live order request; never retries it."""
        if not self.confirm_live or not self._explicit_live_confirmation():
            raise OpenAlgoError(
                "Live execution requires an explicit confirmation token and confirm_live=True."
            )
        if not live_trading_allowed(self.kill_switch):
            raise OpenAlgoError("Live execution is blocked by TradeALGO's execution safety policy.")
        if not self.client.execution_enabled():
            raise OpenAlgoError("OpenAlgo execution is disabled by TRADEALGO_EXECUTION_ENABLED.")

        when = (now or dt.datetime.now()).time()
        allowed, reason = self.risk.can_enter(when, float(request.notional))
        if request.action.upper() == "BUY" and not allowed:
            raise OpenAlgoError(f"Trade blocked by risk manager: {reason}")

        if request.quantity < 1:
            raise OpenAlgoError("quantity must be at least 1.")

        result = self.client.place_order(
            strategy=request.strategy,
            symbol=request.symbol,
            action=request.action,
            exchange=request.exchange,
            pricetype=request.pricetype,
            product=request.product,
            quantity=request.quantity,
            price=request.price,
            trigger_price=request.trigger_price,
            disclosed_quantity=request.disclosed_quantity,
        )
        if request.action.upper() == "BUY":
            self.risk.register_entry()
        return result
