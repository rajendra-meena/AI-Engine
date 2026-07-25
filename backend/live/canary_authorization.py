"""Canary Authorization Model — explicit request/approve/arm/execute workflow.

Phase 47: Every canary trade requires a narrowly scoped, time-limited,
auditable authorization. Single-trade only. MAX_TRADES = 1.
"""

from __future__ import annotations

import uuid
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"can_auth_{uuid.uuid4().hex[:12]}"


CANARY_STORE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data_cache", "canary_store.json"
)

CANARY_MAX_DURATION_MINUTES = 30
MAX_CANARY_TRADES = 1


# ── Audit Event Types ──

CANARY_AUTH_REQUESTED = "canary_auth_requested"
CANARY_AUTH_APPROVED = "canary_auth_approved"
CANARY_ARMED = "canary_armed"
CANARY_PRECHECK_STARTED = "canary_precheck_started"
CANARY_PRECHECK_PASSED = "canary_precheck_passed"
CANARY_PRECHECK_BLOCKED = "canary_precheck_blocked"
CANARY_EXECUTION_STARTED = "canary_execution_started"
CANARY_ORDER_SUBMITTED = "canary_order_submitted"
CANARY_ORDER_ACKNOWLEDGED = "canary_order_acknowledged"
CANARY_ORDER_FILLED = "canary_order_filled"
CANARY_ORDER_REJECTED = "canary_order_rejected"
CANARY_ORDER_UNKNOWN = "canary_order_unknown"
CANARY_POSITION_RECONCILED = "canary_position_reconciled"
CANARY_POSITION_MISMATCH = "canary_position_mismatch"
CANARY_COMPLETED = "canary_completed"
CANARY_FAILED = "canary_failed"
CANARY_EXPIRED = "canary_expired"


class CanaryAuthState:
    REQUESTED = "requested"
    APPROVED = "approved"
    ARMED = "armed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


VALID_TRANSITIONS: dict[str, list[str]] = {
    CanaryAuthState.REQUESTED: [CanaryAuthState.APPROVED, CanaryAuthState.CANCELLED],
    CanaryAuthState.APPROVED: [CanaryAuthState.ARMED, CanaryAuthState.CANCELLED, CanaryAuthState.EXPIRED],
    CanaryAuthState.ARMED: [CanaryAuthState.EXECUTING, CanaryAuthState.CANCELLED, CanaryAuthState.EXPIRED],
    CanaryAuthState.EXECUTING: [CanaryAuthState.COMPLETED, CanaryAuthState.FAILED, CanaryAuthState.EXPIRED],
    CanaryAuthState.COMPLETED: [],
    CanaryAuthState.CANCELLED: [],
    CanaryAuthState.EXPIRED: [],
    CanaryAuthState.FAILED: [],
}


def validate_transition(current: str, target: str) -> bool:
    """Check if a state transition is valid."""
    allowed = VALID_TRANSITIONS.get(current, [])
    return target in allowed


@dataclass
class AuthStateTransition:
    from_state: str = ""
    to_state: str = ""
    actor: str = ""
    reason: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "actor": self.actor,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class CanaryAuthorization:
    """A single canary trade authorization."""
    authorization_id: str = field(default_factory=_new_id)
    state: str = CanaryAuthState.REQUESTED
    reviewer: str = ""
    reason: str = ""
    created_at: str = field(default_factory=_now)
    approved_at: str = ""
    armed_at: str = ""
    expires_at: str = ""
    approved_config_hash: str = ""
    approved_strategy_version: str = ""
    approved_symbol: str = ""
    approved_exchange: str = "NSE"
    approved_direction: str = ""
    approved_quantity: int = 0
    max_notional: float = 0.0
    max_risk: float = 0.0
    max_trades: int = MAX_CANARY_TRADES
    max_daily_loss: float = 500.0
    price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    order_id: str = ""
    broker_order_id: str = ""
    position_id: str = ""
    pnl: float = 0.0
    failure_reason: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorization_id": self.authorization_id,
            "state": self.state,
            "reviewer": self.reviewer,
            "reason": self.reason[:200] if self.reason else "",
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "armed_at": self.armed_at,
            "expires_at": self.expires_at,
            "approved_config_hash": self.approved_config_hash[:16] if self.approved_config_hash else "",
            "approved_strategy_version": self.approved_strategy_version[:16] if self.approved_strategy_version else "",
            "approved_symbol": self.approved_symbol,
            "approved_exchange": self.approved_exchange,
            "approved_direction": self.approved_direction,
            "approved_quantity": self.approved_quantity,
            "max_notional": self.max_notional,
            "max_risk": self.max_risk,
            "max_trades": self.max_trades,
            "max_daily_loss": self.max_daily_loss,
            "price": self.price,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "order_id": self.order_id,
            "broker_order_id": self.broker_order_id,
            "pnl": round(self.pnl, 2),
            "failure_reason": self.failure_reason[:200] if self.failure_reason else "",
            "history": self.history[-20:],
        }

    def summary(self) -> dict[str, Any]:
        return {
            "authorization_id": self.authorization_id,
            "state": self.state,
            "reviewer": self.reviewer,
            "reason": self.reason[:80] if self.reason else "",
            "approved_symbol": self.approved_symbol,
            "approved_direction": self.approved_direction,
            "approved_quantity": self.approved_quantity,
            "expires_at": self.expires_at,
            "broker_order_id": self.broker_order_id,
            "pnl": round(self.pnl, 2),
        }


# ── Persistence ──


def _get_store_path() -> str:
    """Get path to canary store JSON file."""
    return CANARY_STORE_PATH


def _save_authorizations(auths: dict[str, dict]) -> None:
    """Persist authorization store to JSON file."""
    path = _get_store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(auths, f, indent=2, default=str)


def _load_authorizations() -> dict[str, dict]:
    """Load authorization store from JSON file."""
    path = _get_store_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}
