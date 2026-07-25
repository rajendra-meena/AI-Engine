"""Pre-Live Validation data models for Phase 44 operational validation."""

from __future__ import annotations
from typing import Any

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _new_id(prefix: str = "plv") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CheckStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_TESTED = "not_tested"
    SKIPPED = "skipped"


class CheckSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationClassification(str, Enum):
    EXCELLENT = "excellent"
    READY = "ready_for_live_activation"
    CONDITIONAL = "conditional_review"
    NOT_READY = "not_ready"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class PreLiveCheck:
    """A single pre-live validation check."""
    check_id: str = field(default_factory=lambda: _new_id("chk"))
    category: str = ""
    name: str = ""
    status: CheckStatus = CheckStatus.NOT_TESTED
    severity: CheckSeverity = CheckSeverity.INFO
    passed: bool = False
    blocking: bool = False
    message: str = ""
    details: str = ""
    timestamp: str = field(default_factory=_now)
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "category": self.category,
            "name": self.name,
            "status": self.status.value,
            "severity": self.severity.value,
            "passed": self.passed,
            "blocking": self.blocking,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "duration_ms": round(self.duration_ms, 1),
        }


@dataclass
class PreLiveValidationReport:
    """Complete pre-live validation report."""
    validation_id: str = field(default_factory=lambda: _new_id("plv"))
    started_at: str = field(default_factory=_now)
    completed_at: str = ""
    duration_ms: float = 0.0
    score: float = 0.0
    classification: ValidationClassification = ValidationClassification.NOT_READY
    overall_status: str = "not_tested"
    checks: list[PreLiveCheck] = field(default_factory=list)
    hard_blocks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    critical_issues: list[str] = field(default_factory=list)

    broker_status: str = "unknown"
    market_data_status: str = "unknown"
    champion_id: str = ""
    approval_id: str = ""
    config_hash: str = ""
    runtime_mode: str = "observe"
    live_execution_enabled: bool = False
    can_execute_live: bool = False
    generated_at: str = field(default_factory=_now)

    def add_check(self, check: PreLiveCheck):
        self.checks.append(check)

    def to_dict(self) -> dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": round(self.duration_ms, 1),
            "score": round(self.score, 1),
            "classification": self.classification.value,
            "overall_status": self.overall_status,
            "checks": [c.to_dict() for c in self.checks],
            "hard_blocks": self.hard_blocks,
            "warnings": self.warnings,
            "critical_issues": self.critical_issues,
            "broker_status": self.broker_status,
            "market_data_status": self.market_data_status,
            "champion_id": self.champion_id,
            "approval_id": self.approval_id,
            "config_hash": self.config_hash,
            "runtime_mode": self.runtime_mode,
            "live_execution_enabled": self.live_execution_enabled,
            "can_execute_live": self.can_execute_live,
            "generated_at": self.generated_at,
        }

    def summary(self) -> dict[str, Any]:
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c.status == CheckStatus.PASS)
        warnings_count = sum(1 for c in self.checks if c.status == CheckStatus.WARNING)
        failed = sum(1 for c in self.checks if c.status == CheckStatus.FAIL)
        blocked = sum(1 for c in self.checks if c.status == CheckStatus.BLOCKED)
        return {
            "validation_id": self.validation_id,
            "classification": self.classification.value,
            "overall_status": self.overall_status,
            "score": round(self.score, 1),
            "total_checks": total,
            "passed": passed,
            "warnings": warnings_count,
            "failed": failed,
            "blocked": blocked,
            "hard_blocks": len(self.hard_blocks),
        }
