"""DecisionSnapshot — immutable final AI decision output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionSnapshot:
    symbol: str = ""
    timestamp: str = ""

    decision: str = "NO_TRADE"
    score: int = 0
    score_grade: str = "VERY_LOW"
    confidence: int = 0
    confidence_grade: str = "VERY_LOW"
    risk_level: str = "EXTREME"
    risk_score: int = 0
    max_risk_percent: float = 0.0

    trade_plan: dict[str, Any] | None = None
    reasoning: list[str] | None = None
    warnings: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "decision": self.decision,
            "score": self.score,
            "score_grade": self.score_grade,
            "confidence": self.confidence,
            "confidence_grade": self.confidence_grade,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "max_risk_percent": self.max_risk_percent,
            "trade_plan": self.trade_plan or {},
            "reasoning": self.reasoning or [],
            "warnings": self.warnings or [],
        }
