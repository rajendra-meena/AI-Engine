"""Abstract broker adapter — broker-agnostic interface. Never sends real orders in Phase 43."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LiveExecutionDisabledError(Exception):
    """Raised when live execution is attempted but disabled in Phase 43."""
    pass


class BrokerAdapter(ABC):
    """Abstract broker interface. Must never send real orders in Phase 43."""

    @abstractmethod
    async def get_account(self) -> dict[str, Any]: ...

    @abstractmethod
    async def get_balance(self) -> dict[str, Any]: ...

    @abstractmethod
    async def get_positions(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_orders(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_order(self, order_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: float | None = None,
        trigger_price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        validity: str = "day",
        product: str = "MIS",
        client_order_id: str = "",
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def modify_order(
        self,
        order_id: str,
        quantity: int | None = None,
        price: float | None = None,
        trigger_price: float | None = None,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]: ...


class ZerodhaAdapter(BrokerAdapter):
    """Zerodha adapter preparation. Phase 43: never sends real orders."""

    async def get_account(self) -> dict[str, Any]:
        return {"broker": "zerodha", "status": "simulated", "phase_43": True}

    async def get_balance(self) -> dict[str, Any]:
        return {"available": 100000, "used": 0, "status": "simulated", "phase_43": True}

    async def get_positions(self) -> list[dict[str, Any]]:
        return []

    async def get_orders(self) -> list[dict[str, Any]]:
        return []

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return {"order_id": order_id, "status": "unknown", "phase_43": True}

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: float | None = None,
        trigger_price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        validity: str = "day",
        product: str = "MIS",
        client_order_id: str = "",
    ) -> dict[str, Any]:
        """Phase 43: never sends real orders. Always raises."""
        raise LiveExecutionDisabledError(
            "Zerodha real order placement is disabled in Phase 43. "
            "Use ExecutionSimulator for infrastructure testing."
        )

    async def modify_order(
        self,
        order_id: str,
        quantity: int | None = None,
        price: float | None = None,
        trigger_price: float | None = None,
    ) -> dict[str, Any]:
        raise LiveExecutionDisabledError(
            "Zerodha order modification is disabled in Phase 43."
        )

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        raise LiveExecutionDisabledError(
            "Zerodha order cancellation via broker is disabled in Phase 43. "
            "Use internal state management."
        )

    async def health_check(self) -> dict[str, Any]:
        return {"status": "healthy", "latency_ms": 0, "phase_43": True}
