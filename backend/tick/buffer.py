"""
MarketMind AI — Tick Buffer

Maintains an in-memory buffer of recent ticks per symbol.
No persistence. Memory only. Configurable max per symbol.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

from models.tick import Tick


class TickBuffer:
    """
    Holds recent ticks per symbol.

    Default: last 100 ticks per symbol. Configurable.
    Thread-safe at the method level (no async needed for in-memory ops).

    Usage:
        buffer = TickBuffer(max_ticks=100)
        buffer.add(tick)
        latest = buffer.latest("NIFTY 50")
        recent = buffer.recent("NIFTY 50", 10)
    """

    def __init__(self, max_ticks: int = 100):
        self._max_ticks = max_ticks
        self._buffers: dict[str, deque[Tick]] = {}
        self._latest: dict[str, Tick] = {}

    def add(self, tick: Tick):
        """Add a tick to the buffer. Maintains max_ticks per symbol."""
        sym = tick.symbol
        if sym not in self._buffers:
            self._buffers[sym] = deque(maxlen=self._max_ticks)
            self._latest[sym] = tick
        else:
            self._latest[sym] = tick
        self._buffers[sym].append(tick)

    def latest(self, symbol: str) -> Tick | None:
        """Return the most recent tick for a symbol."""
        return self._latest.get(symbol)

    def recent(self, symbol: str, count: int = 10) -> list[Tick]:
        """Return the last N ticks for a symbol."""
        buf = self._buffers.get(symbol)
        if not buf:
            return []
        return list(buf)[-count:]

    def all_symbols(self) -> dict[str, Tick]:
        """Return latest tick for every tracked symbol."""
        return dict(self._latest)

    def clear_symbol(self, symbol: str):
        """Clear buffer for a specific symbol."""
        self._buffers.pop(symbol, None)
        self._latest.pop(symbol, None)

    def clear_all(self):
        """Clear all tick buffers."""
        self._buffers.clear()
        self._latest.clear()

    def count(self, symbol: str) -> int:
        """Number of buffered ticks for a symbol."""
        buf = self._buffers.get(symbol)
        return len(buf) if buf else 0

    def get_stats(self) -> dict[str, Any]:
        return {
            "tracked_symbols": len(self._buffers),
            "total_ticks": sum(len(b) for b in self._buffers.values()),
            "max_per_symbol": self._max_ticks,
            "latest_symbols": list(self._latest.keys()),
        }
