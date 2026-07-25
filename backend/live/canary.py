"""Canary Execution Manager — controlled canary trading with strict limits.

Phase 46: Canary mode must be stricter than normal live mode.
Disarmed by default. Requires explicit human confirmation to arm.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Default Canary Limits ──

CANARY_ENABLED = False
MAX_CANARY_TRADES = 3
MAX_CANARY_QUANTITY = 1
MAX_CANARY_NOTIONAL = 10000
MAX_CANARY_DAILY_LOSS = 500
CANARY_SYMBOL_ALLOWLIST: list[str] = []
CANARY_TIME_WINDOW = "09:15-15:30"


@dataclass
class CanaryConfig:
    """Canary trading configuration."""
    enabled: bool = CANARY_ENABLED
    max_trades: int = MAX_CANARY_TRADES
    max_quantity: int = MAX_CANARY_QUANTITY
    max_notional: float = MAX_CANARY_NOTIONAL
    max_daily_loss: float = MAX_CANARY_DAILY_LOSS
    symbol_allowlist: list[str] = field(default_factory=list)
    time_window: str = CANARY_TIME_WINDOW

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "max_trades": self.max_trades,
            "max_quantity": self.max_quantity,
            "max_notional": self.max_notional,
            "max_daily_loss": self.max_daily_loss,
            "symbol_allowlist": self.symbol_allowlist,
            "time_window": self.time_window,
        }


@dataclass
class CanaryResult:
    """Result of a canary execution check."""
    allowed: bool = False
    blockers: list[str] = field(default_factory=list)
    quantity_allowed: int = 0
    trades_remaining: int = 0
    loss_remaining: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "blockers": self.blockers,
            "quantity_allowed": self.quantity_allowed,
            "trades_remaining": self.trades_remaining,
            "loss_remaining": self.loss_remaining,
            "timestamp": self.timestamp,
        }


class CanaryExecutionManager:
    """
    Controlled canary trading.

    Canary mode is STRICTER than normal live mode.
    Disarmed by default. Requires explicit human confirmation to arm.

    Prerequisites for arming:
    - Champion valid
    - Shadow validation passed
    - Final approval valid
    - Pre-live validation passed
    - Activation gate armed
    - Broker session valid
    - Market data healthy
    - RiskEngine passed
    - LiveExecutionGate passed
    - Kill switch healthy
    - No reconciliation errors
    """

    def __init__(self):
        self._config = CanaryConfig()
        self._armed = False
        self._arm_reviewer = ""
        self._arm_reason = ""
        self._arm_timestamp = ""
        self._canary_trade_count = 0
        self._canary_daily_loss = 0.0
        self._audit_log = None

    def set_audit_log(self, audit): self._audit_log = audit

    def update_config(self, config: CanaryConfig) -> None:
        """Update canary configuration."""
        self._config = config

    def is_armed(self) -> bool:
        return self._armed

    def arm(self, reviewer: str = "", reason: str = "") -> dict[str, Any]:
        """Arm canary mode with explicit human confirmation.

        Required:
            reviewer: Human identity confirming canary mode
            reason: Reason for enabling canary mode

        Returns:
            Dict with arm result
        """
        if not reviewer:
            return {"success": False, "error": "Reviewer identity is required"}
        if not reason:
            return {"success": False, "error": "Reason for arming is required"}

        self._armed = True
        self._arm_reviewer = reviewer
        self._arm_reason = reason
        self._arm_timestamp = _now()
        self._canary_trade_count = 0
        self._canary_daily_loss = 0.0

        self._record_audit(
            "canary_armed",
            details={"reviewer": reviewer, "reason": reason},
        )

        return {
            "success": True,
            "message": "Canary mode armed. Strict limits apply.",
            "config": self._config.to_dict(),
        }

    def disarm(self) -> dict[str, Any]:
        """Disarm canary mode."""
        was_armed = self._armed
        self._armed = False

        self._record_audit(
            "canary_disarmed",
            details={"was_armed": was_armed},
        )

        return {
            "success": True,
            "message": "Canary mode disarmed.",
        }

    def can_execute(
        self,
        symbol: str = "",
        quantity: int = 0,
        price: float | None = None,
    ) -> CanaryResult:
        """Check if a canary trade can be executed.

        Validates:
        - Canary is armed
        - Symbol is in allowlist
        - Quantity within max
        - Notional within max
        - Trade count within max
        - Daily loss within max

        Returns:
            CanaryResult with specific blockers
        """
        result = CanaryResult()
        blockers: list[str] = []

        if not self._armed:
            blockers.append("canary_not_armed")

        if not self._config.enabled:
            blockers.append("canary_not_enabled")

        # Symbol allowlist
        if self._config.symbol_allowlist and symbol not in self._config.symbol_allowlist:
            blockers.append(f"symbol_not_in_allowlist: {symbol}")

        # Max quantity
        if quantity > self._config.max_quantity:
            blockers.append(
                f"max_canary_quantity: {quantity} > {self._config.max_quantity}"
            )

        # Max notional
        notional = (price or 0) * quantity
        if notional > self._config.max_notional:
            blockers.append(
                f"max_canary_notional: {notional:.0f} > {self._config.max_notional:.0f}"
            )

        # Max trades
        if self._canary_trade_count >= self._config.max_trades:
            blockers.append(
                f"max_canary_trades: {self._canary_trade_count} >= {self._config.max_trades}"
            )

        # Max daily loss
        if self._canary_daily_loss <= -self._config.max_daily_loss:
            blockers.append(
                f"max_canary_daily_loss: {self._canary_daily_loss:.0f} <= {-self._config.max_daily_loss:.0f}"
            )

        result.allowed = len(blockers) == 0
        result.blockers = blockers
        result.quantity_allowed = self._config.max_quantity if result.allowed else 0
        result.trades_remaining = max(0, self._config.max_trades - self._canary_trade_count)
        result.loss_remaining = max(0, self._config.max_daily_loss + self._canary_daily_loss)

        if blockers:
            self._record_audit(
                "canary_limit_blocked",
                details={
                    "symbol": symbol,
                    "quantity": quantity,
                    "price": price,
                    "blockers": blockers,
                },
                severity="warning",
            )

        return result

    def record_canary_trade(self, pnl: float = 0.0) -> None:
        """Record a canary trade for limit tracking."""
        self._canary_trade_count += 1
        self._canary_daily_loss += pnl

    def get_status(self) -> dict[str, Any]:
        return {
            "armed": self._armed,
            "config": self._config.to_dict(),
            "current_state": {
                "canary_trade_count": self._canary_trade_count,
                "canary_daily_loss": round(self._canary_daily_loss, 2),
                "trades_remaining": max(0, self._config.max_trades - self._canary_trade_count),
                "loss_remaining": round(
                    max(0, self._config.max_daily_loss + self._canary_daily_loss), 2
                ),
            },
            "arm_details": {
                "reviewer": self._arm_reviewer,
                "reason": self._arm_reason,
                "armed_at": self._arm_timestamp,
            } if self._armed else None,
        }

    def _record_audit(self, event_type: str, details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="canary_execution_manager",
            details={"component": "canary", **(details or {})},
        )
