"""
SMA Indicator — Simple Moving Average

Standard periods: 20, 50, 200
Formula: SMA = sum(closes[-N:]) / N
"""

from collections import deque
from typing import Any

from indicators.base import BaseIndicator
from models.candle import Candle


class SMA(BaseIndicator):
    name = "sma"

    def __init__(self, period: int = 20):
        self.period = period
        self._prices: deque[float] = deque(maxlen=period)
        self._value: float | None = None
        self._history: deque[float] = deque(maxlen=1000)
        self._sum = 0.0

    def update(self, candle: Candle) -> float | None:
        price = candle.close
        if len(self._prices) == self.period:
            self._sum -= self._prices[0]
        self._prices.append(price)
        self._sum += price

        if len(self._prices) == self.period:
            self._value = self._sum / self.period
            self._history.append(self._value)
        return self._value

    def latest(self) -> float | None:
        return self._value

    def history(self, count: int = 100) -> list[float]:
        return list(self._history)[-count:]

    def reset(self):
        self._prices.clear()
        self._history.clear()
        self._value = None
        self._sum = 0.0

    def is_ready(self) -> bool:
        return self._value is not None

    def warmup_needed(self) -> int:
        return self.period
