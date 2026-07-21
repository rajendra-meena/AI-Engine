"""
Liquidity Detector — Identifies liquidity zones from price action.

Detects:
    - Equal highs / equal lows (double tops/bottoms)
    - Liquidity above/below current price
    - Liquidity sweeps (price spikes through a cluster)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from models.candle import Candle


@dataclass
class LiquidityZone:
    zone_type: str  # "equal_high", "equal_low", "liquidity_above", "liquidity_below"
    price: float
    strength: int = 1  # number of touches
    time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.zone_type, "price": self.price, "strength": self.strength, "time": self.time}


class LiquidityDetector:
    """
    Detects liquidity zones from recent candle highs/lows.

    Equal highs = 2+ candles with similar highs within a tolerance.
    Equal lows  = 2+ candles with similar lows within a tolerance.
    """

    def __init__(self, lookback: int = 30, tolerance: float = 0.0005):
        self.lookback = lookback
        self.tolerance = tolerance  # 0.05% by default
        self._candles: deque[Candle] = deque(maxlen=lookback)
        self._zones: list[LiquidityZone] = []
        self._sweeps = 0

    def update(self, candle: Candle) -> list[LiquidityZone]:
        """Process a new candle. Returns any new liquidity zones detected."""
        self._candles.append(candle)
        new_zones: list[LiquidityZone] = []
        candles_list = list(self._candles)

        if len(candles_list) < 3:
            return new_zones

        # Equal highs
        for i in range(len(candles_list) - 1):
            diff = abs(candle.high - candles_list[i].high) / candle.high
            if diff < self.tolerance and candle.time != candles_list[i].time:
                existing = [z for z in self._zones if z.zone_type == "equal_high"
                           and abs(z.price - candle.high) / candle.high < self.tolerance]
                if not existing:
                    zone = LiquidityZone(zone_type="equal_high", price=round(candle.high, 2),
                                         strength=2, time=candle.time)
                    self._zones.append(zone)
                    new_zones.append(zone)

        # Equal lows
        for i in range(len(candles_list) - 1):
            diff = abs(candle.low - candles_list[i].low) / candle.low
            if diff < self.tolerance and candle.time != candles_list[i].time:
                existing = [z for z in self._zones if z.zone_type == "equal_low"
                           and abs(z.price - candle.low) / candle.low < self.tolerance]
                if not existing:
                    zone = LiquidityZone(zone_type="equal_low", price=round(candle.low, 2),
                                         strength=2, time=candle.time)
                    self._zones.append(zone)
                    new_zones.append(zone)

        # Liquidity sweep detection: price exceeded recent equal high/low then reversed
        for z in self._zones[-5:]:
            if z.zone_type == "equal_high" and candle.high > z.price * 1.001 and candle.close < z.price:
                self._sweeps += 1

        return new_zones

    def liquidity_above(self, current_price: float) -> list[LiquidityZone]:
        """Return liquidity zones above current price."""
        return [z for z in self._zones if z.price > current_price]

    def liquidity_below(self, current_price: float) -> list[LiquidityZone]:
        """Return liquidity zones below current price."""
        return [z for z in self._zones if z.price < current_price]

    def get_info(self) -> dict[str, Any]:
        return {
            "zones": [z.to_dict() for z in self._zones[-10:]],
            "total_zones": len(self._zones),
            "sweeps": self._sweeps,
        }

    def reset(self):
        self._candles.clear()
        self._zones.clear()
        self._sweeps = 0
