"""
MarketMind AI — Candle Buffer

Rolling history of completed candles per symbol and timeframe.
"""

from collections import deque
from typing import Any

from models.candle import Candle


class CandleBuffer:
    """
    Holds completed candles per (symbol, interval) pair.

    Default: last 1000 completed candles. Configurable.
    """

    def __init__(self, max_candles: int = 1000):
        self._max = max_candles
        self._buffers: dict[tuple[str, str], deque[Candle]] = {}

    def add(self, candle: Candle):
        """Store a completed candle."""
        key = (candle.symbol, candle.interval)
        if key not in self._buffers:
            self._buffers[key] = deque(maxlen=self._max)
        self._buffers[key].append(candle)

    def history(self, symbol: str, interval: str, count: int = 100) -> list[Candle]:
        """Return last N completed candles for a symbol/interval."""
        key = (symbol, interval)
        buf = self._buffers.get(key)
        if not buf:
            return []
        return list(buf)[-count:]

    def latest(self, symbol: str, interval: str) -> Candle | None:
        """Most recent completed candle for a symbol/interval."""
        key = (symbol, interval)
        buf = self._buffers.get(key)
        if not buf:
            return None
        return buf[-1]

    def count(self, symbol: str, interval: str) -> int:
        key = (symbol, interval)
        buf = self._buffers.get(key)
        return len(buf) if buf else 0

    def clear_symbol(self, symbol: str):
        keys = [k for k in self._buffers if k[0] == symbol]
        for k in keys:
            del self._buffers[k]

    def clear_all(self):
        self._buffers.clear()

    def get_stats(self) -> dict[str, Any]:
        symbols = set(k[0] for k in self._buffers)
        return {
            "total_keys": len(self._buffers),
            "total_candles": sum(len(b) for b in self._buffers.values()),
            "unique_symbols": len(symbols),
            "max_per_key": self._max,
        }
