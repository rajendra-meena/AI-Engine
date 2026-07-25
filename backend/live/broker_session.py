"""Broker Session Manager — validates broker authentication, session, account, and segments.

Phase 46: Read-only session validation. Never exposes API secrets.
Any invalid state blocks execution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


SENSITIVE_FIELDS = [
    "access_token", "api_secret", "api_key", "client_secret",
    "password", "secret", "token", "session_token", "auth_token",
]


def _sanitize(data: dict) -> dict:
    """Remove sensitive fields from responses and logs."""
    if not isinstance(data, dict):
        return data
    return {k: ("***" if any(s in k.lower() for s in SENSITIVE_FIELDS) else v)
            for k, v in data.items()}


@dataclass
class BrokerSessionStatus:
    """Current broker session validation status."""
    authenticated: bool = False
    session_valid: bool = False
    account_valid: bool = False
    segments_valid: bool = False
    exchange_available: bool = False
    checked_at: str = field(default_factory=_now)
    expires_at: str = ""
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def all_valid(self) -> bool:
        return all([
            self.authenticated, self.session_valid, self.account_valid,
            self.segments_valid, self.exchange_available,
        ])

    def to_dict(self) -> dict[str, Any]:
        return {
            "authenticated": self.authenticated,
            "session_valid": self.session_valid,
            "account_valid": self.account_valid,
            "segments_valid": self.segments_valid,
            "exchange_available": self.exchange_available,
            "all_valid": self.all_valid,
            "checked_at": self.checked_at,
            "expires_at": self.expires_at,
            "error": self.error,
            "details": _sanitize(self.details),
        }


class BrokerSessionManager:
    """
    Manages broker authentication session validation.

    All operations are read-only. Never exposes API secrets.
    Invalid session = BLOCK EXECUTION.
    """

    def __init__(self, broker=None):
        self._broker = broker
        self._last_status: BrokerSessionStatus | None = None
        self._audit_log = None

    def set_broker(self, broker):
        """Set the broker adapter instance."""
        self._broker = broker

    def set_audit_log(self, audit_log):
        self._audit_log = audit_log

    def get_last_status(self) -> BrokerSessionStatus | None:
        return self._last_status

    async def validate_session(self) -> BrokerSessionStatus:
        """Check broker authentication and session validity.

        Returns:
            BrokerSessionStatus with all fields populated.
        """
        status = BrokerSessionStatus()
        if not self._broker:
            status.error = "Broker adapter not configured"
            self._last_status = status
            self._record_audit("live_session_invalid", details={"error": status.error})
            return status

        try:
            import asyncio
            # Health check proves auth + connectivity
            health = await self._broker.health_check()
            health_status = health.get("status", "unknown")
            status.authenticated = health_status == "healthy"
            status.session_valid = health_status == "healthy"

            # Try to get account info
            account = await self._broker.get_account()
            account_status = account.get("status", "unknown")
            status.account_valid = account_status in ("active", "healthy", "simulated")

            # Try to get balance (proves funds access)
            balance = await self._broker.get_balance()
            if isinstance(balance, dict) and "available" in balance:
                status.exchange_available = True
                status.details["balance_available"] = balance.get("available", 0)

            if health_status == "healthy":
                from datetime import timedelta
                status.expires_at = (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat()

            if not status.all_valid:
                status.error = (
                    f"Session partially valid: auth={status.authenticated}, "
                    f"session={status.session_valid}, account={status.account_valid}"
                )

            status.segments_valid = status.account_valid
            status.checked_at = _now()
            self._last_status = status
            self._record_audit(
                "live_session_validated" if status.all_valid else "live_session_invalid",
                details={"all_valid": status.all_valid},
                severity="info" if status.all_valid else "warning",
            )
            return status

        except Exception as e:
            status.error = f"Session validation failed: {e}"
            self._last_status = status
            self._record_audit(
                "live_session_invalid", severity="error",
                details={"error": str(e)},
            )
            return status

    async def get_account_status(self) -> dict[str, Any]:
        """Get account information (sanitized)."""
        if not self._broker:
            return {"status": "unknown", "error": "Broker not configured"}
        try:
            account = await self._broker.get_account()
            return _sanitize(account)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_exchange_status(self) -> dict[str, Any]:
        """Check if exchanges are available."""
        if not self._broker:
            return {"nse": False, "bse": False, "error": "Broker not configured"}
        try:
            health = await self._broker.health_check()
            healthy = health.get("status") == "healthy"
            return {"nse": healthy, "bse": False, "available": healthy}
        except Exception as e:
            return {"nse": False, "bse": False, "error": str(e)}

    async def get_status(self) -> dict[str, Any]:
        """Full session status for API responses."""
        if not self._last_status:
            status = await self.validate_session()
        else:
            status = self._last_status
        return {
            "session": status.to_dict(),
            "account": await self.get_account_status(),
            "exchange": await self.get_exchange_status(),
            "broker_configured": self._broker is not None,
        }

    def _record_audit(self, event_type: str, details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="broker_session_manager",
            details={"component": "broker_session", **(details or {})},
        )
