"""Command Center Snapshot — unified immutable system state snapshot.

Phase 52: Single source of truth for the operations dashboard.
Never contains secrets.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class UnifiedStatus:
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    TRADING_BLOCKED = "trading_blocked"
    RECOVERY_REQUIRED = "recovery_required"
    HALTED = "halted"
    INCIDENT_ACTIVE = "incident_active"
    ROLLBACK_ACTIVE = "rollback_active"


# Priority order: highest first
UNIFIED_STATUS_PRIORITY: list[str] = [
    UnifiedStatus.HALTED,
    UnifiedStatus.RECOVERY_REQUIRED,
    UnifiedStatus.ROLLBACK_ACTIVE,
    UnifiedStatus.TRADING_BLOCKED,
    UnifiedStatus.INCIDENT_ACTIVE,
    UnifiedStatus.DEGRADED,
    UnifiedStatus.HEALTHY,
]


@dataclass
class SystemSnapshot:
    operational_state: str = "unknown"
    health_score: float = 0.0
    uptime_seconds: float = 0.0
    degraded: bool = False
    trading_blocked: bool = False
    recovery_required: bool = False
    halted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "operational_state": self.operational_state,
            "health_score": round(self.health_score, 1),
            "uptime_seconds": round(self.uptime_seconds, 1),
            "degraded": self.degraded,
            "trading_blocked": self.trading_blocked,
            "recovery_required": self.recovery_required,
            "halted": self.halted,
        }


@dataclass
class MarketSnapshot:
    connected: bool = False
    last_tick: str = ""
    tick_age_ms: float = 0.0
    stale: bool = False
    data_quality: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "last_tick": self.last_tick,
            "tick_age_ms": round(self.tick_age_ms, 1),
            "stale": self.stale,
            "data_quality": self.data_quality,
        }


@dataclass
class BrokerSnapshot:
    connected: bool = False
    authenticated: bool = False
    session_valid: bool = False
    api_health: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "authenticated": self.authenticated,
            "session_valid": self.session_valid,
            "api_health": self.api_health,
        }


@dataclass
class ExecutionSnapshot:
    enabled: bool = False
    blocked: bool = False
    active_orders: int = 0
    unknown_orders: int = 0
    duplicate_attempts: int = 0
    execution_health: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "blocked": self.blocked,
            "active_orders": self.active_orders,
            "unknown_orders": self.unknown_orders,
            "duplicate_attempts": self.duplicate_attempts,
            "execution_health": self.execution_health,
        }


@dataclass
class PositionSnapshot:
    open_positions: int = 0
    total_exposure: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    net_pnl: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "open_positions": self.open_positions,
            "total_exposure": round(self.total_exposure, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "net_pnl": round(self.net_pnl, 2),
        }


@dataclass
class RiskSnapshot:
    risk_engine_available: bool = False
    daily_loss: float = 0.0
    daily_loss_limit: float = 0.0
    drawdown_pct: float = 0.0
    exposure: float = 0.0
    risk_blocked: bool = False
    kill_switch_active: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_engine_available": self.risk_engine_available,
            "daily_loss": round(self.daily_loss, 2),
            "daily_loss_limit": round(self.daily_loss_limit, 2),
            "drawdown_pct": round(self.drawdown_pct, 2),
            "exposure": round(self.exposure, 2),
            "risk_blocked": self.risk_blocked,
            "kill_switch_active": self.kill_switch_active,
        }


@dataclass
class CanarySnapshot:
    active: bool = False
    current_canary: str = ""
    authorization_state: str = ""
    evaluation_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "current_canary": self.current_canary,
            "authorization_state": self.authorization_state,
            "evaluation_status": self.evaluation_status,
        }


@dataclass
class RolloutSnapshot:
    current_stage: str = ""
    eligible_next_stage: str = ""
    pending_review: bool = False
    rollback_active: bool = False
    rollback_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_stage": self.current_stage,
            "eligible_next_stage": self.eligible_next_stage,
            "pending_review": self.pending_review,
            "rollback_active": self.rollback_active,
            "rollback_reason": self.rollback_reason[:100] if self.rollback_reason else "",
        }


@dataclass
class ReconciliationSnapshot:
    orders_ok: bool = True
    positions_ok: bool = True
    mismatches: int = 0
    last_reconciliation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "orders_ok": self.orders_ok,
            "positions_ok": self.positions_ok,
            "mismatches": self.mismatches,
            "last_reconciliation": self.last_reconciliation,
        }


@dataclass
class IncidentSummarySnapshot:
    open_count: int = 0
    critical_count: int = 0
    emergency_count: int = 0
    latest_incident: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "open_count": self.open_count,
            "critical_count": self.critical_count,
            "emergency_count": self.emergency_count,
            "latest_incident": self.latest_incident[:100] if self.latest_incident else "",
        }


@dataclass
class RecoverySnapshot:
    recovery_required: bool = False
    recovery_state: str = ""
    auto_resume_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_required": self.recovery_required,
            "recovery_state": self.recovery_state,
            "auto_resume_allowed": self.auto_resume_allowed,
        }


@dataclass
class IntegritySnapshot:
    config_match: bool = True
    champion_match: bool = True
    integrity_status: str = "valid"

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_match": self.config_match,
            "champion_match": self.champion_match,
            "integrity_status": self.integrity_status,
        }


@dataclass
class SafetySnapshot:
    phase43_lock: bool = True
    can_execute_live: bool = False
    activation_state: str = "locked"
    kill_switch: bool = False
    all_safety_gates_passed: bool = False
    overall_safety_status: str = "locked"

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase43_lock": self.phase43_lock,
            "can_execute_live": self.can_execute_live,
            "activation_state": self.activation_state,
            "kill_switch": self.kill_switch,
            "all_safety_gates_passed": self.all_safety_gates_passed,
            "overall_safety_status": self.overall_safety_status,
        }


@dataclass
class ApprovalSnapshot:
    latest_approval: str = ""
    approval_state: str = ""
    reviewer: str = ""
    expires_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "latest_approval": self.latest_approval,
            "approval_state": self.approval_state,
            "reviewer": self.reviewer,
            "expires_at": self.expires_at,
        }


@dataclass
class MetricsSnapshot:
    uptime_hours: float = 0.0
    mtta_seconds: float = 0.0
    mttr_seconds: float = 0.0
    heartbeat_rate: float = 0.0
    incident_count: int = 0
    rollback_count: int = 0
    recovery_count: int = 0
    health_score: float = 100.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "uptime_hours": round(self.uptime_hours, 1),
            "mtta_seconds": round(self.mtta_seconds, 1),
            "mttr_seconds": round(self.mttr_seconds, 1),
            "heartbeat_rate": round(self.heartbeat_rate, 1),
            "incident_count": self.incident_count,
            "rollback_count": self.rollback_count,
            "recovery_count": self.recovery_count,
            "health_score": round(self.health_score, 1),
        }


@dataclass
class CommandCenterSnapshot:
    """Unified immutable system state snapshot."""
    snapshot_id: str = field(default_factory=lambda: f"snap_{uuid.uuid4().hex[:12]}")
    timestamp: str = field(default_factory=_now)
    expires_at: str = field(default_factory=lambda: (
        datetime.now(timezone.utc) + timedelta(seconds=5)
    ).isoformat())
    unified_status: str = UnifiedStatus.HEALTHY

    system: SystemSnapshot = field(default_factory=SystemSnapshot)
    market: MarketSnapshot = field(default_factory=MarketSnapshot)
    broker: BrokerSnapshot = field(default_factory=BrokerSnapshot)
    execution: ExecutionSnapshot = field(default_factory=ExecutionSnapshot)
    positions: PositionSnapshot = field(default_factory=PositionSnapshot)
    risk: RiskSnapshot = field(default_factory=RiskSnapshot)
    canary: CanarySnapshot = field(default_factory=CanarySnapshot)
    rollout: RolloutSnapshot = field(default_factory=RolloutSnapshot)
    reconciliation: ReconciliationSnapshot = field(default_factory=ReconciliationSnapshot)
    incidents: IncidentSummarySnapshot = field(default_factory=IncidentSummarySnapshot)
    recovery: RecoverySnapshot = field(default_factory=RecoverySnapshot)
    integrity: IntegritySnapshot = field(default_factory=IntegritySnapshot)
    safety: SafetySnapshot = field(default_factory=SafetySnapshot)
    approval: ApprovalSnapshot = field(default_factory=ApprovalSnapshot)
    metrics: MetricsSnapshot = field(default_factory=MetricsSnapshot)

    @property
    def snapshot_age(self) -> float:
        try:
            ts = datetime.fromisoformat(self.timestamp)
            return (datetime.now(timezone.utc) - ts).total_seconds()
        except (ValueError, TypeError):
            return 999.0

    def is_stale(self, max_age_seconds: int = 5) -> bool:
        return self.snapshot_age > max_age_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "expires_at": self.expires_at,
            "snapshot_age": round(self.snapshot_age, 1),
            "unified_status": self.unified_status,
            "system": self.system.to_dict(),
            "market": self.market.to_dict(),
            "broker": self.broker.to_dict(),
            "execution": self.execution.to_dict(),
            "positions": self.positions.to_dict(),
            "risk": self.risk.to_dict(),
            "canary": self.canary.to_dict(),
            "rollout": self.rollout.to_dict(),
            "reconciliation": self.reconciliation.to_dict(),
            "incidents": self.incidents.to_dict(),
            "recovery": self.recovery.to_dict(),
            "integrity": self.integrity.to_dict(),
            "safety": self.safety.to_dict(),
            "approval": self.approval.to_dict(),
            "metrics": self.metrics.to_dict(),
        }
