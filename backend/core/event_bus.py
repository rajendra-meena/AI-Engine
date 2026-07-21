"""
MarketMind AI — Async Event Bus

The communication backbone for the entire application.

Design:
  - Single in-process asyncio.Queue with priority support
  - Publishers call publish() — non-blocking (put into queue)
  - A background dispatcher task reads from the queue and fans out to subscribers
  - Each subscriber runs in its own asyncio task — one failure never blocks others
  - All monitoring and stats are internal (exposed via get_stats())

Usage:
    bus = EventBus()
    bus.subscribe("new_candle", my_handler)
    await bus.start()           # starts the dispatcher background task
    await bus.publish(Event(type="new_candle", ...))
    await bus.stop()            # graceful shutdown

The bus is a singleton inside the app context. Create it once in main.py
and pass it to modules that need to publish or subscribe.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from core.event_model import Event, EventPriority
from utils.logger import log_info, log_warn, log_error


# Type alias: an async callable that accepts an Event
Handler = Callable[[Event], Coroutine[Any, Any, None]]


@dataclass
class SubscriberInfo:
    """Tracks a registered subscriber."""
    handler: Handler
    event_type: str
    name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EventBus:
    """
    Lightweight in-process async event bus using asyncio.Queue.

    This is NOT a message broker — no Redis, no Kafka, no persistence.
    It simply transports events between in-memory modules within the same process.
    """

    def __init__(self, max_queue_size: int = 1000):
        self._queue: asyncio.Queue[Event] = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._subscribers: dict[str, list[SubscriberInfo]] = {}  # event_type → handlers
        self._dispatcher_task: asyncio.Task | None = None
        self._running = False
        self._max_queue_size = max_queue_size

        # ── Internal stats ──
        self._total_published: int = 0
        self._total_dispatched: int = 0
        self._total_errors: int = 0
        self._total_dropped: int = 0
        self._total_processing_time_ns: int = 0

    # ── Lifecycle ──

    async def start(self):
        """Start the background dispatcher. Called once on app startup."""
        if self._running:
            log_warn("EventBus already running")
            return
        self._running = True
        self._dispatcher_task = asyncio.create_task(self._dispatch_loop(), name="eventbus-dispatcher")
        log_info("EventBus started", max_queue_size=self._max_queue_size)

    async def stop(self):
        """Gracefully stop the dispatcher. Drains remaining events."""
        self._running = False
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
            try:
                await self._dispatcher_task
            except asyncio.CancelledError:
                pass
            self._dispatcher_task = None
        log_info("EventBus stopped", remaining=self._queue.qsize())

    # ── Publishing ──

    async def publish(self, event: Event) -> bool:
        """
        Publish an event to the bus. Non-blocking insert into the queue.

        Returns True if published, False if the queue was full (event dropped).
        """
        if not self._running:
            log_warn("EventBus not running, dropping event", type=event.type, id=event.id)
            self._total_dropped += 1
            return False

        try:
            self._queue.put_nowait(event)
            self._total_published += 1
            return True
        except asyncio.QueueFull:
            self._total_dropped += 1
            log_warn("EventBus queue full, dropping event", type=event.type, id=event.id, queue_size=self._queue.qsize())
            return False

    # ── Subscription ──

    def subscribe(self, event_type: str, handler: Handler, name: str = ""):
        """
        Register a handler for a specific event type.

        The handler must be an async function that accepts a single Event argument.
        Multiple handlers can subscribe to the same event type — all will be called.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        info = SubscriberInfo(
            handler=handler,
            event_type=event_type,
            name=name or handler.__name__,
        )
        self._subscribers[event_type].append(info)
        log_info("Subscriber registered", event_type=event_type, handler=info.name)

    def unsubscribe(self, event_type: str, handler: Handler):
        """Remove a previously registered handler."""
        if event_type not in self._subscribers:
            return
        before = len(self._subscribers[event_type])
        self._subscribers[event_type] = [
            s for s in self._subscribers[event_type]
            if s.handler is not handler
        ]
        removed = before - len(self._subscribers[event_type])
        if removed:
            log_info("Subscriber unsubscribed", event_type=event_type, handler=handler.__name__)

    # ── Dispatch ──

    async def _dispatch_loop(self):
        """
        Background loop: reads events from the priority queue and fans out
        to all subscribers for that event type. Each subscriber runs in its
        own task so a slow/failing handler never blocks others.
        """
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue  # No event within 500ms — loop back and check _running

            await self._dispatch_to_subscribers(event)
            self._queue.task_done()
            self._total_dispatched += 1

    async def _dispatch_to_subscribers(self, event: Event):
        """Fan out an event to all handlers registered for its type."""
        handlers = self._subscribers.get(event.type, [])
        if not handlers:
            return  # No subscribers for this event type

        start_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
        tasks = []
        for sub in handlers:
            task = asyncio.create_task(
                self._safe_call_handler(sub, event),
                name=f"evt-{event.id[:6]}-{sub.name}",
            )
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        elapsed_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000) - start_ns
        self._total_processing_time_ns += elapsed_ns

    async def _safe_call_handler(self, sub: SubscriberInfo, event: Event):
        """
        Call a single handler, catching and logging any exception.
        One failing handler never crashes other handlers or the bus.
        """
        try:
            await sub.handler(event)
        except Exception as e:
            self._total_errors += 1
            log_error(
                "Event handler error",
                handler=sub.name,
                event_type=event.type,
                event_id=event.id,
                error=str(e),
            )

    # ── Monitoring ──

    def get_stats(self) -> dict[str, Any]:
        """Return internal bus statistics (for monitoring/logging)."""
        total_handlers = sum(len(h) for h in self._subscribers.values())
        avg_time_ns = 0
        if self._total_dispatched > 0:
            avg_time_ns = self._total_processing_time_ns // self._total_dispatched

        return {
            "queue_size": self._queue.qsize(),
            "max_queue_size": self._max_queue_size,
            "total_published": self._total_published,
            "total_dispatched": self._total_dispatched,
            "total_errors": self._total_errors,
            "total_dropped": self._total_dropped,
            "avg_processing_time_ns": avg_time_ns,
            "subscriber_count": total_handlers,
            "event_type_count": len(self._subscribers),
            "running": self._running,
        }

    def get_subscriber_summary(self) -> list[dict[str, Any]]:
        """List all registered subscribers (for debugging)."""
        result = []
        for event_type, subs in self._subscribers.items():
            for sub in subs:
                result.append({
                    "event_type": event_type,
                    "handler": sub.name,
                    "created_at": sub.created_at,
                })
        return result
