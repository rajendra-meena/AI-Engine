"""
MarketMind AI — Market Stream Router

Central dispatcher for all market data events.

Design:
  - Subscribes to NEW_TICK on the Event Bus
  - Maintains a registry of consumer callbacks
  - Each consumer specifies symbol filters, channel filters, and mode
  - Routes matching ticks to the appropriate consumers
  - Tracks routing statistics

Usage:
    router = StreamRouter(event_bus)
    await router.start()

    # A downstream module registers:
    async def my_handler(tick, channel, mode):
        ...
    router.register_consumer("my_module", my_handler, symbols=["NIFTY 50"])

    await router.stop()
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine

from core.event_bus import EventBus, Event
from tick.events import NEW_TICK
from stream.events import (
    STREAM_ROUTER_STARTED,
    STREAM_ROUTER_STOPPED,
    CONSUMER_REGISTERED,
    CONSUMER_REMOVED,
)
from utils.logger import log_info, log_warn, log_error


class StreamMode(str, Enum):
    LIVE = "live"
    REPLAY = "replay"
    ALL = "all"


ConsumerHandler = Callable[[dict[str, Any], str, str], Coroutine[Any, Any, None]]
"""Signature: async handler(payload: dict, channel: str, mode: str) -> None"""


@dataclass
class Consumer:
    """A registered stream consumer with its filter criteria."""
    name: str
    handler: ConsumerHandler
    symbols: set[str] | None = None    # None = all symbols
    channels: set[str] | None = None   # None = all channels
    mode: StreamMode = StreamMode.ALL
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    messages_routed: int = 0
    last_routed_at: str | None = None
    errors: int = 0


@dataclass
class StreamStats:
    """Aggregate routing statistics."""
    total_routed: int = 0
    total_dropped: int = 0
    total_errors: int = 0
    per_channel: dict[str, int] = field(default_factory=dict)
    per_symbol: dict[str, int] = field(default_factory=dict)
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_routed": self.total_routed,
            "total_dropped": self.total_dropped,
            "total_errors": self.total_errors,
            "per_channel": dict(self.per_channel),
            "per_symbol": dict(self.per_symbol),
            "start_time": self.start_time,
        }


class StreamRouter:
    """
    Central dispatcher for market data events.

    Every downstream module registers via register_consumer() instead of
    subscribing directly to the Tick Engine or Event Bus.
    """

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._consumers: dict[str, Consumer] = {}
        self._stats = StreamStats()
        self._running = False

    # ── Lifecycle ──

    async def start(self):
        """Start the router and subscribe to NEW_TICK on the Event Bus."""
        if self._running:
            return
        self._running = True
        self._event_bus.subscribe(NEW_TICK, self._on_new_tick, name="stream_router")
        await self._publish_event(STREAM_ROUTER_STARTED, {"start_time": self._stats.start_time})
        log_info("StreamRouter started")

    async def stop(self):
        """Stop the router."""
        self._running = False
        await self._publish_event(STREAM_ROUTER_STOPPED, {"stats": self._stats.to_dict()})
        log_info("StreamRouter stopped", routed=self._stats.total_routed)

    # ── Consumer management ──

    def register_consumer(
        self,
        name: str,
        handler: ConsumerHandler,
        symbols: list[str] | None = None,
        channels: list[str] | None = None,
        mode: str = "all",
    ) -> bool:
        """
        Register a downstream consumer.

        Args:
            name: Unique consumer name (e.g. "candle_engine", "ai_engine")
            handler: Async callback: async def fn(payload, channel, mode)
            symbols: List of symbols to receive, or None for all
            channels: List of channels to receive, or None for all
            mode: "live", "replay", or "all"

        Returns:
            True if registered, False if name already exists.
        """
        if name in self._consumers:
            log_warn("Consumer already registered", name=name)
            return False

        self._consumers[name] = Consumer(
            name=name,
            handler=handler,
            symbols=set(symbols) if symbols else None,
            channels=set(channels) if channels else None,
            mode=StreamMode(mode),
        )
        log_info("Consumer registered", name=name, symbols=symbols, channels=channels, mode=mode)
        return True

    def unregister_consumer(self, name: str) -> bool:
        """Remove a registered consumer."""
        if name in self._consumers:
            del self._consumers[name]
            log_info("Consumer removed", name=name)
            return True
        return False

    def consumer_count(self) -> int:
        """Number of registered consumers."""
        return len(self._consumers)

    def list_consumers(self) -> list[dict[str, Any]]:
        """List all registered consumers with their stats."""
        return [
            {
                "name": c.name,
                "symbols": list(c.symbols) if c.symbols else "*",
                "channels": list(c.channels) if c.channels else "*",
                "mode": c.mode.value,
                "messages_routed": c.messages_routed,
                "errors": c.errors,
            }
            for c in self._consumers.values()
        ]

    # ── Event Bus handler ──

    async def _on_new_tick(self, event: Event):
        """Called on every NEW_TICK event from the Event Bus."""
        if not self._running:
            return

        payload = event.payload
        symbol = payload.get("symbol", "")
        channel = "market_data"
        mode = StreamMode.LIVE.value

        # Check for replay mode indicator in payload
        if payload.get("source") == "replay_engine":
            mode = StreamMode.REPLAY.value

        self._stats.per_symbol[symbol] = self._stats.per_symbol.get(symbol, 0) + 1
        self._stats.per_channel[channel] = self._stats.per_channel.get(channel, 0) + 1

        # Route to matching consumers
        routed = 0
        for consumer in list(self._consumers.values()):
            if not self._matches_consumer(consumer, symbol, channel, mode):
                self._stats.total_dropped += 1
                continue

            try:
                await consumer.handler(payload, channel, mode)
                consumer.messages_routed += 1
                consumer.last_routed_at = datetime.now(timezone.utc).isoformat()
                routed += 1
            except Exception as e:
                consumer.errors += 1
                self._stats.total_errors += 1
                log_error("StreamRouter consumer error", consumer=consumer.name, error=str(e))

        self._stats.total_routed += routed

    @staticmethod
    def _matches_consumer(consumer: Consumer, symbol: str, channel: str, mode: str) -> bool:
        """Check if a message should be routed to a consumer based on its filters."""
        # Mode filter
        if consumer.mode != StreamMode.ALL:
            if consumer.mode.value != mode:
                return False

        # Symbol filter
        if consumer.symbols is not None and symbol not in consumer.symbols:
            return False

        # Channel filter
        if consumer.channels is not None and channel not in consumer.channels:
            return False

        return True

    # ── Status ──

    def get_stats(self) -> dict[str, Any]:
        """Return routing statistics."""
        s = self._stats.to_dict()
        s["running"] = self._running
        s["consumer_count"] = len(self._consumers)
        return s

    # ── Internal ──

    async def _publish_event(self, event_type: str, payload: dict):
        event = Event(type=event_type, source="stream_router", payload=payload)
        await self._event_bus.publish(event)
