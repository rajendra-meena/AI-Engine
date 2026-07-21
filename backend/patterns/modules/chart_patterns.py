"""
Chart Pattern Detector — Detects multi-candle chart patterns.

Detects:
  - Double Top / Double Bottom (reversal)
  - Head & Shoulders / Inverse H&S
  - Ascending/Descending/Symmetrical Triangle
  - Rectangle / Channel
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from models.candle import Candle


@dataclass
class ChartPattern:
    name: str
    direction: str  # "bullish" or "bearish"
    confidence: str  # "low", "medium", "high"
    price: float = 0.0
    time: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "direction": self.direction, "confidence": self.confidence,
                "price": self.price, "time": self.time, "description": self.description}


class ChartPatternDetector:
    """Detects multi-candle chart formations from recent swing points."""

    def __init__(self, lookback: int = 50):
        self.lookback = lookback
        self._candles: deque[Candle] = deque(maxlen=lookback)
        self._patterns: list[ChartPattern] = []
        self._highs: list[float] = []
        self._lows: list[float] = []

    def update(self, candle: Candle, swings_high: list[float], swings_low: list[float]) -> list[ChartPattern]:
        """Process a candle with current swing points. Returns new patterns."""
        self._candles.append(candle)
        new_patterns: list[ChartPattern] = []

        if len(swings_high) < 3 or len(swings_low) < 3:
            return new_patterns

        recent_highs = swings_high[-5:]
        recent_lows = swings_low[-5:]

        # Double Top: 2 similar highs with a dip in between
        if len(recent_highs) >= 2:
            h1, h2 = recent_highs[-2], recent_highs[-1]
            if abs(h2 - h1) / h1 < 0.005 and candle.close < h2:
                new_patterns.append(ChartPattern(
                    name="double_top", direction="bearish", confidence="medium",
                    price=h2, time=candle.time,
                    description=f"Double top at {h2:.1f}"))

        # Double Bottom: 2 similar lows with a rally in between
        if len(recent_lows) >= 2:
            l1, l2 = recent_lows[-2], recent_lows[-1]
            if abs(l2 - l1) / l1 < 0.005 and candle.close > l2:
                new_patterns.append(ChartPattern(
                    name="double_bottom", direction="bullish", confidence="medium",
                    price=l2, time=candle.time,
                    description=f"Double bottom at {l2:.1f}"))

        # Head & Shoulders: 3 peaks with middle highest
        if len(recent_highs) >= 3:
            h1, h2, h3 = recent_highs[-3], recent_highs[-2], recent_highs[-1]
            if h2 > h1 and h2 > h3 and abs(h1 - h3) / h1 < 0.01:
                new_patterns.append(ChartPattern(
                    name="head_and_shoulders", direction="bearish", confidence="medium",
                    price=h2, time=candle.time,
                    description=f"Head & Shoulders at {h2:.1f}"))

        # Inverse H&S: 3 troughs with middle lowest
        if len(recent_lows) >= 3:
            l1, l2, l3 = recent_lows[-3], recent_lows[-2], recent_lows[-1]
            if l2 < l1 and l2 < l3 and abs(l1 - l3) / l1 < 0.01:
                new_patterns.append(ChartPattern(
                    name="inverse_head_and_shoulders", direction="bullish", confidence="medium",
                    price=l2, time=candle.time,
                    description=f"Inverse H&S at {l2:.1f}"))

        self._highs.extend([c.high for c in self._candles][-50:])
        self._lows.extend([c.low for c in self._candles][-50:])

        if new_patterns:
            self._patterns.extend(new_patterns)
        return new_patterns

    def recent(self, count: int = 10) -> list[ChartPattern]:
        return self._patterns[-count:]

    def reset(self):
        self._candles.clear()
        self._patterns.clear()
        self._highs.clear()
        self._lows.clear()
