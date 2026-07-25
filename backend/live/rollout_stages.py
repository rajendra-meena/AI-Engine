"""Rollout Stage enum and models for progressive rollout.

Phase 49: Controlled multi-stage progression from canary to limited rollout.
No stage enables unrestricted live trading.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _new_id() -> str:
    return f"roll_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RolloutStage:
    LOCKED = "locked"
    CANARY_1 = "canary_1"
    CANARY_2 = "canary_2"
    CANARY_3 = "canary_3"
    LIMITED_ROLLOUT = "limited_rollout"
    CONTROLLED_ROLLOUT = "controlled_rollout"
    FULL_REVIEW_REQUIRED = "full_review_required"
    ROLLBACK = "rollback"
    HALTED = "halted"


# Valid stage-to-stage transitions
VALID_STAGE_TRANSITIONS: dict[str, list[str]] = {
    RolloutStage.LOCKED: [RolloutStage.CANARY_1],
    RolloutStage.CANARY_1: [RolloutStage.CANARY_2, RolloutStage.ROLLBACK, RolloutStage.HALTED],
    RolloutStage.CANARY_2: [RolloutStage.CANARY_3, RolloutStage.ROLLBACK, RolloutStage.HALTED],
    RolloutStage.CANARY_3: [RolloutStage.LIMITED_ROLLOUT, RolloutStage.ROLLBACK, RolloutStage.HALTED],
    RolloutStage.LIMITED_ROLLOUT: [RolloutStage.CONTROLLED_ROLLOUT, RolloutStage.ROLLBACK, RolloutStage.HALTED],
    RolloutStage.CONTROLLED_ROLLOUT: [RolloutStage.FULL_REVIEW_REQUIRED, RolloutStage.ROLLBACK, RolloutStage.HALTED],
    RolloutStage.FULL_REVIEW_REQUIRED: [RolloutStage.ROLLBACK, RolloutStage.HALTED],
    RolloutStage.ROLLBACK: [RolloutStage.LOCKED],
    RolloutStage.HALTED: [RolloutStage.LOCKED],
}


def validate_stage_transition(current: str, target: str) -> bool:
    allowed = VALID_STAGE_TRANSITIONS.get(current, [])
    return target in allowed


# ── Stage Risk Limits (server-side immutable ceilings) ──
# CANARY stages: 1 trade max
# LIMITED_ROLLOUT: 10% of risk budget
# CONTROLLED_ROLLOUT: 25% of risk budget
# No stage allows 100% or unlimited.

STAGE_RISK_LIMITS: dict[str, dict[str, Any]] = {
    RolloutStage.CANARY_1: {
        "max_trades": 1, "max_quantity": 1, "max_notional": 10000,
        "max_loss": 500, "risk_allocation_pct": 0.0,
    },
    RolloutStage.CANARY_2: {
        "max_trades": 1, "max_quantity": 1, "max_notional": 10000,
        "max_loss": 500, "risk_allocation_pct": 0.0,
    },
    RolloutStage.CANARY_3: {
        "max_trades": 1, "max_quantity": 1, "max_notional": 10000,
        "max_loss": 500, "risk_allocation_pct": 0.0,
    },
    RolloutStage.LIMITED_ROLLOUT: {
        "max_trades": 5, "max_quantity": 10, "max_notional": 50000,
        "max_loss": 2500, "risk_allocation_pct": 10.0,
    },
    RolloutStage.CONTROLLED_ROLLOUT: {
        "max_trades": 10, "max_quantity": 25, "max_notional": 100000,
        "max_loss": 5000, "risk_allocation_pct": 25.0,
    },
}


def get_stage_limits(stage: str) -> dict[str, Any]:
    """Get risk limits for a given stage. Returns empty dict for non-trading stages."""
    return STAGE_RISK_LIMITS.get(stage, {
        "max_trades": 0, "max_quantity": 0, "max_notional": 0,
        "max_loss": 0, "risk_allocation_pct": 0.0,
    })


# ── Data Models ──


@dataclass
class RolloutRecord:
    """Complete record of a rollout progression."""
    rollout_id: str = field(default_factory=_new_id)
    current_stage: str = RolloutStage.LOCKED
    previous_stage: str = ""
    champion_id: str = ""
    config_hash: str = ""
    reviewer: str = ""
    reason: str = ""
    review_note: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    canary_sequence: list[str] = field(default_factory=list)
    evaluation_results: list[dict[str, Any]] = field(default_factory=list)
    rollback_reason: str = ""
    state_history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollout_id": self.rollout_id,
            "current_stage": self.current_stage,
            "previous_stage": self.previous_stage,
            "champion_id": self.champion_id[:12] if self.champion_id else "",
            "config_hash": self.config_hash[:16] if self.config_hash else "",
            "reviewer": self.reviewer,
            "reason": self.reason[:200] if self.reason else "",
            "review_note": self.review_note[:200] if self.review_note else "",
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "canary_sequence": self.canary_sequence,
            "evaluation_results": self.evaluation_results[-5:],
            "rollback_reason": self.rollback_reason[:200] if self.rollback_reason else "",
            "state_history": self.state_history[-20:],
            "stage_limits": get_stage_limits(self.current_stage),
        }

    def summary(self) -> dict[str, Any]:
        return {
            "rollout_id": self.rollout_id,
            "current_stage": self.current_stage,
            "champion_id": self.champion_id[:12] if self.champion_id else "",
            "canary_count": len(self.canary_sequence),
            "created_at": self.created_at,
        }
