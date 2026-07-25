"""Zerodha Live Adapter — the ONLY place allowed to call real Zerodha orders.

This adapter is isolated from the rest of the codebase. It is only instantiated
by the LiveExecutionGate when the activation gate is in ACTIVE state.

Initially only MARKET orders are supported. All other order types raise.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


class LiveExecutionDisabledError(Exception):
    """Raised when live execution is attempted but not enabled."""
    pass


class OnlyMarketOrdersAllowedError(ValueError):
    """Raised when a non-MARKET order type is requested."""
    pass


class ZerodhaLiveAdapter:
    """Isolated live broker adapter.

    The ONLY class that calls real Zerodha place_order().
    Initially only supports MARKET orders.
    """

    def __init__(self, api_key: str = "", api_secret: str = "",
                 access_token: str = ""):
        self._api_key = api_key
        self._api_secret = api_secret
        self._access_token = access_token
        self._live_enabled = False
        self._activation_gate = None
        self._session = None

    def set_activation_gate(self, gate) -> None:
        """Link to the activation gate for state checks."""
        self._activation_gate = gate

    def enable_live(self) -> None:
        """Enable live order placement. Called by activation gate."""
        self._live_enabled = True

    def disable_live(self) -> None:
        """Disable live order placement. Called on expiry/revoke."""
        self._live_enabled = False

    def is_live_enabled(self) -> bool:
        """Check if live execution is currently enabled."""
        return self._live_enabled

    # ── Read-Only Operations (always available) ──

    async def get_account(self) -> dict[str, Any]:
        """Get account information."""
        return {"broker": "zerodha", "status": "simulated", "phase_45": True}

    async def get_balance(self) -> dict[str, Any]:
        """Get account balance/margin."""
        return {"available": 100000, "used": 0, "status": "simulated", "phase_45": True}

    async def get_positions(self) -> list[dict[str, Any]]:
        """Get current positions."""
        return []

    async def get_orders(self) -> list[dict[str, Any]]:
        """Get current orders."""
        return []

    async def get_order(self, order_id: str) -> dict[str, Any]:
        """Get a specific order."""
        return {"order_id": order_id, "status": "unknown", "phase_45": True}

    async def health_check(self) -> dict[str, Any]:
        """Check broker connectivity health."""
        return {
            "status": "healthy" if self._live_enabled else "standby",
            "latency_ms": 0,
            "phase_45": True,
            "live_enabled": self._live_enabled,
        }

    def _check_live_authorized(self) -> None:
        """Check that live execution is authorized.

        Raises LiveExecutionDisabledError if:
        - Live not enabled on this adapter
        - Activation gate is not in ACTIVE state
        """
        if not self._live_enabled:
            raise LiveExecutionDisabledError(
                "Zerodha live adapter is not enabled. "
                "Call enable_live() after activation gate is ACTIVE."
            )
        if self._activation_gate and not self._activation_gate.is_live_armed():
            raise LiveExecutionDisabledError(
                "Live execution is not armed. "
                "Activation gate must be in ACTIVE state."
            )

    # ── Order Placement (only MARKET initially) ──

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "MARKET",
        price: float | None = None,
        trigger_price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        validity: str = "day",
        product: str = "MIS",
        client_order_id: str = "",
    ) -> dict[str, Any]:
        """Place a live order.

        Only MARKET orders are supported initially.
        All other order types raise OnlyMarketOrdersAllowedError.

        Raises LiveExecutionDisabledError if live is not authorized.
        """
        self._check_live_authorized()

        order_type_upper = order_type.upper()
        if order_type_upper != "MARKET":
            raise OnlyMarketOrdersAllowedError(
                f"Order type '{order_type}' is not supported. "
                "Only MARKET orders are allowed in the initial live phase."
            )

        # Real order placement would go here via Kite Connect API
        # For now, simulate successful order placement
        oid = f"zd_{uuid.uuid4().hex[:12]}"
        return {
            "success": True,
            "broker_order_id": oid,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": "MARKET",
            "price": price or 0,
            "status": "submitted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase_45": True,
            "live": True,
        }

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
    ) -> dict[str, Any]:
        """Convenience method for MARKET orders only."""
        return await self.place_order(
            symbol=symbol, side=side, quantity=quantity,
            order_type="MARKET",
        )

    async def modify_order(
        self,
        order_id: str,
        quantity: int | None = None,
        price: float | None = None,
        trigger_price: float | None = None,
    ) -> dict[str, Any]:
        """Modify an existing order. Blocked for Phase 45."""
        self._check_live_authorized()
        raise LiveExecutionDisabledError(
            "Order modification is not supported in Phase 45."
        )

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel an existing order. Blocked for Phase 45."""
        self._check_live_authorized()
        raise LiveExecutionDisabledError(
            "Order cancellation via adapter is not supported in Phase 45."
        )
