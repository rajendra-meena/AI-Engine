"""Heartbeat Service — per-component health tracking.

Phase 50: Tracks application, market data, broker, execution, reconciliation heartbeats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


@dataclass
class HeartbeatRecord:
    """A single heartbeat record for a component."""
    component: str = ""
    status: str = "unknown"
    timestamp: str = field(default_factory=_now)
    latency_ms: float = 0.0
    last_success: str = ""
    failure_count: int = 0
    consecutive_failures: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status,
            "timestamp": self.timestamp,
            "latency_ms": round(self.latency_ms, 1),
            "last_success": self.last_success,
            "failure_count": self.failure_count,
            "consecutive_failures": self.consecutive_failures,
        }


COMPONENTS = ["application", "market_data", "broker", "execution", "reconciliation"]


class HeartbeatService:
    """Tracks per-component heartbeats for health monitoring."""

    def __init__(self, timeout_seconds: int = 30):
        self._timeout = timeout_seconds
        self._records: dict[str, HeartbeatRecord] = {}
        for comp in COMPONENTS:
            self._records[comp] = HeartbeatRecord(component=comp)

    def beat(self, component: str, status: str = "healthy",
             latency_ms: float = 0.0) -> HeartbeatRecord:
        """Record a heartbeat for a component."""
        record = self._records.get(component)
        if not record:
            record = HeartbeatRecord(component=component)
            self._records[component] = record
        record.timestamp = _now()
        record.status = status
        record.latency_ms = latency_ms
        if status == "healthy":
            record.last_success = _now()
            record.consecutive_failures = 0
        else:
            record.consecutive_failures += 1
            record.failure_count += 1
        return record

    def check_missed(self, timeout_seconds: int | None = None) -> list[str]:
        """Return list of components that missed their heartbeat."""
        timeout = timeout_seconds or self._timeout
        now = _now_ts()
        missed: list[str] = []
        for comp, record in self._records.items():
            try:
                ts = datetime.fromisoformat(record.timestamp).timestamp()
                if (now - ts) > timeout:
                    missed.append(comp)
            except (ValueError, TypeError):
                missed.append(comp)
        return missed

    def get_record(self, component: str) -> HeartbeatRecord | None:
        return self._records.get(component)

    def get_statuses(self) -> dict[str, Any]:
        return {comp: rec.to_dict() for comp, rec in self._records.items()}

    def get_summary(self) -> dict[str, Any]:
        missed = self.check_missed()
        return {
            "components": self.get_statuses(),
            "missed_heartbeats": missed,
            "all_healthy": len(missed) == 0,
            "timeout_seconds": self._timeout,
        }
