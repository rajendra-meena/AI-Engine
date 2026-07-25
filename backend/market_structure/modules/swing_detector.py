"""
Swing Detector — Finds swing highs and lows from price action.

Uses a zigzag-style detection: a swing high is a candle whose high is higher
than N candles on each side. Configurable lookback.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from models.candle import Candle


@dataclass
class SwingPoint:
    type: str  # "high" or "low"
    price: float
    index: int
    time: str = ""
    strength: str = "minor"  # "minor" or "major"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "price": self.price,
            "time": self.time,
            "strength": self.strength,
        }


class SwingDetector:
    """
    Detects swing highs and lows from candle history.

    A swing high = candle whose high > left N and >= right N candles.
    A swing low  = candle whose low  < left N and <= right N candles.
    """

    def __init__(self, lookback: int = 2):
        self.lookback = lookback
        self._candles: deque[Candle] = deque(maxlen=100)
        self._swings: list[SwingPoint] = []
        self._count = 0

    def update(self, candle: Candle) -> list[SwingPoint]:
        """Process a new candle. Returns any new swing points detected."""
        self._candles.append(candle)
        self._count += 1
        new_swings: list[SwingPoint] = []

        if len(self._candles) < self.lookback * 2 + 1:
            return new_swings

        mid_idx = len(self._candles) - self.lookback - 1
        mid = self._candles[mid_idx]

        left = list(self._candles)[mid_idx - self.lookback : mid_idx]
        right = list(self._candles)[mid_idx + 1 : mid_idx + self.lookback + 1]

        # Swing high
        if all(mid.high > c.high for c in left) and all(
            mid.high >= c.high for c in right
        ):
            strength = self._classify_swing_strength(mid.high, mid_idx, "high")
            sp = SwingPoint(
                type="high",
                price=mid.high,
                index=self._count - self.lookback - 1,
                time=mid.time,
                strength=strength,
            )
            self._swings.append(sp)
            new_swings.append(sp)

        # Swing low
        if all(mid.low < c.low for c in left) and all(mid.low <= c.low for c in right):
            strength = self._classify_swing_strength(mid.low, mid_idx, "low")
            sp = SwingPoint(
                type="low",
                price=mid.low,
                index=self._count - self.lookback - 1,
                time=mid.time,
                strength=strength,
            )
            self._swings.append(sp)
            new_swings.append(sp)

        return new_swings

    def _classify_swing_strength(self, price: float, idx: int, swing_type: str) -> str:
        """Classify as major if the swing is more extreme than surrounding swings."""
        return "major"  # simplified; could measure distance to prior swing

    def latest_swing(self, swing_type: str | None = None) -> SwingPoint | None:
        """Most recent swing, optionally filtered by type."""
        for s in reversed(self._swings):
            if swing_type is None or s.type == swing_type:
                return s
        return None

    def latest_swing_high(self) -> SwingPoint | None:
        return self.latest_swing("high")

    def latest_swing_low(self) -> SwingPoint | None:
        return self.latest_swing("low")

    def recent_swings(self, count: int = 10) -> list[SwingPoint]:
        return self._swings[-count:]

    def all_swings(self) -> list[SwingPoint]:
        return list(self._swings)

    def reset(self):
        self._candles.clear()
        self._swings.clear()
        self._count = 0

    @property
    def swings_count(self) -> int:
        return len(self._swings)
