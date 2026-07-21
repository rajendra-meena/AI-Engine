"""
Structure Detector — Detects Break of Structure (BOS), Change of Character (CHoCH),
and market phase (accumulation, markup, distribution, markdown).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from market_structure.modules.swing_detector import SwingPoint
from market_structure.modules.trend_detector import TrendDirection


@dataclass
class StructureEvent:
    event_type: str  # "bos" or "choch"
    direction: str   # "bullish" or "bearish"
    price: float
    time: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.event_type, "direction": self.direction, "price": self.price, "time": self.time,
                "description": self.description}


class MarketPhase(str, Enum):
    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"
    CONSOLIDATION = "consolidation"
    UNDEFINED = "undefined"

from enum import Enum


class StructureDetector:
    """
    Detects BOS, CHoCH, and market phase transitions.

    BOS (Break of Structure): price breaks beyond a recent swing point.
    CHoCH (Change of Character): trend structure shifts (HH/HL → LH/LL or vice versa).
    """

    def __init__(self):
        self._events: list[StructureEvent] = []
        self._phase: MarketPhase = MarketPhase.UNDEFINED
        self._prev_trend: str = ""
        self._bos_count = 0
        self._choch_count = 0
        self._last_bos: StructureEvent | None = None
        self._last_choch: StructureEvent | None = None
        self._impulse_active = False
        self._pullback_active = False
        self._consolidation_bars = 0

    def update(self, candle, trend_info: dict[str, Any], swings: list[SwingPoint]) -> list[StructureEvent]:
        """Process candle + trend + swings. Returns new structure events."""
        new_events: list[StructureEvent] = []
        direction = trend_info.get("direction", "RANGING")

        # Trend change detection
        if self._prev_trend and direction != self._prev_trend:
            choch = StructureEvent(
                event_type="choch",
                direction="bullish" if direction == "UPTREND" else "bearish",
                price=candle.close,
                time=candle.time,
                description=f"Trend changed: {self._prev_trend} → {direction}",
            )
            self._events.append(choch)
            self._last_choch = choch
            self._choch_count += 1
            new_events.append(choch)

        self._prev_trend = direction

        # BOS detection: price breaks beyond last swing
        recent_highs = [s for s in swings if s.type == "high"][-3:]
        recent_lows = [s for s in swings if s.type == "low"][-3:]

        if direction == "UPTREND" and recent_lows:
            last_swing_low = recent_lows[-1].price
            if candle.low < last_swing_low:
                bos = StructureEvent(
                    event_type="bos",
                    direction="bearish",
                    price=candle.low,
                    time=candle.time,
                    description=f"BOS bearish: low {candle.low:.1f} broke swing low {last_swing_low:.1f}",
                )
                self._events.append(bos)
                self._last_bos = bos
                self._bos_count += 1
                new_events.append(bos)

        elif direction == "DOWNTREND" and recent_highs:
            last_swing_high = recent_highs[-1].price
            if candle.high > last_swing_high:
                bos = StructureEvent(
                    event_type="bos",
                    direction="bullish",
                    price=candle.high,
                    time=candle.time,
                    description=f"BOS bullish: high {candle.high:.1f} broke swing high {last_swing_high:.1f}",
                )
                self._events.append(bos)
                self._last_bos = bos
                self._bos_count += 1
                new_events.append(bos)

        # Market phase heuristic
        self._update_phase(direction)

        # Impulse / pullback tracking
        if direction in ("UPTREND", "DOWNTREND"):
            if any(e.event_type == "bos" for e in new_events):
                self._impulse_active = True
                self._pullback_active = False
                self._consolidation_bars = 0
            else:
                if self._impulse_active:
                    self._pullback_active = True
                self._consolidation_bars += 1
        else:
            self._impulse_active = False
            self._pullback_active = False
            self._consolidation_bars += 1

        return new_events

    def _update_phase(self, direction: str):
        if direction == "RANGING":
            if self._phase in (MarketPhase.ACCUMULATION, MarketPhase.DISTRIBUTION):
                pass  # maintain phase
            elif self._consolidation_bars > 5:
                self._phase = MarketPhase.CONSOLIDATION
        elif direction == "UPTREND":
            self._phase = MarketPhase.MARKUP
        elif direction == "DOWNTREND":
            self._phase = MarketPhase.MARKDOWN

    def get_info(self) -> dict[str, Any]:
        return {
            "phase": self._phase.value,
            "bos_count": self._bos_count,
            "choch_count": self._choch_count,
            "last_bos": self._last_bos.to_dict() if self._last_bos else None,
            "last_choch": self._last_choch.to_dict() if self._last_choch else None,
            "impulse_active": self._impulse_active,
            "pullback_active": self._pullback_active,
            "consolidation_bars": self._consolidation_bars,
        }

    def reset(self):
        self._events.clear()
        self._phase = MarketPhase.UNDEFINED
        self._prev_trend = ""
        self._bos_count = 0
        self._choch_count = 0
        self._last_bos = self._last_choch = None
        self._impulse_active = False
        self._pullback_active = False
        self._consolidation_bars = 0
