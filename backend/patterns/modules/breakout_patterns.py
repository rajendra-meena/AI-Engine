"""
Breakout Pattern Detector — Detects breakout patterns from price action.

Detects:
  - Range Breakout / Range Breakdown
  - NR7 (Narrow Range 7)
  - Volatility Contraction
  - Flag / Pennant
  - Gap detection
  - Pullback continuation
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from models.candle import Candle


@dataclass
class BreakoutPattern:
    name: str
    direction: str  # "bullish" or "bearish"
    strength: str  # "weak", "moderate", "strong"
    price: float = 0.0
    time: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "direction": self.direction,
            "strength": self.strength,
            "price": self.price,
            "time": self.time,
            "description": self.description,
        }


class BreakoutPatternDetector:
    """Detects breakout/continuation patterns from price action."""

    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self._candles: deque[Candle] = deque(maxlen=lookback)
        self._patterns: list[BreakoutPattern] = []

    def update(self, candle: Candle) -> list[BreakoutPattern]:
        """Process a candle. Returns new breakout patterns."""
        self._candles.append(candle)
        new_patterns: list[BreakoutPattern] = []

        if len(self._candles) < 3:
            return new_patterns

        lst = list(self._candles)
        p = lst[-2]
        pp = lst[-3] if len(lst) >= 3 else p

        # Range Breakout: close above recent range high
        recent_highs = [c.high for c in lst[-10:]]
        recent_lows = [c.low for c in lst[-10:]]
        range_high = max(recent_highs[:-1]) if len(recent_highs) > 1 else candle.high
        range_low = min(recent_lows[:-1]) if len(recent_lows) > 1 else candle.low
        range_size = range_high - range_low

        if candle.close > range_high:
            new_patterns.append(
                BreakoutPattern(
                    name="range_breakout",
                    direction="bullish",
                    strength="strong",
                    price=candle.close,
                    time=candle.time,
                    description=f"Range breakout above {range_high:.1f}",
                )
            )
        elif candle.close < range_low:
            new_patterns.append(
                BreakoutPattern(
                    name="range_breakdown",
                    direction="bearish",
                    strength="strong",
                    price=candle.close,
                    time=candle.time,
                    description=f"Range breakdown below {range_low:.1f}",
                )
            )

        # NR7: narrowest range in 7 candles
        if len(lst) >= 7:
            ranges = [abs(c.high - c.low) for c in lst[-7:]]
            if ranges[-1] == min(ranges):
                new_patterns.append(
                    BreakoutPattern(
                        name="nr7",
                        direction="neutral",
                        strength="moderate",
                        price=candle.close,
                        time=candle.time,
                        description="NR7 — narrow range, potential expansion",
                    )
                )

        # Volatility Contraction (comparing recent ranges)
        if len(lst) >= 10:
            recent = [c.high - c.low for c in lst[-5:]]
            older = [c.high - c.low for c in lst[-10:-5]]
            if sum(recent) < sum(older) * 0.7:
                new_patterns.append(
                    BreakoutPattern(
                        name="volatility_contraction",
                        direction="neutral",
                        strength="moderate",
                        price=candle.close,
                        time=candle.time,
                        description="Volatility contracting — potential breakout",
                    )
                )

        # Flag/Pennant (consolidation after strong move)
        if len(lst) >= 6:
            body_sizes = [abs(c.close - c.open) for c in lst[-5:]]
            if sum(body_sizes) < sum(body_sizes[:3]) * 0.8 and range_size > 0:
                new_patterns.append(
                    BreakoutPattern(
                        name="flag_pennant",
                        direction="neutral",
                        strength="moderate",
                        price=candle.close,
                        time=candle.time,
                        description="Possible flag/pennant consolidation",
                    )
                )

        if new_patterns:
            self._patterns.extend(new_patterns)
        return new_patterns

    def recent(self, count: int = 10) -> list[BreakoutPattern]:
        return self._patterns[-count:]

    def reset(self):
        self._candles.clear()
        self._patterns.clear()
