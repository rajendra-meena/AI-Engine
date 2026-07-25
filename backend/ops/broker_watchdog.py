"""Broker Watchdog — monitors broker connectivity, session, and API health.

Phase 50: On disconnect → BLOCK NEW ENTRIES. Never auto-retry unknown orders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BrokerHealth:
    """Current broker health status."""
    state: str = "unknown"
    authenticated: bool = False
    session_valid: bool = False
    api_reachable: bool = False
    api_latency_ms: float = 0.0
    last_success: str = ""
    failure_count: int = 0
    consecutive_failures: int = 0
    rate_limited: bool = False
    order_acknowledgement_ok: bool = True
    positions_available: bool = False
    funds_available: bool = False
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "authenticated": self.authenticated,
            "session_valid": self.session_valid,
            "api_reachable": self.api_reachable,
            "api_latency_ms": round(self.api_latency_ms, 1),
            "last_success": self.last_success,
            "failure_count": self.failure_count,
            "consecutive_failures": self.consecutive_failures,
            "rate_limited": self.rate_limited,
            "order_acknowledgement_ok": self.order_acknowledgement_ok,
            "positions_available": self.positions_available,
            "funds_available": self.funds_available,
            "timestamp": self.timestamp,
        }


class BrokerWatchdog:
    """
    Monitors broker connectivity and health.

    On disconnect: BLOCK NEW ENTRIES immediately.
    Do NOT automatically place replacement orders.
    Do NOT assume order failed — QUERY BROKER ORDER STATUS first.
    """

    def __init__(self):
        self._health = BrokerHealth()
        self._alert_mgr = None
        self._audit_log = None
        self._broker = None

    def set_alert_manager(self, am): self._alert_mgr = am
    def set_audit_log(self, a): self._audit_log = a
    def set_broker(self, b): self._broker = b

    def check_health(self) -> BrokerHealth:
        """Check broker health by querying the adapter."""
        h = self._health

        if not self._broker:
            h.state = "not_configured"
            return h

        try:
            import asyncio
            health = asyncio.run(self._broker.health_check())
            status = health.get("status", "unknown")
            h.api_reachable = status == "healthy"
            h.api_latency_ms = health.get("latency_ms", 0)
            if status == "healthy":
                h.authenticated = True
                h.session_valid = True
                h.state = "healthy"
                h.last_success = _now()
                h.consecutive_failures = 0
            else:
                h.consecutive_failures += 1
                h.failure_count += 1
                h.state = "degraded" if h.consecutive_failures < 3 else "disconnected"
        except Exception as e:
            h.consecutive_failures += 1
            h.failure_count += 1
            h.state = "disconnected" if h.consecutive_failures >= 2 else "degraded"
            h.last_error = str(e)[:100]
            self._record_audit("broker_disconnected", severity="critical")

        return h

    def is_trading_blocked(self) -> bool:
        """True if broker state blocks new entries."""
        h = self.check_health()
        return h.state in ("disconnected", "not_configured")

    def get_health(self) -> BrokerHealth:
        return self.check_health()

    def _record_audit(self, event_type: str, severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="broker_watchdog",
            details={"component": "broker_watchdog"},
        )
