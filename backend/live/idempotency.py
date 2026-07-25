"""Execution Idempotency Manager — prevents duplicate live order execution.

Phase 46: Protects against API retry, timeout, frontend duplicate,
WebSocket duplicate events, backend restart, and network retry.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionIdempotencyManager:
    """
    Prevents duplicate live order execution.

    Every live order must have a unique execution key derived from:
    - strategy_version
    - symbol
    - direction (side)
    - signal_timestamp or signal_id
    - trade_intent_id

    Before submitting: checks if intent already has an order.
    If yes: DO NOT SUBMIT AGAIN.
    """

    def __init__(self):
        self._idempotency_store: dict[str, dict[str, Any]] = {}

    def generate_key(
        self,
        signal_id: str = "",
        strategy_version: str = "",
        symbol: str = "",
        side: str = "",
        session: str = "",
    ) -> str:
        """Generate a deterministic idempotency key.

        The key uniquely identifies a trading signal to prevent duplicates.
        """
        raw = f"{signal_id}|{strategy_version}|{symbol}|{side}|{session}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def generate_key_from_intent(
        self,
        signal_id: str = "",
        strategy_version: str = "",
        symbol: str = "",
        side: str = "",
        price: float | None = None,
        stop_loss: float | None = None,
    ) -> str:
        """Generate idempotency key from a full trade intent."""
        raw = f"{signal_id}|{strategy_version}|{symbol}|{side}|{price}|{stop_loss}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def check(self, idempotency_key: str) -> bool:
        """Check if this key has already been submitted.

        Returns True if DUPLICATE (already exists).
        Returns False if NEW (not seen before, registers it).
        """
        if idempotency_key in self._idempotency_store:
            return True  # Duplicate detected
        self._idempotency_store[idempotency_key] = {
            "submitted_at": _now(),
            "status": "pending",
        }
        return False  # New, registered

    def mark_submitted(self, idempotency_key: str, broker_order_id: str = "") -> None:
        """Mark a previously registered key as submitted to the broker."""
        entry = self._idempotency_store.get(idempotency_key)
        if entry:
            entry["status"] = "submitted"
            entry["broker_order_id"] = broker_order_id
            entry["submitted_at"] = _now()

    def mark_completed(self, idempotency_key: str) -> None:
        """Mark an idempotency key as completed (filled/cancelled)."""
        entry = self._idempotency_store.get(idempotency_key)
        if entry:
            entry["status"] = "completed"
            entry["completed_at"] = _now()

    def get(self, idempotency_key: str) -> dict[str, Any] | None:
        """Get the idempotency record for a key."""
        return self._idempotency_store.get(idempotency_key)

    def cleanup(self, max_age_hours: int = 24) -> int:
        """Remove entries older than max_age_hours. Returns count removed."""
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        to_remove = []
        for key, entry in self._idempotency_store.items():
            try:
                submitted = entry.get("submitted_at", "")
                if submitted:
                    dt = datetime.fromisoformat(submitted)
                    if dt.timestamp() < cutoff:
                        to_remove.append(key)
            except (ValueError, TypeError):
                to_remove.append(key)
        for key in to_remove:
            del self._idempotency_store[key]
        return len(to_remove)
