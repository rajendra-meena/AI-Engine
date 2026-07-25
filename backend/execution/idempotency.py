"""Idempotency and duplicate order protection."""

from __future__ import annotations
from typing import Any

import hashlib
from datetime import datetime, timezone


class IdempotencyGuard:
    """Prevents duplicate order creation from repeated signals/requests."""

    def __init__(self):
        self._keys: dict[str, dict[str, Any]] = {}

    def generate_key(self, signal_id: str, strategy_version: str, symbol: str, side: str, session: str = "") -> str:
        raw = f"{signal_id}|{strategy_version}|{symbol}|{side}|{session}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def check(self, idempotency_key: str) -> bool:
        """Returns True if key already exists (duplicate)."""
        if idempotency_key in self._keys:
            return True
        self._keys[idempotency_key] = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }
        return False

    def mark_completed(self, idempotency_key: str):
        entry = self._keys.get(idempotency_key)
        if entry:
            entry["status"] = "completed"

    def get(self, idempotency_key: str) -> dict[str, Any] | None:
        return self._keys.get(idempotency_key)

    def cleanup(self, max_age_hours: int = 24):
        now = datetime.now(timezone.utc)
        self._keys = {
            k: v for k, v in self._keys.items()
            if (now - datetime.fromisoformat(v["created_at"])).total_seconds() < max_age_hours * 3600
        }
