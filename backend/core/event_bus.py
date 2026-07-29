"""
MarketMind AI — Async Event Bus with priority, coalescing, and health metrics.

Design:
  - asyncio.PriorityQueue — events ordered by priority level
  - Coalescible event types (candle_updated, indicator_updated, etc.)
    retain only the latest event per (symbol, timeframe, type) key
  - CRITICAL events (candle_closed, execution, kill_switch) are never dropped
  - Per-event-type drop counters for diagnostics
  - Health status: HEALTHY / DEGRADED / CRITICAL
  - Execution safety gate: block new paper execution when data integrity is unsafe

Priority levels (from core.event_model.EventPriority):
  CRITICAL=0 — candle_closed, execution, position, risk, kill_switch
  HIGH=1     — candle_started, structure_updated, pattern_detected
  NORMAL=2   — indicator_updated, sr_updated, candle_updated
  LOW=3      — live_ui_update, diagnostics

Coalescible types (keep most recent per key):
  - candle_updated
  - indicator_updated
  - support_resistance_updated
  - live_ui_update
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from core.event_model import Event, EventPriority
from utils.logger import log_info, log_warn, log_error

Handler = Callable[[Event], Coroutine[Any, Any, None]]

# Event types that are CRITICAL — must never be dropped
CRITICAL_EVENT_TYPES = {
    "candle_closed", "ai_decision_created", "option_plan_created",
    "risk_result", "execution_request", "position_opened",
    "premium_tick", "position_closed", "kill_switch",
}

# Event types that are coalescible — retain only latest per (sym, tf, type)
COALESCIBLE_EVENT_TYPES = {
    "candle_updated", "indicator_updated", "support_resistance_updated",
    "live_ui_update",
}

# Health thresholds
HEALTHY_MAX_UTIL_PCT = 60
DEGRADED_MAX_UTIL_PCT = 80
BLOCK_EXECUTION_UTIL_PCT = 95
HEALTH_CHECK_INTERVAL_S = 5


def _coalesce_key(event: Event) -> str:
    """Build a dedup key for coalescible events: type:symbol:timeframe."""
    sym = event.payload.get("symbol", "")
    tf = event.payload.get("interval", event.payload.get("timeframe", ""))
    return f"{event.type}:{sym}:{tf}"


@dataclass
class SubscriberInfo:
    """Tracks a registered subscriber."""
    handler: Handler
    event_type: str
    name: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class EventBus:
    """
    In-process async event bus with priority ordering, coalescing, and health.

    CRITICAL events are never dropped — if the queue is full, publish()
    blocks until space is available.
    """

    def __init__(self, max_queue_size: int = 5000):
        self._evt_queue: asyncio.PriorityQueue[tuple] = asyncio.PriorityQueue(
            maxsize=max_queue_size
        )
        self._subscribers: dict[str, list[SubscriberInfo]] = {}
        self._dispatcher_task: asyncio.Task | None = None
        self._health_task: asyncio.Task | None = None
        self._running = False
        self._max_queue_size = max_queue_size

        # ── Coalescing state: coalesce_key → latest event ──
        self._coalesce_cache: dict[str, Event] = {}
        self._total_coalesced: int = 0

        # ── Stats ──
        self._total_published: int = 0
        self._total_dispatched: int = 0
        self._total_errors: int = 0
        self._total_dropped: int = 0
        self._critical_dropped: int = 0
        self._drop_counts: dict[str, int] = {}
        self._total_processing_time_ns: int = 0
        self._health_status: str = "HEALTHY"
        self._events_published_rate: float = 0.0
        self._events_processed_rate: float = 0.0
        # Track when the most recent critical drop happened — used by safety gate
        self._last_critical_drop_at: float = 0.0
        # Safety gate: ignore drops older than this many seconds
        self._critical_drop_cooldown_s: float = 15.0

    # ── Lifecycle ──

    async def start(self, reset_counters: bool = True):
        """Start the background dispatcher. Called once on app startup.

        When reset_counters=True (default), all internal counters including
        critical_events_dropped are reset — this should be used on engine restart
        to clear historical drops from a previous session.
        """
        if self._running:
            log_warn("EventBus already running")
            return
        if reset_counters:
            self._total_published = 0
            self._total_dispatched = 0
            self._total_errors = 0
            self._total_dropped = 0
            self._critical_dropped = 0
            self._drop_counts = {}
            self._total_coalesced = 0
            self._total_processing_time_ns = 0
            self._health_status = "HEALTHY"
            self._coalesce_cache.clear()
        self._running = True
        self._dispatcher_task = asyncio.create_task(
            self._dispatch_loop(), name="eventbus-dispatcher"
        )
        self._health_task = asyncio.create_task(
            self._health_check_loop(), name="eventbus-health"
        )
        log_info("EventBus started", max_queue_size=self._max_queue_size)

    async def stop(self):
        """Gracefully stop the dispatcher. Drains remaining events."""
        self._running = False
        for task in [self._health_task, self._dispatcher_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._dispatcher_task = None
        self._health_task = None
        log_info("EventBus stopped", remaining=self._evt_queue.qsize())

    # ── Publishing ──

    async def publish(self, event: Event) -> bool:
        """
        Publish an event. For coalescible types, retains only the latest
        per (symbol, timeframe). For CRITICAL types, blocks if queue is full.
        Returns True if the event was queued for dispatch.
        """
        if not self._running:
            log_warn("EventBus not running, dropping event", type=event.type, id=event.id)
            self._total_dropped += 1
            self._drop_counts[event.type] = self._drop_counts.get(event.type, 0) + 1
            return False

        # Coalescing: for high-frequency event types, keep only the latest per key
        if event.type in COALESCIBLE_EVENT_TYPES:
            key = _coalesce_key(event)
            if key in self._coalesce_cache:
                self._total_coalesced += 1
                # Replace the cached event — no queue insertion
                self._coalesce_cache[key] = event
                self._total_published += 1
                return True
            else:
                # First event for this key — insert into queue AND cache
                self._coalesce_cache[key] = event

        # Compute priority order (lower number = higher priority)
        priority_map = {
            EventPriority.CRITICAL: 0,
            EventPriority.HIGH: 1,
            EventPriority.NORMAL: 2,
            EventPriority.LOW: 3,
        }
        prio = priority_map.get(event.priority, 2)

        self._total_published += 1

        # For CRITICAL events, block until space is available (never drop)
        if event.type in CRITICAL_EVENT_TYPES:
            try:
                await asyncio.wait_for(self._evt_queue.put((prio, event)), timeout=10.0)
                return True
            except asyncio.TimeoutError:
                self._critical_dropped += 1
                self._total_dropped += 1
                self._last_critical_drop_at = time.time()
                self._drop_counts[event.type] = self._drop_counts.get(event.type, 0) + 1
                log_error("EventBus: CRITICAL event dropped after timeout",
                          type=event.type, id=event.id, queue_size=self._evt_queue.qsize())
                return False

        # Non-critical events: non-blocking insert
        try:
            self._evt_queue.put_nowait((prio, event))
            return True
        except asyncio.QueueFull:
            self._total_dropped += 1
            self._drop_counts[event.type] = self._drop_counts.get(event.type, 0) + 1
            log_warn("EventBus queue full, dropping event",
                     type=event.type, id=event.id, queue_size=self._evt_queue.qsize())
            return False

    # ── Subscription ──

    def subscribe(self, event_type: str, handler: Handler, name: str = ""):
        """Register a handler for a specific event type."""
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
            s for s in self._subscribers[event_type] if s.handler is not handler
        ]
        removed = before - len(self._subscribers[event_type])

    # ── Dispatch ──

    async def _dispatch_loop(self):
        """
        Background loop: reads events from the priority queue and fans out.
        Coalesced events are injected before the next queue read.
        """
        while self._running:
            try:
                prio, event = await asyncio.wait_for(self._evt_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                # Flush any coalesced events into the queue
                await self._flush_coalesced()
                continue

            # Flush coalesced events periodically to keep them moving
            if self._coalesce_cache:
                await self._flush_coalesced()

            await self._dispatch_to_subscribers(event)
            self._evt_queue.task_done()
            self._total_dispatched += 1

    async def _flush_coalesced(self):
        """Push all currently coalesced events into the queue as NORMAL priority."""
        if not self._coalesce_cache:
            return
        events = list(self._coalesce_cache.values())
        self._coalesce_cache.clear()
        for evt in events:
            try:
                self._evt_queue.put_nowait((2, evt))  # NORMAL priority
            except asyncio.QueueFull:
                self._total_dropped += 1
                self._drop_counts[evt.type] = self._drop_counts.get(evt.type, 0) + 1

    async def _dispatch_to_subscribers(self, event: Event):
        """Fan out an event to all handlers registered for its type."""
        handlers = self._subscribers.get(event.type, [])
        if not handlers:
            return

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
        elapsed_ns = (
            int(datetime.now(timezone.utc).timestamp() * 1_000_000_000) - start_ns
        )
        self._total_processing_time_ns += elapsed_ns

    async def _safe_call_handler(self, sub: SubscriberInfo, event: Event):
        """Call a single handler, catching/logging any exception."""
        try:
            await sub.handler(event)
        except Exception as e:
            self._total_errors += 1
            log_error("Event handler error", handler=sub.name,
                      event_type=event.type, event_id=event.id, error=str(e))

    # ── Health check loop ──

    async def _health_check_loop(self):
        """Periodically compute health status from queue metrics."""
        import math
        while self._running:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL_S)
                qsize = self._evt_queue.qsize()
                util_pct = (qsize / max(self._max_queue_size, 1)) * 100.0

                if self._critical_dropped > 0:
                    self._health_status = "CRITICAL"
                elif util_pct > DEGRADED_MAX_UTIL_PCT:
                    self._health_status = "DEGRADED"
                elif util_pct > HEALTHY_MAX_UTIL_PCT:
                    self._health_status = "DEGRADED"
                else:
                    self._health_status = "HEALTHY"
            except asyncio.CancelledError:
                return
            except Exception:
                pass

    # ── Monitoring ──

    def can_execute_safely(self) -> tuple[bool, str]:
        """
        Execution safety gate:
        - Only blocks if critical events were dropped within the cooldown window
        - Drops from more than _critical_drop_cooldown_s seconds ago are ignored
        - queue > 95% full → block regardless

        This prevents warmup drops from permanently blocking all execution.
        Returns (safe: bool, reason: str).
        """
        # Check for recent critical drops (within cooldown window)
        if self._critical_dropped > 0 and self._last_critical_drop_at > 0:
            elapsed = time.time() - self._last_critical_drop_at
            if elapsed < self._critical_drop_cooldown_s:
                return False, (
                    f"EVENTBUS_DATA_INTEGRITY_UNSAFE: "
                    f"{self._critical_dropped} critical events dropped "
                    f"{elapsed:.0f}s ago"
                )

        # Check queue utilization
        qsize = self._evt_queue.qsize()
        util_pct = (qsize / max(self._max_queue_size, 1)) * 100.0
        if util_pct > BLOCK_EXECUTION_UTIL_PCT:
            return False, f"EVENTBUS_QUEUE_OVERLOAD: {util_pct:.0f}% utilization"

        return True, ""

    def get_health_status(self) -> str:
        return self._health_status

    def reset_counters(self):
        """Reset all counters including critical drops.
        Called on engine start to clear historical drops from warmup periods."""
        self._total_published = 0
        self._total_dispatched = 0
        self._total_errors = 0
        self._total_dropped = 0
        self._critical_dropped = 0
        self._drop_counts = {}
        self._total_coalesced = 0
        self._total_processing_time_ns = 0
        self._health_status = "HEALTHY"
        self._last_critical_drop_at = 0.0

    def get_stats(self) -> dict[str, Any]:
        """Return internal bus statistics."""
        total_handlers = sum(len(h) for h in self._subscribers.values())
        avg_time_ns = 0
        if self._total_dispatched > 0:
            avg_time_ns = self._total_processing_time_ns // self._total_dispatched
        qsize = self._evt_queue.qsize()
        util_pct = round((qsize / max(self._max_queue_size, 1)) * 100.0, 1)

        return {
            "queue_size": qsize,
            "max_queue_size": self._max_queue_size,
            "queue_utilization_pct": util_pct,
            "total_published": self._total_published,
            "total_dispatched": self._total_dispatched,
            "total_errors": self._total_errors,
            "total_dropped": self._total_dropped,
            "critical_events_dropped": self._critical_dropped,
            "events_coalesced_total": self._total_coalesced,
            "avg_processing_time_ns": avg_time_ns,
            "subscriber_count": total_handlers,
            "event_type_count": len(self._subscribers),
            "running": self._running,
            "health_status": self._health_status,
            "drop_counts_by_type": dict(self._drop_counts),
        }

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
                result.append(
                    {
                        "event_type": event_type,
                        "handler": sub.name,
                        "created_at": sub.created_at,
                    }
                )
        return result
