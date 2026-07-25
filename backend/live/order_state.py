"""Phase 46 — Order State Machine for live execution orders.

Extends the existing OrderStatus from execution/order_state.py with
Phase 46 specific states and transitions for the preflight path.
"""

from __future__ import annotations

from typing import Any

from execution.order_state import OrderStatus, OrderStateMachine, OrderStateMachineError


class LiveOrderStatus(str):
    """Phase 46 order status constants — extends existing OrderStatus with PREFLIGHT_PASSED."""
    PREFLIGHT_PASSED = "preflight_passed"


class LiveOrderStateMachine:
    """
    Order state machine for live execution.

    Wraps the existing OrderStateMachine and adds preflight validation state.
    """

    def __init__(self, order_id: str):
        self._order_id = order_id
        self._sm = OrderStateMachine(order_id, OrderStatus.CREATED)
        self._preflight_passed = False
        self._transitions: list[dict[str, Any]] = []

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def state(self) -> str:
        return self._sm.get_state()

    def mark_preflight_passed(self) -> None:
        """Mark preflight validation as passed."""
        self._preflight_passed = True
        self._transitions.append({
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "order_id": self._order_id,
            "previous_state": "validating",
            "new_state": "preflight_passed",
            "reason": "All preflight checks passed",
            "source": "preflight_validator",
        })

    def is_preflight_passed(self) -> bool:
        return self._preflight_passed

    def transition_to(
        self,
        new_state: OrderStatus,
        reason: str = "",
        source: str = "",
        correlation_id: str = "",
    ) -> bool:
        """Transition to a new state via the underlying state machine."""
        return self._sm.transition_to(
            new_state, reason=reason, source=source,
            correlation_id=correlation_id,
        )

    def get_history(self) -> list[dict[str, Any]]:
        all_transitions = list(self._sm.get_history())
        all_transitions.extend(self._transitions)
        return all_transitions

    def get_state(self) -> str:
        return self._sm.get_state()
