"""
ATR Indicator — Average True Range

Period: 14
Formula: TR = max(high - low, |high - prev_close|, |low - prev_close|)
         ATR = EMA of TR
"""

from collections import deque
from typing import Any

from indicators.base import BaseIndicator
from models.candle import Candle


class ATR(BaseIndicator):
    name = "atr"

    def __init__(self, period: int = 14):
        self.period = period
        self._prev_close: float | None = None
        self._trs: deque[float] = deque(maxlen=period)
        self._atr: float | None = None
        self._history: deque[float] = deque(maxlen=1000)
        self._count = 0

    def update(self, candle: Candle) -> float | None:
        high, low, close = candle.high, candle.low, candle.close
        self._count += 1

        if self._prev_close is None:
            tr = high - low
        else:
            tr = max(
                high - low, abs(high - self._prev_close), abs(low - self._prev_close)
            )

        self._prev_close = close

        if self._atr is None:
            self._trs.append(tr)
            if len(self._trs) == self.period:
                self._atr = sum(self._trs) / self.period
                self._history.append(self._atr)
        else:
            self._atr = (self._atr * (self.period - 1) + tr) / self.period
            self._history.append(self._atr)

        return self._atr

    def latest(self) -> float | None:
        return self._atr

    def history(self, count: int = 100) -> list[float]:
        return list(self._history)[-count:]

    def reset(self):
        self._prev_close = None
        self._trs.clear()
        self._atr = None
        self._history.clear()
        self._count = 0

    def is_ready(self) -> bool:
        return self._atr is not None

    def warmup_needed(self) -> int:
        return self.period
