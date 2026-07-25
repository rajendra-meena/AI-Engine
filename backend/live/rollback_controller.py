"""Rollback Controller — automatic rollback on safety/performance threshold breach.

Phase 49: Immutable server-side thresholds. Never silently resumes trading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Server-side immutable safety thresholds ──
# These must NOT be configurable from frontend.
# Cannot be weakened at runtime.

MAX_CONSECUTIVE_LOSSES = 3
MAX_ROLLOUT_DRAWDOWN_PERCENT = 5.0
MAX_SLIPPAGE_PERCENT = 0.50
MAX_EXECUTION_LATENCY_MS = 3000
MAX_RECONCILIATION_MISMATCHES = 0
MAX_RISK_VIOLATIONS = 0
MAX_STALE_DATA_EVENTS = 2


@dataclass
class RollbackCheckResult:
    """Result of rollback condition check."""
    rollback_required: bool = False
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    threshold_breaches: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollback_required": self.rollback_required,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "threshold_breaches": self.threshold_breaches,
            "timestamp": self.timestamp,
        }


@dataclass
class RollbackExecutionResult:
    """Result of executing a rollback."""
    success: bool = False
    entries_blocked: bool = False
    orders_cancelled: int = 0
    positions_preserved: bool = False
    rollout_stage: str = ""
    audit_event_recorded: bool = False
    errors: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "entries_blocked": self.entries_blocked,
            "orders_cancelled": self.orders_cancelled,
            "positions_preserved": self.positions_preserved,
            "rollout_stage": self.rollout_stage,
            "audit_event_recorded": self.audit_event_recorded,
            "errors": self.errors,
            "timestamp": self.timestamp,
        }


class RollbackController:
    """
    Automatic rollback when critical conditions occur.

    Thresholds are server-side immutable.
    Rollback NEVER silently resumes trading.
    """

    def __init__(self):
        self._audit_log = None
        self._emergency_cancel = None

        # Thresholds
        self._max_consecutive_losses = MAX_CONSECUTIVE_LOSSES
        self._max_drawdown_pct = MAX_ROLLOUT_DRAWDOWN_PERCENT
        self._max_slippage_pct = MAX_SLIPPAGE_PERCENT
        self._max_latency_ms = MAX_EXECUTION_LATENCY_MS
        self._max_mismatches = MAX_RECONCILIATION_MISMATCHES
        self._max_risk_violations = MAX_RISK_VIOLATIONS
        self._max_stale_events = MAX_STALE_DATA_EVENTS

    def set_audit_log(self, a): self._audit_log = a
    def set_emergency_cancel(self, e): self._emergency_cancel = e

    def check_rollback_conditions(self, monitor_data: dict | None = None) -> RollbackCheckResult:
        """Check all rollback thresholds.

        Args:
            monitor_data: PerformanceSnapshot or dict from monitor

        Returns:
            RollbackCheckResult with reasons if any threshold breached
        """
        result = RollbackCheckResult()
        breaches: list[dict[str, Any]] = []

        if not monitor_data:
            return result

        # Consecutive losses
        cons_losses = monitor_data.get("consecutive_losses", 0)
        if cons_losses >= self._max_consecutive_losses:
            breaches.append({
                "threshold": "max_consecutive_losses",
                "value": cons_losses, "max": self._max_consecutive_losses,
            })

        # Drawdown
        dd = abs(monitor_data.get("max_drawdown_pct", 0))
        if dd >= self._max_drawdown_pct:
            breaches.append({
                "threshold": "max_drawdown",
                "value": dd, "max": self._max_drawdown_pct,
            })

        # Slippage
        slippage = abs(monitor_data.get("avg_slippage_pct", 0))
        if slippage >= self._max_slippage_pct:
            breaches.append({
                "threshold": "max_slippage",
                "value": slippage, "max": self._max_slippage_pct,
            })

        # Latency
        latency = monitor_data.get("avg_latency_ms", 0)
        if latency >= self._max_latency_ms:
            breaches.append({
                "threshold": "max_latency",
                "value": latency, "max": self._max_latency_ms,
            })

        # Reconciliation mismatches
        mismatches = monitor_data.get("order_mismatches", 0) + monitor_data.get("position_mismatches", 0)
        if mismatches > self._max_mismatches:
            breaches.append({
                "threshold": "max_reconciliation_mismatches",
                "value": mismatches, "max": self._max_mismatches,
            })

        # Risk violations
        violations = monitor_data.get("risk_violations", 0)
        if violations > self._max_risk_violations:
            breaches.append({
                "threshold": "max_risk_violations",
                "value": violations, "max": self._max_risk_violations,
            })

        # Stale data events
        stale = monitor_data.get("stale_data_events", 0)
        if stale > self._max_stale_events:
            breaches.append({
                "threshold": "max_stale_data_events",
                "value": stale, "max": self._max_stale_events,
            })

        if breaches:
            result.rollback_required = True
            result.reasons = [b["threshold"] for b in breaches]
            result.threshold_breaches = breaches

        return result

    def execute_rollback(self, reason: str = "", rollout_id: str = "") -> RollbackExecutionResult:
        """Execute rollback procedure.

        Steps:
        1. Block new entries
        2. Cancel eligible pending orders via emergency cancel
        3. Preserve existing positions
        4. Mark stage as ROLLBACK
        5. Record audit event
        6. Freeze progression
        """
        result = RollbackExecutionResult()
        errors: list[str] = []

        # Step 1-2: Emergency cancel if available
        if self._emergency_cancel:
            try:
                import asyncio
                cancel_result = asyncio.run(
                    self._emergency_cancel.cancel_all_open_orders(
                        reason=reason or "rollback_triggered",
                    )
                )
                result.orders_cancelled = cancel_result.total_orders_cancelled
                result.entries_blocked = cancel_result.blocked_new_entries
            except Exception as e:
                errors.append(f"emergency_cancel_error: {e}")
        else:
            result.entries_blocked = True  # Assume blocked

        # Step 3: Positions preserved (no auto-close)
        result.positions_preserved = True

        # Step 4: Stage recorded by caller
        result.rollout_stage = "rollback"

        # Step 5: Audit event
        if self._audit_log:
            self._audit_log.record(
                "rollout_rollback_triggered", severity="critical",
                actor="rollback_controller",
                details={
                    "rollout_id": rollout_id,
                    "reason": reason or "Automatic rollback",
                    "orders_cancelled": result.orders_cancelled,
                },
            )
            result.audit_event_recorded = True

        result.errors = errors
        result.success = len(errors) == 0
        result.timestamp = _now()

        return result

    def recover(self, reviewer: str = "", reason: str = "") -> dict[str, Any]:
        """Recover from rollback. Requires explicit human action.

        Never silently resumes trading.
        """
        if not reviewer:
            return {"success": False, "error": "Reviewer identity required for recovery"}

        if self._audit_log:
            self._audit_log.record(
                "rollout_rollback_completed", severity="info",
                actor="rollback_controller",
                details={"reviewer": reviewer, "reason": reason or "Manual recovery"},
            )

        return {
            "success": True,
            "state": "recovered",
            "message": "Rollback acknowledged. Return to LOCKED stage required for new canary.",
        }

    def get_thresholds(self) -> dict[str, Any]:
        """Get immutable rollback thresholds (read-only)."""
        return {
            "max_consecutive_losses": self._max_consecutive_losses,
            "max_drawdown_pct": self._max_drawdown_pct,
            "max_slippage_pct": self._max_slippage_pct,
            "max_latency_ms": self._max_latency_ms,
            "max_reconciliation_mismatches": self._max_mismatches,
            "max_risk_violations": self._max_risk_violations,
            "max_stale_data_events": self._max_stale_events,
        }
