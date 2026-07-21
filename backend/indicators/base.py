"""
MarketMind AI — Base Indicator Interface

Every indicator module must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from models.candle import Candle


class BaseIndicator(ABC):
    name: str = "base"

    @abstractmethod
    def update(self, candle: Candle) -> Any:
        """Process a new closed candle. Returns latest value or None."""
        ...

    @abstractmethod
    def latest(self) -> Any:
        """Return the most recent computed value or None if not ready."""
        ...

    @abstractmethod
    def history(self, count: int = 100) -> list[Any]:
        """Return last N values."""
        ...

    @abstractmethod
    def reset(self):
        """Clear all state."""
        ...

    @abstractmethod
    def is_ready(self) -> bool:
        """True if the indicator has enough data to compute a value."""
        ...

    @abstractmethod
    def warmup_needed(self) -> int:
        """Number of candles needed before producing a value."""
        ...
