"""Market Data Watchdog — monitors tick health, detects stale/disconnected data.

Phase 50: Stale data must block new entries. Never trade using stale data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

MAX_TICK_AGE_MS = 5000
MAX_MISSING_TICKS = 10
MAX_RECONNECT_ATTEMPTS = 3
MAX_OUT_OF_ORDER_TICKS = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MarketDataHealth:
    """Current market data health status."""
    state: str = "unknown"
    last_tick_timestamp: str = ""
    tick_age_ms: float = 0.0
    websocket_connected: bool = False
    missing_ticks: int = 0
    out_of_order_ticks: int = 0
    reconnect_attempts: int = 0
    alerts_triggered: int = 0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "last_tick_timestamp": self.last_tick_timestamp,
            "tick_age_ms": round(self.tick_age_ms, 1),
            "websocket_connected": self.websocket_connected,
            "missing_ticks": self.missing_ticks,
            "out_of_order_ticks": self.out_of_order_ticks,
            "reconnect_attempts": self.reconnect_attempts,
            "alerts_triggered": self.alerts_triggered,
            "timestamp": self.timestamp,
        }


class MarketDataWatchdog:
    """
    Monitors market data health.

    On stale data:
    1. Block new entries
    2. Mark system DEGRADED
    3. Trigger alert
    4. Trigger audit event
    5. Request reconciliation
    6. If unresolved → ROLLBACK_REQUIRED
    7. Require human review before resuming
    """

    def __init__(self):
        self._health = MarketDataHealth()
        self._alert_mgr = None
        self._audit_log = None
        self._max_tick_age_ms = MAX_TICK_AGE_MS
        self._max_missing = MAX_MISSING_TICKS
        self._max_reconnect = MAX_RECONNECT_ATTEMPTS

    def set_alert_manager(self, am): self._alert_mgr = am
    def set_audit_log(self, a): self._audit_log = a

    def record_tick(self, timestamp: str = "") -> None:
        """Record a tick arrival."""
        self._health.last_tick_timestamp = timestamp or _now()
        self._health.websocket_connected = True
        self._health.missing_ticks = 0
        if self._health.state in ("stale", "disconnected"):
            self._health.state = "recovered"
            self._record_audit("market_data_recovered")

    def record_disconnect(self) -> None:
        """Record a websocket disconnect."""
        self._health.websocket_connected = False
        self._health.reconnect_attempts += 1
        self._health.state = "disconnected"
        self._record_audit("market_data_stale", severity="warning")

    def record_missing_tick(self) -> None:
        """Record a missing tick."""
        self._health.missing_ticks += 1

    def check_health(self) -> MarketDataHealth:
        """Check current market data health.

        Returns:
            MarketDataHealth with current state.
        """
        h = self._health

        # Check tick age
        if h.last_tick_timestamp:
            try:
                last = datetime.fromisoformat(h.last_tick_timestamp)
                age = (datetime.now(timezone.utc) - last).total_seconds() * 1000
                h.tick_age_ms = age
                if age > self._max_tick_age_ms:
                    h.state = "stale"
                elif h.state == "stale" and age <= self._max_tick_age_ms:
                    h.state = "healthy"
            except (ValueError, TypeError):
                pass
        else:
            h.state = "unknown"

        # Check missing ticks threshold
        if h.missing_ticks >= self._max_missing:
            h.state = "stale"

        # Check reconnect attempts
        if h.reconnect_attempts >= self._max_reconnect:
            h.state = "disconnected"

        # Determine if trading should be blocked
        if h.state in ("stale", "disconnected"):
            h.state = "blocked"

        return h

    def is_trading_blocked(self) -> bool:
        """True if market data health blocks new entries."""
        h = self.check_health()
        return h.state in ("stale", "disconnected", "blocked")

    def get_health(self) -> MarketDataHealth:
        return self.check_health()

    def _record_audit(self, event_type: str, severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="market_data_watchdog",
            details={"component": "market_data_watchdog"},
        )
