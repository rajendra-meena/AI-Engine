"""
SuperTrend Indicator

Parameters: ATR period = 10, Multiplier = 3
Formula:
  Basic Band = (high + low) / 2
  Upper Band = Basic Band + (multiplier × ATR)
  Lower Band = Basic Band - (multiplier × ATR)
  Trend = UP if close > prev Upper Band, DOWN if close < prev Lower Band
"""

from dataclasses import dataclass
from typing import Any

from indicators.base import BaseIndicator
from indicators.modules.atr import ATR
from models.candle import Candle


@dataclass
class SuperTrendValue:
    trend: str           # "UP" or "DOWN"
    atr: float
    upper_band: float
    lower_band: float
    price: float
    is_ready: bool = True


class SuperTrend(BaseIndicator):
    name = "supertrend"

    def __init__(self, atr_period: int = 10, multiplier: float = 3.0):
        self.atr_period = atr_period
        self.multiplier = multiplier
        self._atr = ATR(atr_period)
        self._value: SuperTrendValue | None = None
        self._prev_upper: float | None = None
        self._prev_lower: float | None = None
        self._history: list[SuperTrendValue] = []

    def update(self, candle: Candle) -> SuperTrendValue | None:
        atr_val = self._atr.update(candle)
        if atr_val is None:
            return None

        basic = (candle.high + candle.low) / 2.0
        upper = basic + self.multiplier * atr_val
        lower = basic - self.multiplier * atr_val

        if self._prev_upper is None:
            trend = "UP" if candle.close > upper else "DOWN"
        else:
            if candle.close > self._prev_upper:
                trend = "UP"
            elif candle.close < self._prev_lower:
                trend = "DOWN"
            else:
                trend = self._value.trend if self._value else "UP"

            # Band adjustment
            if trend == "UP":
                upper = min(upper, self._prev_upper) if self._prev_upper is not None else upper
            else:
                lower = max(lower, self._prev_lower) if self._prev_lower is not None else lower

        self._prev_upper = upper
        self._prev_lower = lower

        self._value = SuperTrendValue(
            trend=trend,
            atr=atr_val,
            upper_band=round(upper, 2),
            lower_band=round(lower, 2),
            price=candle.close,
        )
        self._history.append(self._value)
        return self._value

    def latest(self) -> SuperTrendValue | None:
        return self._value

    def history(self, count: int = 100) -> list[dict]:
        return [
            {"trend": v.trend, "atr": v.atr, "upper_band": v.upper_band, "lower_band": v.lower_band}
            for v in self._history[-count:]
        ]

    def reset(self):
        self._atr.reset()
        self._value = None
        self._prev_upper = None
        self._prev_lower = None
        self._history.clear()

    def is_ready(self) -> bool:
        return self._value is not None

    def warmup_needed(self) -> int:
        return self.atr_period
