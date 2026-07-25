"""SR Engine data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SRLevel:
    """A single support or resistance level."""

    price: float
    level_type: str  # "support" or "resistance"
    source: str  # "swing_high", "swing_low", "prev_day_high", etc.
    strength: str  # "VERY_WEAK", "WEAK", "NORMAL", "STRONG", "VERY_STRONG"
    touches: int = 0
    age: int = 0
    label: str = ""
    is_major: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "price": self.price,
            "type": self.level_type,
            "source": self.source,
            "strength": self.strength,
            "touches": self.touches,
            "label": self.label,
            "is_major": self.is_major,
        }


@dataclass
class SupplyDemandZone:
    """A supply or demand zone defined by a price range."""

    zone_type: str  # "supply" or "demand"
    top: float
    bottom: float
    strength: str = "NORMAL"
    touch_count: int = 0
    creation_time: str = ""
    broken: bool = False
    active: bool = True
    age: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.zone_type,
            "top": self.top,
            "bottom": self.bottom,
            "strength": self.strength,
            "touches": self.touch_count,
            "active": self.active,
            "broken": self.broken,
        }
