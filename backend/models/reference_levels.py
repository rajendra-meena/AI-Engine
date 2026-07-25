"""
MarketMind AI — Reference Levels Model

Standardized daily/weekly reference levels.
Maps to the existing dailyRefs API response format via to_dict().
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReferenceLevels:
    """
    Daily and weekly reference levels for a symbol.

    All values computed from the most recent trading days.
    """

    symbol: str = ""
    prev_day_high: float = 0.0
    prev_day_low: float = 0.0
    prev_day_close: float = 0.0
    prev_day_open: float = 0.0
    weekly_high: float = 0.0
    weekly_low: float = 0.0
    prev_day_range: float = 0.0
    prev_day_midpoint: float = 0.0
    prev_day_vwap: float = 0.0

    # ── Serialization (matching existing dailyRefs format) ──

    def to_dict(self) -> dict[str, Any]:
        """Returns dict matching the existing dailyRefs API format."""
        return {
            "prevDayHigh": self.prev_day_high,
            "prevDayLow": self.prev_day_low,
            "prevDayClose": self.prev_day_close,
            "prevDayOpen": self.prev_day_open,
            "weeklyHigh": self.weekly_high,
            "weeklyLow": self.weekly_low,
            "prevDayRange": self.prev_day_range,
            "prevDayMidpoint": self.prev_day_midpoint,
            "prevDayVWAP": self.prev_day_vwap,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReferenceLevels:
        """Create from a dict (accepts both camelCase and snake_case keys)."""
        return cls(
            symbol=data.get("symbol", ""),
            prev_day_high=float(data.get("prevDayHigh", data.get("prev_day_high", 0))),
            prev_day_low=float(data.get("prevDayLow", data.get("prev_day_low", 0))),
            prev_day_close=float(
                data.get("prevDayClose", data.get("prev_day_close", 0))
            ),
            prev_day_open=float(data.get("prevDayOpen", data.get("prev_day_open", 0))),
            weekly_high=float(data.get("weeklyHigh", data.get("weekly_high", 0))),
            weekly_low=float(data.get("weeklyLow", data.get("weekly_low", 0))),
            prev_day_range=float(
                data.get("prevDayRange", data.get("prev_day_range", 0))
            ),
            prev_day_midpoint=float(
                data.get("prevDayMidpoint", data.get("prev_day_midpoint", 0))
            ),
            prev_day_vwap=float(data.get("prevDayVWAP", data.get("prev_day_vwap", 0))),
        )
