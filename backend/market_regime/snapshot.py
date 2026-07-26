"""Market Regime data models — frozen dataclasses for regime detection output."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"rg_{uuid.uuid4().hex[:12]}"


@dataclass(frozen=True)
class RegimeSnapshot:
    """Complete regime detection result for one symbol at one time."""
    id: str = ""
    symbol: str = ""
    timestamp: str = ""
    regime: str = ""
    regime_category: str = ""
    confidence: int = 0
    supporting_factors: tuple[str, ...] = ()
    duration_bars: int = 0
    duration_minutes: int = 0
    stability_score: float = 0.0
    transition_probability: float = 0.0
    previous_regime: str | None = None
    regime_age_bars: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id or _new_id(),
            "symbol": self.symbol,
            "timestamp": self.timestamp or _now(),
            "regime": self.regime,
            "regime_category": self.regime_category,
            "confidence": self.confidence,
            "supporting_factors": list(self.supporting_factors),
            "duration_bars": self.duration_bars,
            "duration_minutes": self.duration_minutes,
            "stability_score": self.stability_score,
            "transition_probability": self.transition_probability,
            "previous_regime": self.previous_regime,
            "regime_age_bars": self.regime_age_bars,
        }


@dataclass(frozen=True)
class RegimeStrategyRecommendation:
    """Strategy recommendation for a detected regime."""
    regime: str = ""
    primary_strategy: str = ""
    secondary_strategy: str = ""
    avoid_strategies: tuple[str, ...] = ()
    expected_win_rate: float = 0.0
    historical_success: float = 0.0
    confidence: int = 0
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime": self.regime,
            "primary": self.primary_strategy,
            "secondary": self.secondary_strategy,
            "avoid": list(self.avoid_strategies),
            "expected_win_rate": self.expected_win_rate,
            "historical_success": self.historical_success,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


@dataclass(frozen=True)
class RegimeTransition:
    """Record of a regime transition event."""
    id: str = ""
    symbol: str = ""
    timestamp: str = ""
    from_regime: str = ""
    to_regime: str = ""
    transition_type: str = ""
    confidence: float = 0.0
    duration_bars: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id or _new_id(),
            "symbol": self.symbol,
            "timestamp": self.timestamp or _now(),
            "from_regime": self.from_regime,
            "to_regime": self.to_regime,
            "transition_type": self.transition_type,
            "confidence": self.confidence,
            "duration_bars": self.duration_bars,
        }


@dataclass(frozen=True)
class RegimeExplanation:
    """Human-readable explanation of a regime detection."""
    regime: str = ""
    confidence: int = 0
    primary_reason: str = ""
    supporting_evidence: tuple[str, ...] = ()
    recommended_strategy: str = ""
    avoid_strategies: tuple[str, ...] = ()
    strategy_reasoning: str = ""
    market_conditions_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime": self.regime,
            "confidence": self.confidence,
            "primary_reason": self.primary_reason,
            "supporting_evidence": list(self.supporting_evidence),
            "recommended_strategy": self.recommended_strategy,
            "avoid_strategies": list(self.avoid_strategies),
            "strategy_reasoning": self.strategy_reasoning,
            "market_conditions_summary": self.market_conditions_summary,
        }
