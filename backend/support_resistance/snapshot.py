"""SRSnapshot — immutable snapshot of all S/R levels and zones."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SRSnapshot:
    symbol: str = ""
    timestamp: str = ""
    nearest_support: float | None = None
    nearest_resistance: float | None = None
    major_supports: list[dict[str, Any]] | None = None
    major_resistances: list[dict[str, Any]] | None = None
    dynamic_levels: list[dict[str, Any]] | None = None
    supply_zones: list[dict[str, Any]] | None = None
    demand_zones: list[dict[str, Any]] | None = None
    psychological_levels: list[dict[str, Any]] | None = None
    breakout_state: str = "none"
    zone_strength: str = "WEAK"
    confidence: int = 0
    warnings: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "nearest_support": self.nearest_support,
            "nearest_resistance": self.nearest_resistance,
            "major_supports": self.major_supports or [],
            "major_resistances": self.major_resistances or [],
            "dynamic_levels": self.dynamic_levels or [],
            "supply_zones": self.supply_zones or [],
            "demand_zones": self.demand_zones or [],
            "psychological_levels": self.psychological_levels or [],
            "breakout_state": self.breakout_state,
            "zone_strength": self.zone_strength,
            "confidence": self.confidence,
            "warnings": self.warnings or [],
        }
