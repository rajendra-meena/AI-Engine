"""Rollout Governance Models — evaluation-driven rollout state machine.

Phase 48: Determines whether the system is ready for the next controlled step.
Never enables unrestricted live trading.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RolloutGovernanceState:
    NOT_ELIGIBLE = "not_eligible"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    CONTROLLED_NEXT_STEP_ELIGIBLE = "controlled_next_step_eligible"
    ROLLOUT_BLOCKED = "rollout_blocked"
    ROLLBACK_REQUIRED = "rollback_required"


class HumanReviewDecision:
    ACCEPT_CANARY = "accept_canary"
    REJECT_CANARY = "reject_canary"
    REQUEST_MORE_DATA = "request_more_data"
    ROLLBACK = "rollback"


@dataclass
class RolloutGovernanceReport:
    """Complete rollout governance report for a canary evaluation."""
    governance_id: str = field(default_factory=lambda: f"gov_{uuid.uuid4().hex[:12]}")
    evaluation_id: str = ""
    state: str = RolloutGovernanceState.NOT_ELIGIBLE
    review_required: bool = True
    reviewer: str = ""
    review_note: str = ""
    decision: str = ""
    recommendations: list[str] = field(default_factory=list)
    canary_id: str = ""
    created_at: str = field(default_factory=_now)
    reviewed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "governance_id": self.governance_id,
            "evaluation_id": self.evaluation_id,
            "state": self.state,
            "review_required": self.review_required,
            "reviewer": self.reviewer,
            "review_note": self.review_note[:200] if self.review_note else "",
            "decision": self.decision,
            "recommendations": self.recommendations,
            "canary_id": self.canary_id,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "governance_id": self.governance_id,
            "evaluation_id": self.evaluation_id,
            "state": self.state,
            "decision": self.decision,
            "reviewer": self.reviewer,
            "canary_id": self.canary_id,
            "created_at": self.created_at,
        }


@dataclass
class MultiCanaryTracker:
    """Tracks cumulative stats across multiple canary executions."""
    total_canaries: int = 0
    completed_canaries: int = 0
    failed_canaries: int = 0
    cumulative_pnl: float = 0.0
    wins: int = 0
    losses: int = 0
    avg_slippage_pct: float = 0.0
    avg_latency_ms: float = 0.0
    reconciliation_failures: int = 0
    broker_errors: int = 0
    risk_violations: int = 0
    sl_target_violations: int = 0
    data_quality_incidents: int = 0
    kill_switch_incidents: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_canaries": self.total_canaries,
            "completed_canaries": self.completed_canaries,
            "failed_canaries": self.failed_canaries,
            "cumulative_pnl": round(self.cumulative_pnl, 2),
            "wins": self.wins,
            "losses": self.losses,
            "avg_slippage_pct": round(self.avg_slippage_pct, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "reconciliation_failures": self.reconciliation_failures,
            "broker_errors": self.broker_errors,
            "risk_violations": self.risk_violations,
            "sl_target_violations": self.sl_target_violations,
            "data_quality_incidents": self.data_quality_incidents,
            "kill_switch_incidents": self.kill_switch_incidents,
        }
