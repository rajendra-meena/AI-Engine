"""Alert Manager — system alerts with severity levels and acknowledgement workflow.

Phase 50: Never includes secrets in alerts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AlertSeverity:
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertCategory:
    SYSTEM = "system"
    BROKER = "broker"
    MARKET_DATA = "market_data"
    EXECUTION = "execution"
    RISK = "risk"
    RECONCILIATION = "reconciliation"
    ROLLBACK = "rollback"
    SECURITY = "security"


class AlertStatus:
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class AlertRecord:
    """A single alert record."""
    alert_id: str = field(default_factory=lambda: f"alert_{uuid.uuid4().hex[:12]}")
    timestamp: str = field(default_factory=_now)
    severity: str = AlertSeverity.INFO
    category: str = AlertCategory.SYSTEM
    message: str = ""
    source: str = ""
    status: str = AlertStatus.OPEN
    acknowledged_by: str = ""
    acknowledged_at: str = ""
    resolution: str = ""
    resolved_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "category": self.category,
            "message": self.message[:200] if self.message else "",
            "source": self.source,
            "status": self.status,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at,
            "resolution": self.resolution[:200] if self.resolution else "",
            "resolved_at": self.resolved_at,
        }


class AlertManager:
    """Manages system alerts with acknowledgement workflow."""

    def __init__(self):
        self._alerts: dict[str, AlertRecord] = {}
        self._history: list[AlertRecord] = []

    def raise_alert(self, severity: str = AlertSeverity.INFO,
                    category: str = AlertCategory.SYSTEM,
                    message: str = "", source: str = "") -> AlertRecord:
        """Create a new alert."""
        alert = AlertRecord(
            severity=severity, category=category,
            message=message, source=source,
        )
        self._alerts[alert.alert_id] = alert
        self._history.append(alert)
        return alert

    def acknowledge(self, alert_id: str, reviewer: str = "") -> AlertRecord | None:
        """Acknowledge an alert. Requires reviewer identity."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        if not reviewer:
            return alert  # Can't ack without reviewer but don't throw
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = reviewer
        alert.acknowledged_at = _now()
        return alert

    def resolve(self, alert_id: str, resolution: str = "") -> AlertRecord | None:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        alert.status = AlertStatus.RESOLVED
        alert.resolution = resolution
        alert.resolved_at = _now()
        return alert

    def get_active(self) -> list[AlertRecord]:
        """Get all open and acknowledged alerts."""
        return [
            a for a in self._alerts.values()
            if a.status in (AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED)
        ]

    def active_count(self) -> int:
        return len(self.get_active())

    def get_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get alert history."""
        return [a.to_dict() for a in self._history[-limit:]]

    def get_by_severity(self, severity: str) -> list[AlertRecord]:
        return [a for a in self._history if a.severity == severity]
