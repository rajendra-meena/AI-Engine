"""
Candlestick Pattern Detector

Detects 12+ single and multi-candle patterns from closed candles.
All methods are static — operate on the current and previous candle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.candle import Candle


@dataclass
class DetectedPattern:
    name: str
    direction: str  # "bullish", "bearish", or "neutral"
    strength: str  # "weak", "moderate", "strong"
    candle_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "direction": self.direction,
            "strength": self.strength,
            "time": self.candle_time,
        }


class CandlestickPatternDetector:
    """Detects candlestick patterns from pairs of consecutive candles."""

    def __init__(self):
        self._prev: Candle | None = None
        self._patterns: list[DetectedPattern] = []

    def update(self, candle: Candle) -> list[DetectedPattern]:
        """Compare with previous candle to detect patterns. Returns new detections."""
        new_patterns: list[DetectedPattern] = []
        if self._prev is None:
            self._prev = candle
            return new_patterns

        p, c = self._prev, candle
        body_p = abs(p.close - p.open)
        body_c = abs(c.close - c.open)
        range_p = p.high - p.low
        range_c = c.high - c.low
        upper_p = p.high - max(p.close, p.open)
        lower_p = min(p.close, p.open) - p.low

        # Doji (very small body)
        if range_c > 0 and body_c < range_c * 0.1:
            new_patterns.append(
                DetectedPattern(
                    name="doji",
                    direction="neutral",
                    strength="moderate",
                    candle_time=candle.time,
                )
            )

        # Hammer / Shooting Star (small body, long lower/upper wick)
        if range_c > 0 and body_c < range_c * 0.35:
            lower = min(c.close, c.open) - c.low
            upper = c.high - max(c.close, c.open)
            if lower > body_c * 2 and upper < body_c:
                new_patterns.append(
                    DetectedPattern(
                        name="hammer",
                        direction="bullish",
                        strength="strong",
                        candle_time=candle.time,
                    )
                )
            if upper > body_c * 2 and lower < body_c:
                new_patterns.append(
                    DetectedPattern(
                        name="shooting_star",
                        direction="bearish",
                        strength="strong",
                        candle_time=candle.time,
                    )
                )

        # Engulfing
        if range_p > 0:
            if c.close > c.open and c.open < p.low and c.close > p.high:
                new_patterns.append(
                    DetectedPattern(
                        name="bullish_engulfing",
                        direction="bullish",
                        strength="strong",
                        candle_time=candle.time,
                    )
                )
            if c.close < c.open and c.open > p.high and c.close < p.low:
                new_patterns.append(
                    DetectedPattern(
                        name="bearish_engulfing",
                        direction="bearish",
                        strength="strong",
                        candle_time=candle.time,
                    )
                )

        # Inside Bar
        if c.high <= p.high and c.low >= p.low:
            new_patterns.append(
                DetectedPattern(
                    name="inside_bar",
                    direction="neutral",
                    strength="weak",
                    candle_time=candle.time,
                )
            )

        # Outside Bar
        if c.high > p.high and c.low < p.low:
            direction = "bullish" if c.close > c.open else "bearish"
            new_patterns.append(
                DetectedPattern(
                    name="outside_bar",
                    direction=direction,
                    strength="moderate",
                    candle_time=candle.time,
                )
            )

        # Marubozu (very long body, almost no wicks)
        if body_c > 0 and range_c > 0 and body_c > range_c * 0.95:
            if upper_p < range_c * 0.02 or lower_p < range_c * 0.02:
                direction = "bullish" if c.close > c.open else "bearish"
                new_patterns.append(
                    DetectedPattern(
                        name="marubozu",
                        direction=direction,
                        strength="strong",
                        candle_time=candle.time,
                    )
                )

        # Spinning Top (small body, long wicks both sides)
        if range_c > 0 and body_c < range_c * 0.4:
            upper = c.high - max(c.close, c.open)
            lower = min(c.close, c.open) - c.low
            if upper > body_c * 1.5 and lower > body_c * 1.5:
                new_patterns.append(
                    DetectedPattern(
                        name="spinning_top",
                        direction="neutral",
                        strength="weak",
                        candle_time=candle.time,
                    )
                )

        self._patterns.extend(new_patterns)
        self._prev = candle
        return new_patterns

    def recent(self, count: int = 10) -> list[DetectedPattern]:
        return self._patterns[-count:]

    def reset(self):
        self._prev = None
        self._patterns.clear()
