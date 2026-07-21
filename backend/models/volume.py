"""
MarketMind AI — Volume Data Model

Volume analysis data associated with a candle or snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VolumeData:
    """
    Volume analysis for a single candle or time period.
    """
    current_volume: float = 0.0
    average_volume: float = 0.0
    volume_ratio: float = 0.0             # current / average
    is_spike: bool = False                 # current > 1.5× average
    is_low: bool = False                   # current < 0.5× average
    previous_volume: float = 0.0
    change_percent: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_volume": self.current_volume,
            "average_volume": self.average_volume,
            "volume_ratio": round(self.volume_ratio, 2),
            "is_spike": self.is_spike,
            "is_low": self.is_low,
            "previous_volume": self.previous_volume,
            "change_percent": round(self.change_percent, 1),
        }
