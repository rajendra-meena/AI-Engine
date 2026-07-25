"""
MarketMind AI — Candle Builder

Internal mutable state for constructing a single OHLCV candle from ticks.
Releases immutable Candle instances when closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from models.candle import Candle


@dataclass
class ActiveCandle:
    """
    Mutable candle state that updates with each tick.

    When the candle is closed, to_candle() produces an immutable Candle.
    """

    symbol: str = ""
    interval: str = ""
    open_time: str = ""  # ISO-8601 start time of this candle
    open: float = 0.0
    high: float = 0.0
    low: float = float("inf")
    close: float = 0.0
    volume: float = 0.0
    tick_count: int = 0
    first_tick_time: str = ""
    last_tick_time: str = ""

    def update(self, price: float, volume: float, timestamp: str):
        """Update OHLCV with a new tick price."""
        if self.tick_count == 0:
            self.open = price
            self.open_time = timestamp

        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += volume
        self.tick_count += 1
        self.last_tick_time = timestamp

    def to_candle(self) -> Candle:
        """Produce an immutable Candle from this mutable state."""
        return Candle(
            symbol=self.symbol,
            interval=self.interval,
            time=self.open_time,
            open=self.open,
            high=self.high,
            low=self.low if self.low != float("inf") else self.open,
            close=self.close,
            volume=self.volume,
            is_closed=True,
        )

    def to_active_dict(self) -> dict[str, Any]:
        """Return snapshot as dict for inspection."""
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "open_time": self.open_time,
            "open": self.open,
            "high": self.high,
            "low": self.low if self.low != float("inf") else self.open,
            "close": self.close,
            "volume": self.volume,
            "tick_count": self.tick_count,
            "last_tick_time": self.last_tick_time,
        }
