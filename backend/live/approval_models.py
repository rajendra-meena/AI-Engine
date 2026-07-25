"""Final Live Approval data models."""

from __future__ import annotations

from dataclasses import dataclass, field

from typing import Any


@dataclass
class ApprovalGate:
    name: str = ""
    status: str = "pending"
    details: str = ""
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "details": self.details,
            "score": self.score,
        }


@dataclass
class LiveApprovalRecord:
    approval_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    status: str = "pending"
    champion_version: str = ""
    readiness_report_id: str = ""
    shadow_validation_id: str = ""
    config_hash: str = ""
    risk_config_hash: str = ""
    runtime_mode: str = ""
    automated_score: float = 0.0
    hard_blocks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    gates: list[ApprovalGate] = field(default_factory=list)
    reviewer: str = ""
    reviewer_note: str = ""
    approved_at: str = ""
    expires_at: str = ""
    rejection_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "champion_version": self.champion_version,
            "readiness_report_id": self.readiness_report_id,
            "shadow_validation_id": self.shadow_validation_id,
            "config_hash": self.config_hash,
            "runtime_mode": self.runtime_mode,
            "automated_score": round(self.automated_score, 1),
            "hard_blocks": self.hard_blocks,
            "warnings": self.warnings,
            "gates": [g.to_dict() for g in self.gates],
            "reviewer": self.reviewer,
            "reviewer_note": self.reviewer_note[:100] if self.reviewer_note else "",
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
            "rejection_reason": self.rejection_reason,
        }
