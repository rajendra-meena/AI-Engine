"""
Trend Detector — Analyzes swing sequence to determine trend.

Detects:
    - Higher High (HH) / Higher Low (HL) = UPTREND
    - Lower High (LH) / Lower Low (LL)   = DOWNTREND
    - Mixed / unclear                      = RANGING

Tracks trend age, strength, and transition points.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from market_structure.modules.swing_detector import SwingPoint


class TrendDirection(str, Enum):
    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    RANGING = "RANGING"


class TrendStrength(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


class TrendDetector:
    """
    Analyzes swing highs and lows to determine trend.

    Call update() after new swings are detected.
    """

    def __init__(self):
        self._direction: TrendDirection = TrendDirection.RANGING
        self._strength: TrendStrength = TrendStrength.WEAK
        self._age = 0  # bars in current trend
        self._last_hh: float | None = None
        self._last_hl: float | None = None
        self._last_lh: float | None = None
        self._last_ll: float | None = None
        self._changes = 0

    def update(self, swings: list[SwingPoint]) -> TrendDirection:
        """Process new swing points and update trend direction."""
        highs = [s for s in swings if s.type == "high"]
        lows = [s for s in swings if s.type == "low"]

        if len(highs) < 2 and len(lows) < 2:
            return self._direction

        prev_direction = self._direction

        # Check for HH/HL (uptrend)
        if len(highs) >= 2:
            recent_highs = highs[-2:]
            if recent_highs[1].price > recent_highs[0].price:
                self._last_hh = recent_highs[1].price
            else:
                self._last_lh = recent_highs[1].price

        if len(lows) >= 2:
            recent_lows = lows[-2:]
            if recent_lows[1].price > recent_lows[0].price:
                self._last_hl = recent_lows[1].price
            else:
                self._last_ll = recent_lows[1].price

        # Determine direction from last HH/HL or LH/LL
        if self._last_hh is not None and self._last_hl is not None:
            self._direction = TrendDirection.UPTREND
        elif self._last_lh is not None and self._last_ll is not None:
            self._direction = TrendDirection.DOWNTREND
        else:
            self._direction = TrendDirection.RANGING

        # Strength
        if self._direction != TrendDirection.RANGING:
            if self._last_hh is not None and self._last_hl is not None:
                diff_hh = abs(self._last_hh - (self._last_hl or self._last_hh))
                self._strength = TrendStrength.STRONG if diff_hh > 0 else TrendStrength.MODERATE
            elif self._last_lh is not None and self._last_ll is not None:
                diff_ll = abs(self._last_lh - (self._last_ll or self._last_lh))
                self._strength = TrendStrength.STRONG if diff_ll > 0 else TrendStrength.MODERATE

        # Age and changes
        if self._direction != prev_direction:
            self._age = 0
            self._changes += 1
        else:
            self._age += 1

        return self._direction

    def get_info(self) -> dict[str, Any]:
        return {
            "direction": self._direction.value,
            "strength": self._strength.value,
            "age": self._age,
            "last_hh": self._last_hh,
            "last_hl": self._last_hl,
            "last_lh": self._last_lh,
            "last_ll": self._last_ll,
            "changes": self._changes,
        }

    def reset(self):
        self._direction = TrendDirection.RANGING
        self._strength = TrendStrength.WEAK
        self._age = 0
        self._last_hh = self._last_hl = self._last_lh = self._last_ll = None
        self._changes = 0
