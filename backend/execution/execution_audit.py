"""Append-only execution audit log."""

from __future__ import annotations
from typing import Any

import uuid
from datetime import datetime, timezone


def _new_id() -> str:
    return f"aud_{uuid.uuid4().hex[:10]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionAuditLog:
    """Append-only audit trail for all execution events."""

    def __init__(self):
        self._entries: list[dict[str, Any]] = []

    def record(
        self,
        event_type: str,
        severity: str = "info",
        order_id: str = "",
        signal_id: str = "",
        champion_id: str = "",
        approval_id: str = "",
        correlation_id: str = "",
        actor: str = "system",
        reason: str = "",
        before_state: str = "",
        after_state: str = "",
        details: dict | None = None,
    ) -> str:
        eid = _new_id()
        entry = {
            "event_id": eid,
            "timestamp": _now(),
            "event_type": event_type,
            "severity": severity,
            "order_id": order_id,
            "signal_id": signal_id,
            "champion_id": champion_id,
            "approval_id": approval_id,
            "correlation_id": correlation_id,
            "actor": actor,
            "reason": reason,
            "before_state": before_state,
            "after_state": after_state,
            "details": details or {},
        }
        self._entries.append(entry)
        return eid

    def get_entries(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(self._entries[-limit:])

    def count(self) -> int:
        return len(self._entries)
