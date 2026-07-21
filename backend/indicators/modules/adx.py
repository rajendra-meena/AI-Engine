"""
ADX Indicator — Average Directional Index

Period: 14
Measures trend strength (not direction).
Values > 25 = trending, < 20 = ranging.
"""

from collections import deque
from typing import Any

from indicators.base import BaseIndicator
from models.candle import Candle


class ADX(BaseIndicator):
    name = "adx"

    def __init__(self, period: int = 14):
        self.period = period
        self._prev_candle: Candle | None = None
        self._tr_sum = 0.0
        self._plus_dm_sum = 0.0
        self._minus_dm_sum = 0.0
        self._trs: deque[float] = deque(maxlen=period)
        self._plus_dms: deque[float] = deque(maxlen=period)
        self._minus_dms: deque[float] = deque(maxlen=period)
        self._dx_values: deque[float] = deque(maxlen=period)
        self._value: float | None = None
        self._history: list[float] = []
        self._count = 0

    def update(self, candle: Candle) -> float | None:
        self._count += 1

        if self._prev_candle is None:
            self._prev_candle = candle
            return None

        high, low = candle.high, candle.low
        prev_high = self._prev_candle.high
        prev_low = self._prev_candle.low
        prev_close = self._prev_candle.close

        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        up_move = high - prev_high
        down_move = prev_low - low
        plus_dm = up_move if up_move > down_move and up_move > 0 else 0.0
        minus_dm = down_move if down_move > up_move and down_move > 0 else 0.0

        self._trs.append(tr)
        self._plus_dms.append(plus_dm)
        self._minus_dms.append(minus_dm)

        if len(self._trs) >= self.period:
            atr = sum(self._trs) / min(len(self._trs), self.period)
            plus_di = sum(self._plus_dms) / min(len(self._plus_dms), self.period) / atr * 100 if atr > 0 else 0
            minus_di = sum(self._minus_dms) / min(len(self._minus_dms), self.period) / atr * 100 if atr > 0 else 0
            dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0

            self._dx_values.append(dx)

            if len(self._dx_values) >= self.period:
                self._value = sum(self._dx_values) / len(self._dx_values)
                self._history.append(self._value)

        self._prev_candle = candle
        return self._value

    def latest(self) -> float | None:
        return self._value

    def history(self, count: int = 100) -> list[float]:
        return self._history[-count:]

    def reset(self):
        self._prev_candle = None
        self._trs.clear()
        self._plus_dms.clear()
        self._minus_dms.clear()
        self._dx_values.clear()
        self._value = None
        self._history.clear()
        self._count = 0

    def is_ready(self) -> bool:
        return self._value is not None

    def warmup_needed(self) -> int:
        return self.period * 2
