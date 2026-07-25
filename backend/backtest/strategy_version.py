"""
Strategy Version Model — versioned strategy representation with status lifecycle.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class VersionStatus:
    DRAFT = "draft"
    CANDIDATE = "candidate"
    CHAMPION = "champion"
    REJECTED = "rejected"
    RETIRED = "retired"
    RESEARCH_APPROVED = "research_approved"


class VersionSource:
    MANUAL = "manual"
    OPTIMIZATION = "optimization"
    RESEARCH = "research"


@dataclass
class StrategyVersion:
    strategy_id: str = ""
    version_id: str = ""
    parent_version_id: str = ""
    name: str = ""
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    status: str = "draft"
    source: str = "manual"
    optimization_id: str = ""
    validation_id: str = ""
    governance_report_id: str = ""

    # Strategy parameters
    confidence_threshold: float = 65.0
    strategy_score_threshold: float = 60.0
    minimum_rr: float = 1.5
    risk_percent: float = 1.0
    parameter_hash: str = ""

    # Optional metrics snapshot
    validation_score: float = 0.0
    oos_score: float = 0.0
    oos_return: float = 0.0
    oos_win_rate: float = 0.0
    oos_profit_factor: float = 0.0
    oos_sharpe: float = 0.0
    oos_max_drawdown_pct: float = 0.0
    overfit_risk: str = "unknown"
    governance_score: float = 0.0

    # Metadata
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def compute_hash(self) -> str:
        raw = f"{self.confidence_threshold}|{self.strategy_score_threshold}|{self.minimum_rr}|{self.risk_percent}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "version_id": self.version_id,
            "parent_version_id": self.parent_version_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "source": self.source,
            "optimization_id": self.optimization_id,
            "validation_id": self.validation_id,
            "governance_report_id": self.governance_report_id,
            "confidence_threshold": self.confidence_threshold,
            "strategy_score_threshold": self.strategy_score_threshold,
            "minimum_rr": self.minimum_rr,
            "risk_percent": self.risk_percent,
            "parameter_hash": self.parameter_hash or self.compute_hash(),
            "validation_score": self.validation_score,
            "oos_score": self.oos_score,
            "oos_return": self.oos_return,
            "oos_win_rate": self.oos_win_rate,
            "oos_profit_factor": self.oos_profit_factor,
            "oos_sharpe": self.oos_sharpe,
            "oos_max_drawdown_pct": self.oos_max_drawdown_pct,
            "overfit_risk": self.overfit_risk,
            "governance_score": self.governance_score,
            "tags": self.tags,
            "notes": self.notes,
        }


class ChampionManager:
    """Manages strategy versions, champion/challenger lifecycle."""

    def __init__(self):
        self._versions: dict[str, StrategyVersion] = {}
        self._champion_id: str | None = None

    def create_version(
        self,
        strategy_id: str = "default",
        name: str = "",
        confidence: float = 65.0,
        strategy_score: float = 60.0,
        min_rr: float = 1.5,
        risk_pct: float = 1.0,
        source: str = "manual",
        parent_version_id: str = "",
        optimization_id: str = "",
        validation_id: str = "",
        tags: list[str] | None = None,
    ) -> StrategyVersion:
        vid = f"v_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()
        version = StrategyVersion(
            strategy_id=strategy_id,
            version_id=vid,
            parent_version_id=parent_version_id,
            name=name or f"Version {vid[:8]}",
            created_at=now,
            updated_at=now,
            status=VersionStatus.DRAFT,
            source=source,
            optimization_id=optimization_id,
            validation_id=validation_id,
            confidence_threshold=confidence,
            strategy_score_threshold=strategy_score,
            minimum_rr=min_rr,
            risk_percent=risk_pct,
        )
        version.parameter_hash = version.compute_hash()
        self._versions[vid] = version
        return version

    def register_champion(self, version_id: str) -> bool:
        version = self._versions.get(version_id)
        if not version:
            return False
        if self._champion_id:
            old = self._versions.get(self._champion_id)
            if old:
                old.status = VersionStatus.RETIRED
        version.status = VersionStatus.CHAMPION
        self._champion_id = version_id
        return True

    def register_challenger(self, version_id: str) -> bool:
        version = self._versions.get(version_id)
        if not version:
            return False
        version.status = VersionStatus.CANDIDATE
        return True

    def promote_challenger(self, version_id: str) -> bool:
        version = self._versions.get(version_id)
        if not version or version.status != VersionStatus.CANDIDATE:
            return False
        return self.register_champion(version_id)

    def reject_challenger(self, version_id: str) -> bool:
        version = self._versions.get(version_id)
        if not version:
            return False
        version.status = VersionStatus.REJECTED
        return True

    def get_champion(self) -> StrategyVersion | None:
        if self._champion_id:
            return self._versions.get(self._champion_id)
        return None

    def get_version(self, version_id: str) -> StrategyVersion | None:
        return self._versions.get(version_id)

    def get_all_versions(self) -> list[StrategyVersion]:
        return list(self._versions.values())

    def get_champion_id(self) -> str | None:
        return self._champion_id
