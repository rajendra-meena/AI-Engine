"""
Institutional Risk Firewall — Trade Validator

Validates a single trade against all pre-trade checks before execution.
Each check returns a ValidationResult with status, severity, and reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    BLOCK = "block"


@dataclass
class ValidationResult:
    check: str
    status: ValidationStatus
    severity: Severity = Severity.LOW
    reason: str = ""
    recommendation: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "status": self.status.value,
            "severity": self.severity.value,
            "reason": self.reason,
            "recommendation": self.recommendation,
            "detail": self.detail,
        }


@dataclass
class ValidationSummary:
    passed: bool
    results: list[ValidationResult]
    risk_score: float = 0.0
    risk_grade: str = "LOW"
    execution_permitted: bool = False
    rejected_by: list[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "results": [r.to_dict() for r in self.results],
            "risk_score": self.risk_score,
            "risk_grade": self.risk_grade,
            "execution_permitted": self.execution_permitted,
            "rejected_by": self.rejected_by,
            "timestamp": self.timestamp,
        }


@dataclass
class TradeIntent:
    """Normalised trade request that the Risk Firewall evaluates."""
    symbol: str
    side: str
    quantity: int
    price: float | None
    order_type: str
    product: str
    exchange: str
    strategy: str = "manual"
    ai_score: float | None = None
    ai_confidence: float | None = None
    ai_decision: str | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    user_id: str = ""
    tag: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
