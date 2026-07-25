"""Live Readiness data models."""

from __future__ import annotations

from dataclasses import dataclass, field

from typing import Any


@dataclass
class ReadinessCheck:
    name: str = ""
    status: str = "pending"  # pass, warning, fail, blocked
    severity: str = "info"
    details: str = ""
    category: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "severity": self.severity,
            "details": self.details,
            "category": self.category,
        }


@dataclass
class LiveReadinessReport:
    id: str = ""
    timestamp: str = ""
    status: str = "pending"
    score: float = 0.0
    classification: str = "not_ready"
    champion_id: str = ""
    champion_version: str = ""
    champion_hash: str = ""
    shadow_score: float = 0.0
    shadow_classification: str = ""
    shadow_trade_count: int = 0
    hard_blocks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    checks: list[ReadinessCheck] = field(default_factory=list)
    configuration_snapshot: dict[str, Any] = field(default_factory=dict)
    review_required: bool = False
    live_execution_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "status": self.status,
            "score": round(self.score, 1),
            "classification": self.classification,
            "champion_id": self.champion_id,
            "champion_version": self.champion_version,
            "champion_hash": self.champion_hash,
            "shadow_score": self.shadow_score,
            "shadow_classification": self.shadow_classification,
            "shadow_trade_count": self.shadow_trade_count,
            "hard_blocks": self.hard_blocks,
            "warnings": self.warnings,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "checks": [c.to_dict() for c in self.checks],
            "configuration_snapshot": self.configuration_snapshot,
            "review_required": self.review_required,
            "live_execution_enabled": self.live_execution_enabled,
        }
