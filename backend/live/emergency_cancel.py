"""Emergency Cancel Manager — cancels all open orders at the broker.

Phase 46: After emergency cancellation, NEW ENTRIES = BLOCKED.
Requires explicit human recovery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EmergencyCancelResult:
    """Result of emergency cancel operation."""
    success: bool = False
    total_orders_cancelled: int = 0
    failed_cancellations: int = 0
    blocked_new_entries: bool = False
    errors: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "total_orders_cancelled": self.total_orders_cancelled,
            "failed_cancellations": self.failed_cancellations,
            "blocked_new_entries": self.blocked_new_entries,
            "errors": self.errors,
            "timestamp": self.timestamp,
        }


TRIGGER_REASONS = {
    "kill_switch": "Emergency kill switch triggered",
    "reconciliation_failure": "Order reconciliation failure",
    "position_mismatch": "Position reconciliation mismatch",
    "stale_market_data": "Market data stale threshold exceeded",
    "excessive_slippage": "Excessive slippage detected",
    "daily_loss_limit": "Daily loss limit reached",
    "health_failure": "System health check failure",
    "activation_expiry": "Activation window expired",
    "manual_emergency": "Manual emergency request",
}


class EmergencyCancelManager:
    """
    Manages emergency cancellation of all open orders.

    After cancellation:
    - NEW ENTRIES = BLOCKED
    - Requires explicit human recovery
    - Does NOT close existing positions
    """

    def __init__(self):
        self._emergency_active = False
        self._last_result: EmergencyCancelResult | None = None
        self._audit_log = None
        self._kill_switch = None

    def set_audit_log(self, audit): self._audit_log = audit
    def set_kill_switch(self, ks): self._kill_switch = ks

    async def cancel_all_open_orders(
        self,
        broker=None,
        reason: str = "manual_emergency",
    ) -> EmergencyCancelResult:
        """Cancel all open orders at the broker.

        Triggers:
        - kill_switch, reconciliation_failure, position_mismatch,
          stale_market_data, excessive_slippage, daily_loss_limit,
          health_failure, activation_expiry, manual_emergency

        Args:
            broker: Broker adapter to cancel orders through
            reason: Trigger reason key from TRIGGER_REASONS

        Returns:
            EmergencyCancelResult with cancellation details
        """
        result = EmergencyCancelResult()
        reason_text = TRIGGER_REASONS.get(reason, reason)

        # Activate kill switch if available
        if self._kill_switch:
            try:
                from execution.kill_switch import KillSwitchLevel
                self._kill_switch.activate(
                    KillSwitchLevel.GLOBAL, "",
                    f"Emergency cancel: {reason_text}",
                )
            except Exception as e:
                result.errors.append(f"kill_switch_error: {e}")

        # Cancel orders via broker
        if broker and hasattr(broker, 'get_orders'):
            try:
                import asyncio
                open_orders = await broker.get_orders()
                # Filter for cancellable orders
                cancellable = [
                    o for o in open_orders
                    if o.get("status", "").lower() in (
                        "open", "pending", "submitted", "acknowledged",
                        "trigger_pending",
                    )
                ]

                for order in cancellable:
                    try:
                        order_id = order.get("order_id", order.get("broker_order_id", ""))
                        if order_id:
                            await broker.cancel_order(order_id)
                            result.total_orders_cancelled += 1
                    except Exception as e:
                        result.failed_cancellations += 1
                        result.errors.append(f"cancel_failed: {order.get('order_id', '')}: {e}")

            except Exception as e:
                result.errors.append(f"get_orders_failed: {e}")

        # Block new entries
        self._emergency_active = True
        result.blocked_new_entries = True
        result.success = True
        result.timestamp = _now()
        self._last_result = result

        self._record_audit(
            "emergency_cancel_completed",
            details={
                "reason": reason_text,
                "total_cancelled": result.total_orders_cancelled,
                "failed": result.failed_cancellations,
                "errors": result.errors,
            },
            severity="critical",
        )

        return result

    def is_emergency_active(self) -> bool:
        return self._emergency_active

    def reset_emergency(self, reviewer: str = "", reason: str = "") -> dict[str, Any]:
        """Reset emergency state after human review.

        Required:
            reviewer: Human identity confirming recovery
            reason: Reason for reset

        Returns:
            Dict with reset status
        """
        if not reviewer:
            return {"success": False, "error": "Reviewer identity required"}

        self._emergency_active = False
        self._last_result = None

        self._record_audit(
            "emergency_cancel_reset",
            details={
                "reviewer": reviewer,
                "reason": reason or "Manual reset",
            },
            severity="info",
        )

        return {
            "success": True,
            "state": "normal",
            "message": "Emergency state reset. New entries allowed.",
        }

    def get_last_result(self) -> EmergencyCancelResult | None:
        return self._last_result

    def get_status(self) -> dict[str, Any]:
        return {
            "emergency_active": self._emergency_active,
            "last_emergency": self._last_result.to_dict() if self._last_result else None,
        }

    def _record_audit(self, event_type: str, details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="emergency_cancel_manager",
            details={"component": "emergency_cancel", **(details or {})},
        )
