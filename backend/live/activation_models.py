"""Phase 45 — Controlled Live Activation state machine and data models.

Sits between FinalApproval/PreLiveValidation and ExecutionGateway.
The ONLY component that can transition the system to LIVE execution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _new_id(prefix: str = "act") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── State Machine ──


class ActivationState(str, Enum):
    """Controlled live activation state machine."""
    LOCKED = "locked"
    READY = "ready"
    ARMED = "armed"
    ACTIVE = "active"
    PAUSED = "paused"
    KILL_SWITCHED = "kill_switched"
    EXPIRED = "expired"
    REVOKED = "revoked"


VALID_TRANSITIONS: dict[ActivationState, list[ActivationState]] = {
    ActivationState.LOCKED: [ActivationState.READY],
    ActivationState.READY: [ActivationState.ARMED, ActivationState.LOCKED],
    ActivationState.ARMED: [
        ActivationState.ACTIVE, ActivationState.EXPIRED,
        ActivationState.REVOKED, ActivationState.LOCKED,
    ],
    ActivationState.ACTIVE: [
        ActivationState.PAUSED, ActivationState.KILL_SWITCHED,
        ActivationState.EXPIRED, ActivationState.REVOKED,
    ],
    ActivationState.PAUSED: [
        ActivationState.ACTIVE, ActivationState.KILL_SWITCHED,
        ActivationState.REVOKED,
    ],
    ActivationState.KILL_SWITCHED: [ActivationState.LOCKED],
    ActivationState.EXPIRED: [ActivationState.LOCKED],
    ActivationState.REVOKED: [ActivationState.LOCKED],
}


def validate_transition(current: ActivationState, target: ActivationState) -> bool:
    """Check if a state transition is valid."""
    allowed = VALID_TRANSITIONS.get(current, [])
    return target in allowed


# ── Data Models ──


@dataclass
class StateTransition:
    """Record of a single state transition."""
    from_state: ActivationState | None = None
    to_state: ActivationState | None = None
    actor: str = ""
    reason: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state.value if self.from_state else None,
            "to_state": self.to_state.value if self.to_state else None,
            "actor": self.actor,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class PrerequisiteStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_TESTED = "not_tested"
    SKIPPED = "skipped"


@dataclass
class ActivationPrerequisite:
    """A single prerequisite for live activation."""
    check_id: str = ""
    category: str = ""
    name: str = ""
    status: PrerequisiteStatus = PrerequisiteStatus.NOT_TESTED
    passed: bool = False
    blocking: bool = False
    message: str = ""
    details: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "category": self.category,
            "name": self.name,
            "status": self.status.value,
            "passed": self.passed,
            "blocking": self.blocking,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class ActivationRecord:
    """Complete record of an activation lifecycle."""
    activation_id: str = field(default_factory=lambda: _new_id("act"))
    state: ActivationState = ActivationState.LOCKED
    previous_state: ActivationState | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    activated_at: str = ""
    expires_at: str = ""
    activation_duration_minutes: int = 30
    reviewer: str = ""
    reason: str = ""
    confirmation_token: str = ""
    champion_id: str = ""
    approval_id: str = ""
    config_hash: str = ""
    prerequisites: list[ActivationPrerequisite] = field(default_factory=list)
    history: list[StateTransition] = field(default_factory=list)
    daily_pnl: float = 0.0
    total_orders_placed: int = 0
    total_orders_blocked: int = 0
    positions_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "activation_id": self.activation_id,
            "state": self.state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "activated_at": self.activated_at,
            "expires_at": self.expires_at,
            "activation_duration_minutes": self.activation_duration_minutes,
            "reviewer": self.reviewer,
            "reason": self.reason,
            "champion_id": self.champion_id,
            "approval_id": self.approval_id,
            "config_hash": self.config_hash,
            "prerequisites_passed": sum(1 for p in self.prerequisites if p.passed),
            "prerequisites_total": len(self.prerequisites),
            "prerequisites": [p.to_dict() for p in self.prerequisites],
            "history": [h.to_dict() for h in self.history[-20:]],
            "daily_pnl": round(self.daily_pnl, 2),
            "total_orders_placed": self.total_orders_placed,
            "total_orders_blocked": self.total_orders_blocked,
            "positions_count": self.positions_count,
        }

    def summary(self) -> dict[str, Any]:
        """Compact summary for list views."""
        return {
            "activation_id": self.activation_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "activated_at": self.activated_at,
            "expires_at": self.expires_at,
            "reviewer": self.reviewer,
            "reason": self.reason[:80] if self.reason else "",
        }


# ── Audit Event Types ──

LIVE_ACTIVATION_REQUESTED = "live_activation_requested"
LIVE_ACTIVATION_APPROVED = "live_activation_approved"
LIVE_ACTIVATION_REJECTED = "live_activation_rejected"
LIVE_ACTIVATION_STARTED = "live_activation_started"
LIVE_ACTIVATION_EXPIRED = "live_activation_expired"
LIVE_ACTIVATION_REVOKED = "live_activation_revoked"
LIVE_ORDER_AUTHORIZED = "live_order_authorized"
LIVE_ORDER_BLOCKED = "live_order_blocked"
LIVE_ORDER_SUBMITTED = "live_order_submitted"
LIVE_ORDER_ACKNOWLEDGED = "live_order_acknowledged"
LIVE_ORDER_REJECTED = "live_order_rejected"
LIVE_ORDER_UNKNOWN = "live_order_unknown"
LIVE_ORDER_RECONCILIATION = "live_order_reconciliation"
LIVE_KILL_SWITCH_TRIGGERED = "live_kill_switch_triggered"
LIVE_NEW_ORDERS_PAUSED = "live_new_orders_paused"
LIVE_RECOVERY_REQUESTED = "live_recovery_requested"
LIVE_RECOVERY_APPROVED = "live_recovery_approved"
