"""
MarketMind AI — Tick Engine

Centralized engine that receives, normalizes, buffers, and publishes market ticks.

Data flow:
    Producer (ReplayEngine / LiveMarketDataEngine)
        │
        ▼
    TickEngine.publish_tick()
        │
        ├── Convert to Tick model (if not already)
        ├── Store in TickBuffer
        ├── Publish NEW_TICK event to Event Bus
        ├── Update statistics
        └── Return sequence number

    All future modules subscribe to NEW_TICK on the Event Bus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from models.tick import Tick
from tick.buffer import TickBuffer
from tick.events import (
    NEW_TICK,
    TICK_UPDATED,
    STREAM_STARTED,
    STREAM_STOPPED,
)
from core.event_bus import EventBus
from core.event_model import Event
from utils.logger import log_info, log_warn


@dataclass
class TickStats:
    """Aggregate tick processing statistics."""
    total_ticks_received: int = 0
    total_events_published: int = 0
    total_errors: int = 0
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_tick_time: str | None = None
    last_tick_symbol: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_ticks_received": self.total_ticks_received,
            "total_events_published": self.total_events_published,
            "total_errors": self.total_errors,
            "start_time": self.start_time,
            "last_tick_time": self.last_tick_time,
            "last_tick_symbol": self.last_tick_symbol,
        }


class TickEngine:
    """
    THE single source of market ticks in the application.

    Usage:
        engine = TickEngine(event_bus)
        await engine.start()

        # Producers call:
        await engine.publish_tick(Tick(symbol="NIFTY 50", price=24500, ...))

        # Consumers query:
        latest = engine.latest_tick("NIFTY 50")
    """

    def __init__(self, event_bus: EventBus, max_buffer: int = 100):
        self._event_bus = event_bus
        self._buffer = TickBuffer(max_ticks=max_buffer)
        self._stats = TickStats()
        self._sequence: int = 0
        self._running = False

    # ── Lifecycle ──

    async def start(self):
        """Start the tick engine."""
        if self._running:
            return
        self._running = True
        await self._publish_event(STREAM_STARTED, {
            "start_time": self._stats.start_time,
            "max_buffer": self._buffer.get_stats()["max_per_symbol"],
        })
        log_info("TickEngine started")

    async def stop(self):
        """Stop the tick engine."""
        self._running = False
        await self._publish_event(STREAM_STOPPED, {"stats": self._stats.to_dict()})
        log_info("TickEngine stopped", ticks=self._stats.total_ticks_received)

    # ── Publishing ──

    async def publish_tick(self, tick: Tick) -> int:
        """
        Publish a tick into the engine.

        This is the ONLY method producers should call.

        Args:
            tick: A Tick object (from models/tick.py)

        Returns:
            Sequence number for this tick (monotonically increasing).

        The tick is:
            1. Stored in the tick buffer
            2. Published as a NEW_TICK event on the Event Bus
            3. Tracked in statistics
        """
        if not self._running:
            log_warn("TickEngine not running, dropping tick", symbol=tick.symbol)
            return -1

        self._sequence += 1

        # Store in buffer
        self._buffer.add(tick)

        # Update stats
        self._stats.total_ticks_received += 1
        self._stats.last_tick_time = (
            tick.timestamp.isoformat(timespec="milliseconds")
            if hasattr(tick.timestamp, "isoformat")
            else str(tick.timestamp)
        )
        self._stats.last_tick_symbol = tick.symbol

        # Publish event
        await self._publish_event(NEW_TICK, {
            "sequence": self._sequence,
            "symbol": tick.symbol,
            "price": tick.price,
            "timestamp": self._stats.last_tick_time,
            "volume": tick.volume,
            "provider": tick.provider,
        })

        return self._sequence

    # ─── Queries ──

    def latest_tick(self, symbol: str) -> Tick | None:
        """Return the most recent tick for a symbol."""
        return self._buffer.latest(symbol)

    def latest_ticks(self) -> dict[str, Tick]:
        """Return latest tick for every symbol."""
        return self._buffer.all_symbols()

    def recent_ticks(self, symbol: str, count: int = 10) -> list[Tick]:
        """Return the last N ticks for a symbol."""
        return self._buffer.recent(symbol, count)

    # ── Status ──

    def get_stats(self) -> dict[str, Any]:
        """Return engine + buffer statistics."""
        stats = self._stats.to_dict()
        stats["sequence"] = self._sequence
        stats["running"] = self._running
        stats["buffer"] = self._buffer.get_stats()
        return stats

    def health(self) -> dict[str, Any]:
        """Quick health check."""
        return {
            "running": self._running,
            "last_tick_time": self._stats.last_tick_time,
            "total_ticks": self._stats.total_ticks_received,
        }

    # ── Helpers ──

    async def _publish_event(self, event_type: str, payload: dict):
        event = Event(
            type=event_type,
            source="tick_engine",
            payload=payload,
        )
        await self._event_bus.publish(event)
        self._stats.total_events_published += 1
