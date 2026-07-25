"""Operational Event Bus — publish/subscribe for system events with immutable records.

Phase 51: Decoupled from trading EventBus. No secrets in metadata.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"evt_{uuid.uuid4().hex[:12]}"


# ── Centralized Event Types ──

# System
SYSTEM_STARTED = "system_started"
SYSTEM_READY = "system_ready"
SYSTEM_DEGRADED = "system_degraded"
SYSTEM_HALTED = "system_halted"

# Heartbeat
HEARTBEAT_MISSED = "heartbeat_missed"
HEARTBEAT_RECOVERED = "heartbeat_recovered"

# Market Data
MARKET_DATA_STALE = "market_data_stale"
MARKET_DATA_RECOVERED = "market_data_recovered"

# Broker
BROKER_DISCONNECTED = "broker_disconnected"
BROKER_RECONNECTED = "broker_reconnected"
BROKER_SESSION_EXPIRED = "broker_session_expired"

# Orders
ORDER_SUBMITTED = "order_submitted"
ORDER_ACCEPTED = "order_accepted"
ORDER_REJECTED = "order_rejected"
ORDER_FILLED = "order_filled"
ORDER_UNKNOWN = "order_unknown"

# Positions
POSITION_MISMATCH = "position_mismatch"
POSITION_RECONCILED = "position_reconciled"

# Reconciliation
RECONCILIATION_STARTED = "reconciliation_started"
RECONCILIATION_FAILED = "reconciliation_failed"
RECONCILIATION_COMPLETED = "reconciliation_completed"

# Risk
RISK_BLOCK = "risk_block"
RISK_LIMIT_BREACH = "risk_limit_breach"

# Kill Switch
KILL_SWITCH_TRIGGERED = "kill_switch_triggered"
KILL_SWITCH_CLEARED = "kill_switch_cleared"

# Integrity
CONFIG_INTEGRITY_FAILURE = "config_integrity_failure"
CHAMPION_INTEGRITY_FAILURE = "champion_integrity_failure"

# Recovery
RECOVERY_REQUIRED = "recovery_required"
RECOVERY_STARTED = "recovery_started"
RECOVERY_COMPLETED = "recovery_completed"
RECOVERY_FAILED = "recovery_failed"

# Rollback
ROLLBACK_TRIGGERED = "rollback_triggered"
ROLLBACK_COMPLETED = "rollback_completed"

# Canary
CANARY_STARTED = "canary_started"
CANARY_COMPLETED = "canary_completed"
CANARY_FAILED = "canary_failed"

# Approval
APPROVAL_REQUESTED = "approval_requested"
APPROVAL_GRANTED = "approval_granted"
APPROVAL_REJECTED = "approval_rejected"
APPROVAL_EXPIRED = "approval_expired"

# Infrastructure
AUDIT_WRITE_FAILURE = "audit_write_failure"
PERSISTENCE_FAILURE = "persistence_failure"

# Security
SECURITY_EVENT = "security_event"
UNAUTHORIZED_OPERATION = "unauthorized_operation"

# Incident
INCIDENT_ACKNOWLEDGED = "incident_acknowledged"
INCIDENT_MITIGATION_STARTED = "incident_mitigation_started"
INCIDENT_RESOLVED = "incident_resolved"
INCIDENT_CLOSED = "incident_closed"
RUNBOOK_VIEWED = "runbook_viewed"
OPERATIONAL_OVERRIDE_REQUESTED = "operational_override_requested"

# Trading
TRADING_BLOCKED = "trading_blocked"
TRADING_ALLOWED = "trading_allowed"

ALL_EVENT_TYPES = [
    v for k, v in list(globals().items())
    if isinstance(v, str) and v.startswith((
        "system_", "heartbeat_", "market_data_", "broker_", "order_",
        "position_", "reconciliation_", "risk_", "kill_", "config_",
        "champion_", "recovery_", "rollback_", "canary_", "approval_",
        "audit_", "persistence_", "security_", "incident_", "runbook_",
        "operational_", "trading_",
    ))
]


@dataclass
class OperationalEvent:
    """Immutable operational event record."""
    event_id: str = field(default_factory=_new_id)
    timestamp: str = field(default_factory=_now)
    event_type: str = ""
    severity: str = "info"
    component: str = ""
    source: str = ""
    symbol: str = ""
    order_id: str = ""
    position_id: str = ""
    incident_id: str = ""
    operational_state: str = ""
    trading_allowed: bool = False
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "severity": self.severity,
            "component": self.component,
            "source": self.source,
            "symbol": self.symbol,
            "order_id": self.order_id,
            "position_id": self.position_id,
            "incident_id": self.incident_id,
            "operational_state": self.operational_state,
            "trading_allowed": self.trading_allowed,
            "message": self.message[:200] if self.message else "",
            "correlation_id": self.correlation_id,
        }


EventHandler = Callable[[OperationalEvent], None]


class OperationalEventBus:
    """Publish/subscribe event bus for operational events.

    Immutable event records. No secrets in metadata.
    """

    def __init__(self, max_events: int = 10000):
        self._events: dict[str, OperationalEvent] = {}
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._max_events = max_events

    def publish(self, event: OperationalEvent) -> str:
        """Publish an event. Returns event_id."""
        self._events[event.event_id] = event
        # Enforce max events
        if len(self._events) > self._max_events:
            excess = len(self._events) - self._max_events
            for eid in list(self._events.keys())[:excess]:
                del self._events[eid]
        # Notify subscribers
        for handler in self._subscribers.get(event.event_type, []):
            try:
                handler(event)
            except Exception:
                pass
        for handler in self._subscribers.get("*", []):
            try:
                handler(event)
            except Exception:
                pass
        return event.event_id

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an event type. Use '*' for all events."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent events."""
        events = list(self._events.values())[-limit:]
        return list(reversed([e.to_dict() for e in events]))

    def get_by_id(self, event_id: str) -> OperationalEvent | None:
        return self._events.get(event_id)

    def get_by_type(self, event_type: str, limit: int = 50) -> list[dict[str, Any]]:
        matching = [e for e in self._events.values() if e.event_type == event_type]
        return [e.to_dict() for e in matching[-limit:]]

    def clear_expired(self, max_age_hours: int = 48) -> int:
        """Remove events older than max_age_hours."""
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        to_remove = []
        for eid, event in self._events.items():
            try:
                ts = datetime.fromisoformat(event.timestamp).timestamp()
                if ts < cutoff:
                    to_remove.append(eid)
            except (ValueError, TypeError):
                to_remove.append(eid)
        for eid in to_remove:
            del self._events[eid]
        return len(to_remove)

    def event_count(self) -> int:
        return len(self._events)

    def get_health(self) -> dict[str, Any]:
        return {
            "total_events": self.event_count(),
            "subscriber_count": sum(len(v) for v in self._subscribers.values()),
        }
