"""
RSI Indicator — Relative Strength Index

Period: 14
Formula: RSI = 100 - 100 / (1 + RS)
Where: RS = avg_gain / avg_loss over N periods
"""

from collections import deque
from typing import Any

from indicators.base import BaseIndicator
from models.candle import Candle


class RSI(BaseIndicator):
    name = "rsi"

    def __init__(self, period: int = 14):
        self.period = period
        self._prev_close: float | None = None
        self._gains: deque[float] = deque(maxlen=period)
        self._losses: deque[float] = deque(maxlen=period)
        self._avg_gain: float | None = None
        self._avg_loss: float | None = None
        self._value: float | None = None
        self._history: deque[float] = deque(maxlen=1000)
        self._count = 0

    def update(self, candle: Candle) -> float | None:
        price = candle.close
        if self._prev_close is not None:
            diff = price - self._prev_close
            gain = diff if diff > 0 else 0.0
            loss = -diff if diff < 0 else 0.0

            if self._avg_gain is None:
                self._gains.append(gain)
                self._losses.append(loss)
                if len(self._gains) == self.period:
                    self._avg_gain = sum(self._gains) / self.period
                    self._avg_loss = sum(self._losses) / self.period
                    self._compute_rsi()
            else:
                self._avg_gain = (
                    self._avg_gain * (self.period - 1) + gain
                ) / self.period
                self._avg_loss = (
                    self._avg_loss * (self.period - 1) + loss
                ) / self.period
                self._compute_rsi()

        self._prev_close = price
        self._count += 1
        return self._value

    def _compute_rsi(self):
        if self._avg_loss == 0:
            self._value = 100.0
        else:
            rs = self._avg_gain / self._avg_loss
            self._value = 100.0 - 100.0 / (1.0 + rs)
        self._history.append(self._value)

    def latest(self) -> float | None:
        return self._value

    def history(self, count: int = 100) -> list[float]:
        return list(self._history)[-count:]

    def reset(self):
        self._prev_close = None
        self._gains.clear()
        self._losses.clear()
        self._avg_gain = None
        self._avg_loss = None
        self._value = None
        self._history.clear()
        self._count = 0

    def is_ready(self) -> bool:
        return self._value is not None

    def warmup_needed(self) -> int:
        return self.period + 1
