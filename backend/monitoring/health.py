"""
Health check endpoints and monitoring utilities.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    status: str = "healthy"  # healthy, degraded, unhealthy
    uptime_seconds: float = 0.0
    version: str = "1.0.0"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    checks: dict[str, bool] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """Performs health checks on all system components."""

    def __init__(self, start_time: Optional[datetime] = None):
        self.start_time = start_time or datetime.now(timezone.utc)
        self._checks: dict[str, callable] = {}

    def register_check(self, name: str, check_fn: callable):
        self._checks[name] = check_fn

    async def check_all(self) -> HealthStatus:
        results: dict[str, bool] = {}
        details: dict[str, Any] = {}

        for name, fn in self._checks.items():
            try:
                result = await fn()
                results[name] = result is True
                details[name] = "ok" if result is True else str(result)
            except Exception as e:
                results[name] = False
                details[name] = str(e)

        all_healthy = all(results.values())
        any_healthy = any(results.values())

        return HealthStatus(
            status="healthy" if all_healthy else "degraded" if any_healthy else "unhealthy",
            uptime_seconds=(datetime.now(timezone.utc) - self.start_time).total_seconds(),
            checks=results,
            details=details,
        )


# Prometheus metrics placeholder
class MetricsCollector:
    """Collects and exposes Prometheus metrics."""

    def __init__(self):
        self._metrics: dict[str, float] = {}

    def increment(self, name: str, value: float = 1.0):
        self._metrics[name] = self._metrics.get(name, 0) + value

    def gauge(self, name: str, value: float):
        self._metrics[name] = value

    def observe(self, name: str, value: float):
        if name not in self._metrics:
            self._metrics[name] = value
        else:
            # Simple moving average for observation metrics
            self._metrics[name] = (self._metrics[name] + value) / 2

    def snapshot(self) -> dict[str, float]:
        return dict(self._metrics)

    def reset(self):
        self._metrics.clear()
