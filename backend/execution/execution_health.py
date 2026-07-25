"""Execution Health Monitor — monitors broker connectivity, API latency, and system health."""

from __future__ import annotations
from typing import Any

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


def _new_id() -> str:
    return f"hlth_{uuid.uuid4().hex[:8]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    name: str = ""
    state: HealthState = HealthState.UNKNOWN
    latency_ms: float = 0.0
    last_success: str = ""
    last_failure: str = ""
    consecutive_failures: int = 0
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "latency_ms": self.latency_ms,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "consecutive_failures": self.consecutive_failures,
            "details": self.details,
        }


class ExecutionHealthMonitor:
    """
    Monitors all execution-related health signals.
    Any CRITICAL failure must block new orders.
    """

    def __init__(self):
        self._checks: dict[str, HealthCheckResult] = {}
        self._overall_state = HealthState.UNKNOWN

        # Initialize all checks
        for name in [
            "broker_connectivity",
            "websocket_health",
            "api_latency",
            "order_acknowledgement_latency",
            "fill_latency",
            "rejection_rate",
            "reconciliation_status",
            "market_data_freshness",
            "system_heartbeat",
            "kill_switch_status",
        ]:
            self._checks[name] = HealthCheckResult(name=name, state=HealthState.UNKNOWN)

    def record_success(self, check_name: str, latency_ms: float = 0.0, details: str = ""):
        """Record a successful health check."""
        check = self._checks.get(check_name)
        if check:
            check.state = HealthState.HEALTHY
            check.latency_ms = latency_ms
            check.last_success = _now()
            check.consecutive_failures = 0
            check.details = details
        self._recompute_overall()

    def record_failure(self, check_name: str, details: str = ""):
        """Record a failed health check."""
        check = self._checks.get(check_name)
        if check:
            check.consecutive_failures += 1
            check.state = HealthState.BLOCKED if check.consecutive_failures >= 2 else HealthState.DEGRADED
            check.last_failure = _now()
            check.details = details
        self._recompute_overall()

    def record_degraded(self, check_name: str, details: str = ""):
        """Record a degraded health check (non-critical)."""
        check = self._checks.get(check_name)
        if check:
            check.state = HealthState.DEGRADED
            check.details = details
        self._recompute_overall()

    def is_healthy(self) -> bool:
        """True only if all checks are healthy."""
        return all(c.state == HealthState.HEALTHY for c in self._checks.values())

    def is_blocked(self) -> bool:
        """True if any check is in BLOCKED state."""
        return any(c.state == HealthState.BLOCKED for c in self._checks.values())

    def get_overall_state(self) -> HealthState:
        return self._overall_state

    def get_check(self, name: str) -> HealthCheckResult | None:
        return self._checks.get(name)

    def get_all_checks(self) -> dict[str, dict[str, Any]]:
        return {name: check.to_dict() for name, check in self._checks.items()}

    def get_status(self) -> dict[str, Any]:
        return {
            "overall": self._overall_state.value,
            "healthy": self.is_healthy(),
            "blocked": self.is_blocked(),
            "checks": self.get_all_checks(),
        }

    def _recompute_overall(self):
        states = [c.state for c in self._checks.values()]
        if HealthState.BLOCKED in states:
            self._overall_state = HealthState.BLOCKED
        elif HealthState.DEGRADED in states:
            self._overall_state = HealthState.DEGRADED
        elif all(s == HealthState.HEALTHY for s in states):
            self._overall_state = HealthState.HEALTHY
        else:
            self._overall_state = HealthState.UNKNOWN
