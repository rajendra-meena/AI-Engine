"""
MarketMind AI — Subscriber Helpers

Convenience functions for subscribing to events and utilities for
building handler functions.

Future modules should use these helpers to register their handlers
with the Event Bus in a consistent way.
"""

from __future__ import annotations

from typing import Any, Callable, Coroutine

from core.event_bus import EventBus, Handler, Event


def subscribe(
    bus: EventBus,
    event_type: str,
    handler: Handler,
    name: str = "",
):
    """
    Register a handler for an event type.

    This is a thin wrapper around EventBus.subscribe() for consistency.
    The handler must be an async function: async def my_handler(event: Event) -> None

    Example:
        subscribe(bus, NEW_CANDLE, on_new_candle, name="my_indicator")
    """
    bus.subscribe(event_type, handler, name=name)


def subscribe_many(
    bus: EventBus,
    event_types: list[str],
    handler: Handler,
    name: str = "",
):
    """
    Register the same handler for multiple event types.

    Useful for a logger or monitor that needs to observe all events.
    """
    for et in event_types:
        bus.subscribe(et, handler, name=name)


def ignore_event(event: Event) -> bool:
    """
    Check if an event should be ignored (e.g. based on payload or source).
    Placeholder for future filtering logic.
    """
    return False


def event_summary(event: Event) -> dict[str, Any]:
    """
    Produce a concise summary of an event for logging or display.
    """
    return {
        "type": event.type,
        "source": event.source,
        "priority": event.priority.value,
        "id": event.id,
        "ts": event.timestamp,
    }
