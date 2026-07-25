"""Operational Metrics — tracks uptime, incident metrics, and system health.

Phase 51: Monitoring-only. Never used to bypass safety gates.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OperationalMetrics:
    """Tracks operational metrics for observability.

    Metrics collected: uptime, heartbeat_success_rate, failures,
    broker_disconnect_count, market_data_stale_count, order_unknown_count,
    reconciliation_failure_count, incident_count, critical_incident_count,
    mean_time_to_acknowledge/resolve, kill_switch_count, rollback_count,
    recovery_count/failures, audit_failure_count.
    """

    def __init__(self):
        self._start_time = time.time()
        self._counts: dict[str, int] = defaultdict(int)
        self._ack_times: list[float] = []
        self._resolve_times: list[float] = []

    def record(self, event_type: str, metadata: dict | None = None) -> None:
        """Record an operational event for metrics."""
        self._counts["total_events"] += 1
        key = f"{event_type}_count"
        self._counts[key] += 1

        if metadata:
            if "ack_latency_seconds" in metadata:
                self._ack_times.append(metadata["ack_latency_seconds"])
            if "resolve_latency_seconds" in metadata:
                self._resolve_times.append(metadata["resolve_latency_seconds"])

    def get_metrics(self) -> dict[str, Any]:
        """Get all operational metrics."""
        uptime = time.time() - self._start_time
        total_beats = self._counts.get("heartbeat_beat_count", 0)
        failed_beats = self._counts.get("heartbeat_missed_count", 0)
        heartbeat_rate = (
            (total_beats - failed_beats) / total_beats * 100
            if total_beats > 0 else 100.0
        )

        mean_ack = (
            sum(self._ack_times) / len(self._ack_times)
            if self._ack_times else 0.0
        )
        mean_resolve = (
            sum(self._resolve_times) / len(self._resolve_times)
            if self._resolve_times else 0.0
        )

        return {
            "uptime_seconds": round(uptime, 1),
            "uptime_hours": round(uptime / 3600, 2),
            "heartbeat_success_rate": round(heartbeat_rate, 1),
            "heartbeat_failures": failed_beats,
            "broker_disconnect_count": self._counts.get("broker_disconnected_count", 0),
            "market_data_stale_count": self._counts.get("market_data_stale_count", 0),
            "order_unknown_count": self._counts.get("order_unknown_count", 0),
            "reconciliation_failure_count": self._counts.get("reconciliation_failed_count", 0),
            "incident_count": self._counts.get("incident_created_count", 0),
            "critical_incident_count": self._counts.get("critical_incident_count", 0),
            "mean_time_to_acknowledge_seconds": round(mean_ack, 1),
            "mean_time_to_resolve_seconds": round(mean_resolve, 1),
            "kill_switch_count": self._counts.get("kill_switch_triggered_count", 0),
            "rollback_count": self._counts.get("rollback_triggered_count", 0),
            "recovery_count": self._counts.get("recovery_completed_count", 0),
            "recovery_failure_count": self._counts.get("recovery_failed_count", 0),
            "audit_failure_count": self._counts.get("audit_write_failure_count", 0),
            "total_events": self._counts["total_events"],
        }

    def get_health_score(self) -> float:
        """Calculate a health score 0-100.

        Score is for observability only. Never used to bypass safety gates.
        """
        metrics = self.get_metrics()
        score = 100.0

        if metrics["critical_incident_count"] > 0:
            score -= 20 * min(metrics["critical_incident_count"], 3)
        if metrics["heartbeat_failures"] > 0:
            score -= min(metrics["heartbeat_failures"], 10)
        if metrics["recovery_failure_count"] > 0:
            score -= 15
        if metrics["audit_failure_count"] > 0:
            score -= 10

        return max(0, round(score, 1))
