"""MTFSnapshot — immutable multi-timeframe alignment view."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MTFSnapshot:
    symbol: str = ""
    timestamp: str = ""

    timeframes: dict[str, Any] | None = None

    alignment_level: str = "MIXED"
    alignment_score: int = 0
    institutional_bias: str = "NEUTRAL"
    market_condition: str = "MIXED"

    execution_timeframe: dict[str, str] | None = None

    trading_permission: str = "WAIT"
    overall_confidence: int = 0

    warnings: list[str] | None = None

    trigger_candle_version: str = ""
    analysis_cycle_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "timeframes": self.timeframes or {},
            "alignment_level": self.alignment_level,
            "alignment_score": self.alignment_score,
            "institutional_bias": self.institutional_bias,
            "market_condition": self.market_condition,
            "execution_timeframe": self.execution_timeframe or {},
            "trading_permission": self.trading_permission,
            "overall_confidence": self.overall_confidence,
            "warnings": self.warnings or [],
            "candle_version": self.trigger_candle_version,
            "analysis_cycle_id": self.analysis_cycle_id,
        }
