"""
ChampionRuntimeResolver — resolves the current governed champion strategy version
for runtime execution. Only accepts CHAMPION status strategies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backtest.strategy_version import ChampionManager, VersionStatus


class ChampionRuntimeResolver:
    """
    Resolves the current champion strategy for runtime use.

    Only CHAMPION status strategies may be used for live/paper/shadow execution.
    CANDIDATE, REJECTED, RETIRED, and DRAFT strategies are never resolved.
    """

    def __init__(self, champion_manager: ChampionManager | None = None):
        self._champion_manager = champion_manager

    def set_champion_manager(self, mgr: ChampionManager):
        self._champion_manager = mgr

    def get_current_champion(self) -> dict[str, Any] | None:
        """Get the current champion strategy version."""
        if not self._champion_manager:
            return None
        champ = self._champion_manager.get_champion()
        if not champ or champ.status != VersionStatus.CHAMPION:
            return None
        return {
            "strategy_version_id": champ.version_id,
            "strategy_name": champ.name,
            "strategy_version": champ.version_id[:8],
            "status": champ.status,
            "created_at": champ.created_at,
            "parameters": {
                "confidence_threshold": champ.confidence_threshold,
                "strategy_score_threshold": champ.strategy_score_threshold,
                "minimum_rr": champ.minimum_rr,
                "risk_percent": champ.risk_percent,
            },
            "parameter_hash": champ.parameter_hash,
            "source": champ.source,
            "source_optimization_id": champ.optimization_id,
            "governance_report_id": champ.governance_report_id,
            "validation_score": champ.validation_score,
            "oos_score": champ.oos_score,
        }

    def resolve_for_symbol(self, symbol: str) -> dict[str, Any] | None:
        """Resolve champion for a specific symbol. Returns champion info or None."""
        champ = self.get_current_champion()
        if not champ:
            return None
        champ["symbol"] = symbol
        champ["resolved_at"] = datetime.now(timezone.utc).isoformat()
        return champ

    def validate_champion(self) -> dict[str, Any]:
        """Validate that a valid champion exists for execution."""
        champ = self.get_current_champion()
        if not champ:
            return {"valid": False, "reason": "No champion strategy available"}
        return {"valid": True, "champion": champ}

    def get_status(self) -> dict[str, Any]:
        champ = self.get_current_champion()
        return {
            "champion_available": champ is not None,
            "champion": champ,
            "champion_manager_active": self._champion_manager is not None,
        }
