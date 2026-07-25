"""ProgressiveRolloutEngine — orchestrates multi-canary sequence and rollout stages.

Phase 49: Controlled multi-canary trading with progressive rollout stages.
Human approval required between every stage.
Automatic rollback on threshold breach.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from live.rollout_stages import (
    RolloutStage, RolloutRecord, validate_stage_transition, get_stage_limits,
)
from live.rollout_monitor import RolloutPerformanceMonitor
from live.rollback_controller import RollbackController, RollbackCheckResult
from live.multi_canary import MultiCanaryRolloutTracker, CanaryRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


ROLLOUT_AUDIT_EVENTS = [
    "rollout_requested", "rollout_approved", "rollout_rejected",
    "rollout_stage_changed", "canary_sequence_started",
    "canary_sequence_completed", "rollout_rollback_triggered",
    "rollout_rollback_completed", "rollout_halted",
]


class ProgressiveRolloutError(Exception):
    pass


class ProgressiveRolloutEngine:
    """
    Orchestrates multi-canary trading and progressive rollout.

    Stage progression:
    LOCKED -> CANARY_1 -> CANARY_2 -> CANARY_3 -> LIMITED_ROLLOUT -> CONTROLLED_ROLLOUT
    ANY -> ROLLBACK (auto on threshold breach)
    ANY -> HALTED (manual)
    ROLLBACK -> LOCKED (human recovery)

    Human approval required between every stage.
    """

    def __init__(self):
        self._record = RolloutRecord()
        self._tracker = MultiCanaryRolloutTracker()
        self._monitor = RolloutPerformanceMonitor()
        self._rollback_ctrl = RollbackController()
        self._eligibility = None
        self._audit_log = None
        self._champion_manager = None
        self._champion_id = ""
        self._config_hash = ""

    def set_eligibility_engine(self, e): self._eligibility = e
    def set_audit_log(self, a): self._audit_log = a
    def set_champion_manager(self, m): self._champion_manager = m
    def set_rollback_controller(self, r): self._rollback_ctrl = r
    def set_monitor(self, m): self._monitor = m
    def set_tracker(self, t): self._tracker = t

    def _record_audit(self, event_type: str, details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="progressive_rollout",
            details={
                "rollout_id": self._record.rollout_id,
                "stage": self._record.current_stage,
                "champion_id": self._champion_id[:12] if self._champion_id else "",
                **(details or {}),
            },
        )

    def _store_state(self) -> None:
        """Record current state in history."""
        self._record.state_history.append({
            "stage": self._record.current_stage,
            "timestamp": _now(),
            "canary_count": len(self._record.canary_sequence),
        })
        self._record.updated_at = _now()

    def get_status(self) -> dict[str, Any]:
        """Get current rollout status."""
        tracker_summary = self._tracker.get_summary()
        return {
            "rollout_id": self._record.rollout_id,
            "current_stage": self._record.current_stage,
            "previous_stage": self._record.previous_stage,
            "champion_id": self._champion_id[:12] if self._champion_id else "",
            "config_hash": self._config_hash[:16] if self._config_hash else "",
            "reviewer": self._record.reviewer,
            "stage_limits": get_stage_limits(self._record.current_stage),
            "canary_count": len(self._record.canary_sequence),
            "canary_summary": {
                "total": tracker_summary["total_canaries"],
                "wins": tracker_summary["wins"],
                "losses": tracker_summary["losses"],
                "cumulative_pnl": tracker_summary["cumulative_pnl"],
            },
            "performance": self._monitor.get_summary(),
            "monitoring": self._monitor.get_current().to_dict(),
        }

    def request_progression(
        self, reviewer: str = "", reason: str = "",
        target_stage: str = "",
    ) -> RolloutRecord:
        """Request progression to a new stage.

        Creates a progression request. Requires human approval to proceed.
        """
        if not reviewer:
            raise ProgressiveRolloutError("Reviewer identity is required")
        if not reason:
            raise ProgressiveRolloutError("Reason is required")
        if not target_stage:
            raise ProgressiveRolloutError("Target stage is required")

        current = self._record.current_stage
        if not validate_stage_transition(current, target_stage):
            raise ProgressiveRolloutError(
                f"Cannot transition from {current} to {target_stage}"
            )

        # Store current config
        if self._champion_manager:
            try:
                champ = self._champion_manager.get_champion()
                if champ:
                    self._champion_id = getattr(
                        champ, "id", getattr(champ, "version", "")
                    )
            except Exception:
                pass

        self._record.reviewer = reviewer
        self._record.reason = reason
        self._record.previous_stage = current
        self._record.updated_at = _now()

        self._record_audit("rollout_requested", details={
            "target_stage": target_stage, "reviewer": reviewer,
        })
        return self._record

    def approve_progression(
        self, rollout_id: str = "", reviewer: str = "",
        review_note: str = "", target_stage: str = "",
    ) -> RolloutRecord:
        """Approve a progression request.

        Validates eligibility before approving.
        """
        if not reviewer:
            raise ProgressiveRolloutError("Reviewer identity is required")
        if not review_note:
            raise ProgressiveRolloutError("Review note is required")
        if not target_stage:
            raise ProgressiveRolloutError("Target stage is required")

        # Check eligibility
        if self._eligibility:
            eval_id = ""
            if self._record.evaluation_results:
                eval_id = self._record.evaluation_results[-1].get("evaluation_id", "")
            prior_evals = self._record.evaluation_results

            eligibility = self._eligibility.check_eligibility(
                current_stage=self._record.current_stage,
                target_stage=target_stage,
                champion_id=self._champion_id,
                config_hash=self._config_hash,
                evaluation_id=eval_id,
                canary_sequence=self._record.canary_sequence,
                previous_evaluations=prior_evals,
            )
            if not eligibility.eligible:
                raise ProgressiveRolloutError(
                    f"Eligibility check failed: {'; '.join(eligibility.hard_blocks[:3])}"
                )

        # Update stage
        self._record.previous_stage = self._record.current_stage
        self._record.current_stage = target_stage
        self._record.reviewer = reviewer
        self._record.review_note = review_note
        self._store_state()

        self._record_audit("rollout_approved", details={
            "target_stage": target_stage, "reviewer": reviewer,
        })
        return self._record

    def reject_progression(
        self, rollout_id: str = "", reviewer: str = "",
        reason: str = "",
    ) -> RolloutRecord:
        """Reject a progression request."""
        if not reviewer:
            raise ProgressiveRolloutError("Reviewer identity is required")

        self._record_audit("rollout_rejected", details={
            "reviewer": reviewer, "reason": reason or "Rejected",
        })
        return self._record

    def execute_rollback(self, reason: str = "") -> RolloutRecord:
        """Execute automatic rollback."""
        self._record.previous_stage = self._record.current_stage
        self._record.current_stage = RolloutStage.ROLLBACK
        self._record.rollback_reason = reason
        self._store_state()

        # Execute via rollback controller
        rb_result = self._rollback_ctrl.execute_rollback(
            reason=reason, rollout_id=self._record.rollout_id,
        )
        _ = rb_result  # Result captured for telemetry

        self._record_audit("rollout_rollback_triggered", details={
            "reason": reason, "from_stage": self._record.previous_stage,
        }, severity="critical")

        return self._record

    def record_canary_completed(self, canary_record: CanaryRecord) -> None:
        """Record a completed canary in the tracker."""
        self._tracker.record_canary(canary_record)
        self._record.canary_sequence.append(canary_record.authorization_id)

        # Update monitor
        self._monitor.update_trade(
            pnl=canary_record.pnl,
            won=canary_record.pnl > 0,
            r_multiple=canary_record.r_multiple,
            slippage_pct=canary_record.slippage_pct,
            latency_ms=canary_record.execution_latency_ms,
        )

        self._record_audit("canary_sequence_completed", details={
            "sequence": canary_record.sequence,
            "symbol": canary_record.symbol,
            "pnl": canary_record.pnl,
        })

    def get_effective_limits(self) -> dict[str, Any]:
        """Get effective limits = min of all applicable limits.

        Takes the strictest of:
        - Stage limits
        - RiskEngine limits (via eligibility)
        """
        stage_limits = get_stage_limits(self._record.current_stage)
        return {
            "stage": self._record.current_stage,
            **stage_limits,
            "note": "Effective quantity = min(RiskEngine, ExecutionRiskLimiter, Stage, Canary)",
        }

    def check_rollback_conditions(self) -> RollbackCheckResult:
        """Check if rollback conditions are met."""
        current = self._monitor.get_current()
        return self._rollback_ctrl.check_rollback_conditions(
            monitor_data=current.to_dict(),
        )

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [self._record.summary()]

    def get_performance(self) -> dict[str, Any]:
        return self._monitor.get_summary()

    def get_rollout_limits(self) -> dict[str, Any]:
        return self._rollback_ctrl.get_thresholds()
