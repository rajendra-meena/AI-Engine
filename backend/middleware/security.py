"""
Security middleware — rate limiting, audit logging, input validation.
"""

from __future__ import annotations

import time
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding window rate limiter."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > window_start]

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.time()
        window_start = now - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        return max(0, self.max_requests - len(self._requests[key]))

    def reset(self, key: Optional[str] = None):
        if key:
            self._requests[key].clear()
        else:
            self._requests.clear()


class AuditLogger:
    """Structured audit logging for security events."""

    def __init__(self):
        self._logs: list[dict[str, Any]] = []

    def log(
        self,
        action: str,
        resource: str,
        user_id: Optional[str] = None,
        detail: Optional[dict] = None,
        ip: Optional[str] = None,
    ):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "resource": resource,
            "user_id": user_id,
            "detail": detail or {},
            "ip": ip,
        }
        self._logs.append(entry)
        logger.info(f"Audit: {action} on {resource} by {user_id}")
        return entry

    def get_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(self._logs[-limit:])

    def get_user_logs(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        return [l for l in self._logs if l["user_id"] == user_id][-limit:]


class InputValidator:
    """Input validation utilities."""

    @staticmethod
    def is_valid_symbol(symbol: str) -> bool:
        if not symbol or len(symbol) > 20:
            return False
        return all(c.isalnum() or c in " -_." for c in symbol)

    @staticmethod
    def is_valid_quantity(qty: int) -> bool:
        return isinstance(qty, int) and qty > 0 and qty <= 100000

    @staticmethod
    def is_valid_price(price: float) -> bool:
        return isinstance(price, (int, float)) and price > 0

    @staticmethod
    def is_valid_email(email: str) -> bool:
        import re

        return bool(
            re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email)
        )

    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        import re

        sanitized = re.sub(r"[<>\";]|script|alert", "", value)
        return sanitized[:max_length]
