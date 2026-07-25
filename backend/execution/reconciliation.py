"""Order Reconciliation Engine — compares internal vs broker order state."""

from __future__ import annotations
from typing import Any

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _new_id() -> str:
    return f"rec_{uuid.uuid4().hex[:10]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReconciliationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReconciliationIssueState(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    BLOCKING = "blocking"


@dataclass
class ReconciliationIssue:
    """A discrepancy between internal and broker order state."""
    issue_id: str = field(default_factory=_new_id)
    severity: ReconciliationSeverity = ReconciliationSeverity.INFO
    order_id: str = ""
    broker_order_id: str = ""
    internal_state: str = ""
    broker_state: str = ""
    description: str = ""
    timestamp: str = field(default_factory=_now)
    resolution_state: ReconciliationIssueState = ReconciliationIssueState.OPEN
    resolved_at: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "severity": self.severity.value,
            "order_id": self.order_id,
            "broker_order_id": self.broker_order_id,
            "internal_state": self.internal_state,
            "broker_state": self.broker_state,
            "description": self.description,
            "timestamp": self.timestamp,
            "resolution_state": self.resolution_state.value,
            "resolved_at": self.resolved_at,
            "details": self.details,
        }


class OrderReconciliationEngine:
    """
    Compares internal order state against broker-reported state.
    Never silently overwrites state — every discrepancy generates a ReconciliationIssue.
    """

    def __init__(self):
        self._issues: list[ReconciliationIssue] = []

    def reconcile(
        self,
        internal_order: dict[str, Any],
        broker_order: dict[str, Any] | None,
    ) -> list[ReconciliationIssue]:
        """Compare internal vs broker order state. Returns new issues found."""
        order_id = internal_order.get("internal_order_id", "")
        broker_order_id = internal_order.get("broker_order_id", "")
        findings: list[ReconciliationIssue] = []

        # Missing broker order
        if broker_order is None:
            issue = ReconciliationIssue(
                severity=ReconciliationSeverity.ERROR,
                order_id=order_id,
                broker_order_id=broker_order_id,
                internal_state=internal_order.get("state", ""),
                broker_state="nonexistent",
                description="Order exists internally but not found at broker",
            )
            findings.append(issue)
            self._issues.append(issue)
            return findings

        broker_status = broker_order.get("status", "unknown")

        # Unknown broker order (no internal tracking)
        if not order_id:
            issue = ReconciliationIssue(
                severity=ReconciliationSeverity.WARNING,
                order_id="",
                broker_order_id=broker_order.get("order_id", ""),
                internal_state="untracked",
                broker_state=broker_status,
                description="Order exists at broker but is not tracked internally",
            )
            findings.append(issue)
            self._issues.append(issue)
            return findings

        # Status mismatch
        internal_state = internal_order.get("state", "")
        mapped_broker_status = self._map_broker_status(broker_status)
        if internal_state != mapped_broker_status and not self._is_equivalent(internal_state, mapped_broker_status):
            issue = ReconciliationIssue(
                severity=ReconciliationSeverity.WARNING,
                order_id=order_id,
                broker_order_id=broker_order_id,
                internal_state=internal_state,
                broker_state=broker_status,
                description=f"Status mismatch: internal={internal_state}, broker={broker_status}",
            )
            findings.append(issue)
            self._issues.append(issue)

        # Quantity mismatch
        internal_qty = internal_order.get("quantity", 0)
        broker_qty = broker_order.get("quantity", 0)
        if broker_qty and internal_qty != broker_qty:
            issue = ReconciliationIssue(
                severity=ReconciliationSeverity.WARNING,
                order_id=order_id,
                broker_order_id=broker_order_id,
                internal_state=str(internal_qty),
                broker_state=str(broker_qty),
                description=f"Quantity mismatch: internal={internal_qty}, broker={broker_qty}",
            )
            findings.append(issue)
            self._issues.append(issue)

        # Fill mismatch
        internal_filled = internal_order.get("filled_quantity", 0)
        broker_filled = broker_order.get("filled_quantity", 0)
        if broker_filled is not None and internal_filled != broker_filled:
            issue = ReconciliationIssue(
                severity=ReconciliationSeverity.WARNING,
                order_id=order_id,
                broker_order_id=broker_order_id,
                internal_state=str(internal_filled),
                broker_state=str(broker_filled),
                description=f"Fill mismatch: internal_filled={internal_filled}, broker_filled={broker_filled}",
            )
            findings.append(issue)
            self._issues.append(issue)

        # Price mismatch
        internal_price = internal_order.get("average_fill_price")
        broker_price = broker_order.get("average_price")
        if internal_price and broker_price and abs(internal_price - broker_price) > 0.01:
            issue = ReconciliationIssue(
                severity=ReconciliationSeverity.INFO,
                order_id=order_id,
                broker_order_id=broker_order_id,
                internal_state=str(internal_price),
                broker_state=str(broker_price),
                description=f"Price mismatch: internal={internal_price:.2f}, broker={broker_price:.2f}",
            )
            findings.append(issue)
            self._issues.append(issue)

        # Cancelled internally but active at broker
        if internal_state in ("cancelled", "cancel_requested") and broker_status not in (
            "cancelled", "cancelled", "rejected"
        ):
            issue = ReconciliationIssue(
                severity=ReconciliationSeverity.ERROR,
                order_id=order_id,
                broker_order_id=broker_order_id,
                internal_state=internal_state,
                broker_state=broker_status,
                description="Order cancelled internally but still active at broker",
            )
            findings.append(issue)
            self._issues.append(issue)

        return findings

    def _map_broker_status(self, broker_status: str) -> str:
        """Map broker status string to internal state string."""
        mapping = {
            "open": "submitted",
            "pending": "submitted",
            "trigger_pending": "submitted",
            "complete": "filled",
            "filled": "filled",
            "partially_filled": "partially_filled",
            "cancelled": "cancelled",
            "cancelled": "cancelled",
            "rejected": "rejected",
            "expired": "rejected",
            "not_found": "unknown",
            "unknown": "unknown",
        }
        return mapping.get(broker_status.lower(), broker_status.lower())

    def _is_equivalent(self, internal: str, broker: str) -> bool:
        """Check if two states are semantically equivalent."""
        equivalents = [
            {"submitted", "acknowledged"},
            {"filled", "closed"},
        ]
        for eq_set in equivalents:
            if internal in eq_set and broker in eq_set:
                return True
        return False

    def get_issues(
        self,
        severity: ReconciliationSeverity | None = None,
        resolution: ReconciliationIssueState | None = None,
        limit: int = 100,
    ) -> list[ReconciliationIssue]:
        """Get reconciliation issues with optional filters."""
        result = self._issues
        if severity:
            result = [i for i in result if i.severity == severity]
        if resolution:
            result = [i for i in result if i.resolution_state == resolution]
        return list(result[-limit:])

    def get_blocking_issues(self) -> list[ReconciliationIssue]:
        """Get issues that should block execution."""
        return [
            i for i in self._issues
            if i.severity in (ReconciliationSeverity.ERROR, ReconciliationSeverity.CRITICAL)
            and i.resolution_state in (ReconciliationIssueState.OPEN, ReconciliationIssueState.BLOCKING)
        ]

    def resolve_issue(self, issue_id: str) -> bool:
        """Mark an issue as resolved."""
        for issue in self._issues:
            if issue.issue_id == issue_id:
                issue.resolution_state = ReconciliationIssueState.RESOLVED
                issue.resolved_at = _now()
                return True
        return False

    def count(self) -> int:
        return len(self._issues)
