"""Live Order Reconciliation — compares internal vs broker order state after submission.

Phase 46: After every live order, reconcile internal state with broker state.
On mismatch: transition to RECONCILIATION_REQUIRED, block new orders.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class OrderReconResult:
    """Result of a single order reconciliation."""
    matched: bool = False
    internal_order: dict[str, Any] = field(default_factory=dict)
    broker_order: dict[str, Any] | None = None
    mismatches: list[str] = field(default_factory=list)
    blocking: bool = False
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "mismatches": self.mismatches,
            "blocking": self.blocking,
            "timestamp": self.timestamp,
        }


COMPARE_FIELDS = [
    ("symbol", "symbol"),
    ("side", "side", "transaction_type"),
    ("quantity", "quantity"),
    ("status", "status"),
    ("filled_quantity", "filled_quantity"),
    ("average_price", "average_price", "avg_price"),
    ("order_type", "order_type"),
]


class LiveOrderReconciliation:
    """
    Compares internal vs broker order state after submission.

    Rules:
    - If broker state differs from internal: RECONCILIATION_REQUIRED
    - Do NOT blindly assume the order failed
    - Do NOT auto-retry or auto-cancel
    - Block new orders on critical mismatch
    """

    def __init__(self):
        self._reconciliation_blocked = False
        self._results: list[OrderReconResult] = []
        self._audit_log = None

    def set_audit_log(self, audit): self._audit_log = audit

    def reconcile(
        self,
        internal_order: dict[str, Any],
        broker_order: dict[str, Any] | None,
    ) -> OrderReconResult:
        """Compare internal vs broker order state.

        Args:
            internal_order: Internal order state dict
            broker_order: Broker order state dict (None = not found at broker)

        Returns:
            OrderReconResult with mismatch details
        """
        result = OrderReconResult(
            internal_order=internal_order,
            broker_order=broker_order,
        )
        mismatches: list[str] = []

        # Broker order not found
        if broker_order is None:
            mismatches.append("order_not_found_at_broker")
            result.blocking = True
            result.matched = False
            result.mismatches = mismatches
            self._results.append(result)
            self._reconciliation_blocked = True

            self._record_audit("order_reconciliation_failed",
                               details={"mismatches": mismatches, "blocking": True},
                               severity="critical")
            return result

        # Compare each field
        internal_order_id = internal_order.get("internal_order_id", "")
        broker_order_id = broker_order.get("broker_order_id", broker_order.get("order_id", ""))

        for field_tuple in COMPARE_FIELDS:
            field_name = field_tuple[0]
            internal_val = internal_order.get(field_name)
            broker_val = None
            for f in field_tuple[1:]:
                broker_val = broker_order.get(f)
                if broker_val is not None:
                    break

            if internal_val is not None and broker_val is not None:
                # Normalize for comparison
                str_internal = str(internal_val).lower().strip()
                str_broker = str(broker_val).lower().strip()
                if str_internal != str_broker:
                    mismatches.append(
                        f"{field_name}: internal={str_internal} vs broker={str_broker}"
                    )

        # Status-specific logic
        internal_status = str(internal_order.get("status", "")).lower()
        broker_status = str(broker_order.get("status", "")).lower()

        # Order cancelled at broker but we think it's active
        if broker_status in ("cancelled", "rejected", "expired") and internal_status not in (
            "cancelled", "cancelled", "rejected", "expired", "closed"
        ):
            mismatches.append(f"broker_cancelled: internal={internal_status}, broker={broker_status}")
            result.blocking = True

        # Order filled at broker but we don't know
        if broker_status in ("complete", "filled") and internal_status in (
            "submitted", "acknowledged", "pending"
        ):
            mismatches.append(f"broker_filled_unknown: internal={internal_status}, broker={broker_status}")
            result.blocking = True

        result.mismatches = mismatches
        result.matched = len(mismatches) == 0
        result.blocking = result.blocking or len(mismatches) >= 2

        if mismatches:
            self._reconciliation_blocked = result.blocking
            self._record_audit(
                "order_reconciliation_failed" if result.blocking else "order_reconciliation_warning",
                details={
                    "order_id": internal_order_id,
                    "broker_order_id": broker_order_id,
                    "mismatches": mismatches,
                    "blocking": result.blocking,
                },
                severity="critical" if result.blocking else "warning",
            )

        self._results.append(result)
        return result

    def is_blocked(self) -> bool:
        """True if a critical reconciliation mismatch has been detected.

        New orders should NOT be submitted while blocked.
        """
        return self._reconciliation_blocked

    def get_results(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent reconciliation results."""
        return [r.to_dict() for r in self._results[-limit:]]

    def reset_blocked(self) -> None:
        """Reset the blocked state after manual reconciliation."""
        self._reconciliation_blocked = False

    def _record_audit(self, event_type: str, details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="live_order_reconciliation",
            details={"component": "order_reconciliation", **(details or {})},
        )
