"""System Health Monitor — full system health status.

Phase 50: Aggregates component statuses, detects critical failures.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HealthStatus:
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    WARNING = "warning"
    CRITICAL = "critical"
    HALTED = "halted"
    RECOVERY_REQUIRED = "recovery_required"


@dataclass
class HealthSnapshot:
    """Complete system health snapshot."""
    status: str = HealthStatus.HEALTHY
    timestamp: str = field(default_factory=_now)
    uptime_seconds: float = 0.0
    process_id: int = 0
    database_status: str = "unknown"
    broker_status: str = "unknown"
    market_data_status: str = "unknown"
    websocket_status: str = "unknown"
    risk_engine_status: str = "unknown"
    execution_gate_status: str = "unknown"
    reconciliation_status: str = "unknown"
    kill_switch_status: str = "unknown"
    champion_status: str = "unknown"
    rollout_status: str = "unknown"
    persistence_status: str = "unknown"
    last_heartbeat: str = ""
    last_successful_tick: str = ""
    last_successful_order: str = ""
    last_reconciliation: str = ""
    active_alerts: int = 0
    critical_failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "timestamp": self.timestamp,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "process_id": self.process_id,
            "component_statuses": {
                "database": self.database_status,
                "broker": self.broker_status,
                "market_data": self.market_data_status,
                "websocket": self.websocket_status,
                "risk_engine": self.risk_engine_status,
                "execution_gate": self.execution_gate_status,
                "reconciliation": self.reconciliation_status,
                "kill_switch": self.kill_switch_status,
                "champion": self.champion_status,
                "rollout": self.rollout_status,
                "persistence": self.persistence_status,
            },
            "last_heartbeat": self.last_heartbeat,
            "last_successful_tick": self.last_successful_tick,
            "last_successful_order": self.last_successful_order,
            "last_reconciliation": self.last_reconciliation,
            "active_alerts": self.active_alerts,
            "critical_failures": self.critical_failures,
        }


class SystemHealthMonitor:
    """Monitors overall system health from component statuses."""

    def __init__(self):
        self._start_time = time.time()
        self._snapshot = HealthSnapshot(process_id=os.getpid())
        self._heartbeat = None
        self._alert_mgr = None

    def set_heartbeat(self, hb): self._heartbeat = hb
    def set_alert_manager(self, am): self._alert_mgr = am

    def update_component(self, component: str, status: str) -> None:
        """Update a single component's status."""
        if hasattr(self._snapshot, f"{component}_status"):
            setattr(self._snapshot, f"{component}_status", status)
        self._recompute()

    def _recompute(self) -> None:
        """Recompute overall health from component statuses."""
        snapshot = self._snapshot
        criticals = []
        for comp_field in [
            "database_status", "broker_status", "market_data_status",
            "websocket_status", "risk_engine_status", "execution_gate_status",
            "reconciliation_status", "kill_switch_status", "persistence_status",
        ]:
            val = getattr(snapshot, comp_field, "unknown")
            if val in ("critical", "halted", "recovery_required"):
                criticals.append(comp_field.replace("_status", ""))

        if criticals:
            snapshot.status = HealthStatus.CRITICAL
            snapshot.critical_failures = criticals
        elif any(
            getattr(snapshot, f, "healthy") in ("degraded", "warning")
            for f in [
                "broker_status", "market_data_status", "websocket_status",
                "reconciliation_status",
            ]
        ):
            snapshot.status = HealthStatus.DEGRADED
        else:
            snapshot.status = HealthStatus.HEALTHY

    def snapshot(self) -> dict[str, Any]:
        """Take a full health snapshot."""
        s = self._snapshot
        s.timestamp = _now()
        s.uptime_seconds = time.time() - self._start_time
        s.active_alerts = self._alert_mgr.active_count() if self._alert_mgr else 0

        if self._heartbeat:
            hb_summary = self._heartbeat.get_summary()
            s.last_heartbeat = _now()
            if not hb_summary["all_healthy"]:
                self.update_component("heartbeat", "degraded")

        self._recompute()
        return s.to_dict()

    def get_status(self) -> str:
        return self._snapshot.status

    def mark_healthy(self) -> None:
        self._snapshot.status = HealthStatus.HEALTHY

    def mark_critical(self, reason: str) -> None:
        self._snapshot.status = HealthStatus.CRITICAL
        if reason not in self._snapshot.critical_failures:
            self._snapshot.critical_failures.append(reason)
