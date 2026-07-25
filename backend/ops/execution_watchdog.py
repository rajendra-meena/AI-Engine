"""Execution Watchdog — monitors order health, latency, unknown states.

Phase 50: UNKNOWN ≠ FAILED, UNKNOWN ≠ RETRY, UNKNOWN = RECONCILIATION_REQUIRED.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ExecutionHealth:
    """Current execution health status."""
    state: str = "healthy"
    pending_orders: int = 0
    unknown_orders: int = 0
    rejected_orders: int = 0
    duplicate_attempts: int = 0
    max_ack_latency_ms: float = 0.0
    max_fill_latency_ms: float = 0.0
    last_order_timestamp: str = ""
    reconciliation_required: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "pending_orders": self.pending_orders,
            "unknown_orders": self.unknown_orders,
            "rejected_orders": self.rejected_orders,
            "duplicate_attempts": self.duplicate_attempts,
            "max_ack_latency_ms": round(self.max_ack_latency_ms, 1),
            "max_fill_latency_ms": round(self.max_fill_latency_ms, 1),
            "last_order_timestamp": self.last_order_timestamp,
            "reconciliation_required": self.reconciliation_required,
            "timestamp": self.timestamp,
        }


class ExecutionWatchdog:
    """
    Monitors execution health.

    Rules:
    - UNKNOWN order status = RECONCILIATION REQUIRED (not retry)
    - Never automatically retry an order whose final broker state is unknown
    - Flag duplicate attempts
    """

    def __init__(self):
        self._health = ExecutionHealth()
        self._audit_log = None

    def set_audit_log(self, a): self._audit_log = a

    def record_order_unknown(self, order_id: str) -> None:
        """Record an unknown order status."""
        self._health.unknown_orders += 1
        if order_id not in self._health.reconciliation_required:
            self._health.reconciliation_required.append(order_id)
        self._health.state = "reconciliation_required"

    def record_order_rejected(self) -> None:
        self._health.rejected_orders += 1

    def record_duplicate_attempt(self) -> None:
        self._health.duplicate_attempts += 1

    def record_ack_latency(self, latency_ms: float) -> None:
        self._health.max_ack_latency_ms = max(self._health.max_ack_latency_ms, latency_ms)

    def record_fill_latency(self, latency_ms: float) -> None:
        self._health.max_fill_latency_ms = max(self._health.max_fill_latency_ms, latency_ms)

    def set_pending_orders(self, count: int) -> None:
        self._health.pending_orders = count

    def get_health(self) -> ExecutionHealth:
        return self._health

    def is_reconciliation_required(self) -> bool:
        return len(self._health.reconciliation_required) > 0
