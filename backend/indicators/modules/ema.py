"""
EMA Indicator — Exponential Moving Average

Standard periods: 9, 20, 50, 200
Formula: EMA = (close × multiplier) + (prev_EMA × (1 - multiplier))
Where: multiplier = 2 / (period + 1)
"""

from collections import deque
from typing import Any

from indicators.base import BaseIndicator
from models.candle import Candle


class EMA(BaseIndicator):
    name = "ema"

    def __init__(self, period: int = 20):
        self.period = period
        self.multiplier = 2.0 / (period + 1)
        self._value: float | None = None
        self._history: deque[float] = deque(maxlen=1000)
        self._count = 0

    def update(self, candle: Candle) -> float | None:
        price = candle.close
        self._count += 1

        if self._count == 1:
            self._value = price  # seed with first value
        else:
            self._value = (price - self._value) * self.multiplier + self._value  # type: ignore

        if self._count >= self.period:
            self._history.append(self._value)  # type: ignore
        return self._value if self._count >= self.period else None

    def latest(self) -> float | None:
        return self._value if self._count >= self.period else None

    def history(self, count: int = 100) -> list[float]:
        return list(self._history)[-count:]

    def reset(self):
        self._value = None
        self._history.clear()
        self._count = 0

    def is_ready(self) -> bool:
        return self._count >= self.period

    def warmup_needed(self) -> int:
        return self.period
