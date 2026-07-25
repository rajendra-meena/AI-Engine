"""
MACD Indicator — Moving Average Convergence Divergence

Standard: 12, 26, 9
Formula: MACD = EMA(12) - EMA(26)
         Signal = EMA(9) of MACD
         Histogram = MACD - Signal
"""

from dataclasses import dataclass
from typing import Any

from indicators.base import BaseIndicator
from indicators.modules.ema import EMA
from models.candle import Candle


@dataclass
class MACDValue:
    macd: float
    signal: float
    histogram: float
    is_ready: bool = True


class MACD(BaseIndicator):
    name = "macd"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self._ema_fast = EMA(fast)
        self._ema_slow = EMA(slow)
        self._ema_signal = EMA(signal)
        self._value: MACDValue | None = None
        self._history: list[MACDValue] = []

    def update(self, candle: Candle) -> MACDValue | None:
        fast_val = self._ema_fast.update(candle)
        slow_val = self._ema_slow.update(candle)

        if fast_val is not None and slow_val is not None:
            macd_line = fast_val - slow_val
            # Feed macd_line into signal EMA using a synthetic candle
            signal_candle = Candle(
                symbol=candle.symbol,
                interval=candle.interval,
                time=candle.time,
                open=macd_line,
                high=macd_line,
                low=macd_line,
                close=macd_line,
                volume=0,
                is_closed=True,
            )
            signal_val = self._ema_signal.update(signal_candle)

            if signal_val is not None:
                self._value = MACDValue(
                    macd=macd_line,
                    signal=signal_val,
                    histogram=macd_line - signal_val,
                )
                self._history.append(self._value)

        return self._value

    def latest(self) -> MACDValue | None:
        return self._value

    def history(self, count: int = 100) -> list[dict]:
        return [
            {"macd": v.macd, "signal": v.signal, "histogram": v.histogram}
            for v in self._history[-count:]
        ]

    def reset(self):
        self._ema_fast.reset()
        self._ema_slow.reset()
        self._ema_signal.reset()
        self._value = None
        self._history.clear()

    def is_ready(self) -> bool:
        return self._value is not None

    def warmup_needed(self) -> int:
        return self.slow + 9  # slow EMA + signal EMA
