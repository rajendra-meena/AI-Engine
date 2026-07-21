"""
VWAP Indicator — Volume Weighted Average Price

Session-based: resets at the start of each trading day.
Formula: VWAP = Σ(typical_price × volume) / Σ(volume)
Where: typical_price = (high + low + close) / 3
"""

from typing import Any

from indicators.base import BaseIndicator
from models.candle import Candle


class VWAP(BaseIndicator):
    name = "vwap"

    def __init__(self):
        self._cumulative_tpv = 0.0  # typical_price × volume
        self._cumulative_volume = 0.0
        self._value: float | None = None
        self._history: list[float] = []
        self._last_date: str = ""

    def update(self, candle: Candle) -> float | None:
        candle_date = candle.time[:10] if candle.time else ""

        # Reset at new trading day
        if candle_date and candle_date != self._last_date:
            if self._last_date:
                pass  # session boundary noted
            self._last_date = candle_date
            # New day: reset cumulative values
            self._cumulative_tpv = 0.0
            self._cumulative_volume = 0.0

        typical_price = (candle.high + candle.low + candle.close) / 3.0
        self._cumulative_tpv += typical_price * candle.volume
        self._cumulative_volume += candle.volume

        if self._cumulative_volume > 0:
            self._value = self._cumulative_tpv / self._cumulative_volume
            self._history.append(self._value)

        return self._value

    def latest(self) -> float | None:
        return self._value

    def history(self, count: int = 100) -> list[float]:
        return self._history[-count:]

    def reset(self):
        self._cumulative_tpv = 0.0
        self._cumulative_volume = 0.0
        self._value = None
        self._history.clear()
        self._last_date = ""

    def is_ready(self) -> bool:
        return self._value is not None and self._cumulative_volume > 0

    def warmup_needed(self) -> int:
        return 1
