"""Order State Machine with valid transitions and audit."""

from __future__ import annotations

from enum import Enum
from typing import Any


class OrderStatus(str, Enum):
    CREATED = "created"
    VALIDATING = "validating"
    RISK_APPROVED = "risk_approved"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"
    UNKNOWN = "unknown"
    RECONCILING = "reconciling"
    CLOSED = "closed"


VALID_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.CREATED: [OrderStatus.VALIDATING, OrderStatus.REJECTED, OrderStatus.FAILED],
    OrderStatus.VALIDATING: [OrderStatus.RISK_APPROVED, OrderStatus.REJECTED, OrderStatus.FAILED],
    OrderStatus.RISK_APPROVED: [OrderStatus.SUBMITTED, OrderStatus.REJECTED, OrderStatus.FAILED],
    OrderStatus.SUBMITTED: [OrderStatus.ACKNOWLEDGED, OrderStatus.REJECTED, OrderStatus.FAILED, OrderStatus.UNKNOWN],
    OrderStatus.ACKNOWLEDGED: [
        OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED,
        OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.RECONCILING,
    ],
    OrderStatus.PARTIALLY_FILLED: [OrderStatus.FILLED, OrderStatus.CANCEL_REQUESTED, OrderStatus.RECONCILING],
    OrderStatus.FILLED: [OrderStatus.CLOSED, OrderStatus.RECONCILING],
    OrderStatus.CANCEL_REQUESTED: [OrderStatus.CANCELLED, OrderStatus.FILLED, OrderStatus.RECONCILING],
    OrderStatus.CANCELLED: [OrderStatus.RECONCILING],
    OrderStatus.REJECTED: [OrderStatus.RECONCILING],
    OrderStatus.FAILED: [OrderStatus.RECONCILING],
    OrderStatus.UNKNOWN: [OrderStatus.RECONCILING],
    OrderStatus.RECONCILING: [OrderStatus.CREATED, OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.CLOSED],
    OrderStatus.CLOSED: [],
}


class OrderStateMachineError(Exception):
    """Raised on invalid state transition."""
    pass


class OrderStateMachine:
    """Tracks and validates order state transitions."""

    def __init__(self, order_id: str, initial_state: OrderStatus = OrderStatus.CREATED):
        self.order_id = order_id
        self._state = initial_state
        self._transitions: list[dict[str, Any]] = []

    @property
    def state(self) -> OrderStatus:
        return self._state

    def transition_to(
        self,
        new_state: OrderStatus,
        reason: str = "",
        source: str = "",
        correlation_id: str = "",
    ) -> bool:
        """Attempt state transition. Returns True if successful."""
        allowed = VALID_TRANSITIONS.get(self._state, [])
        if new_state not in allowed:
            raise OrderStateMachineError(
                f"Invalid transition: {self._state.value} -> {new_state.value} for order {self.order_id}"
            )
        previous = self._state
        self._state = new_state
        self._transitions.append({
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "order_id": self.order_id,
            "previous_state": previous.value,
            "new_state": new_state.value,
            "reason": reason,
            "source": source,
            "correlation_id": correlation_id,
        })
        return True

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._transitions)

    def get_state(self) -> str:
        return self._state.value
