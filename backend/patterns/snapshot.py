"""PatternSnapshot — immutable snapshot of all detected patterns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PatternSnapshot:
    symbol: str = ""
    interval: str = ""
    timestamp: str = ""

    candlestick_patterns: list[dict[str, Any]] | None = None
    chart_patterns: list[dict[str, Any]] | None = None
    breakout_patterns: list[dict[str, Any]] | None = None

    strongest_pattern: str = ""
    pattern_direction: str = ""
    confidence: str = ""
    total_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "timestamp": self.timestamp,
            "candlestick_patterns": self.candlestick_patterns or [],
            "chart_patterns": self.chart_patterns or [],
            "breakout_patterns": self.breakout_patterns or [],
            "strongest_pattern": self.strongest_pattern,
            "pattern_direction": self.pattern_direction,
            "confidence": self.confidence,
            "total_count": self.total_count,
        }
