"""
MarketMind AI — Event Model

The standard event object that flows through the Event Bus.
Every event carries an id, type, timestamp, source, payload, and metadata.

Priority levels allow future modules to signal urgency without the bus
needing to understand the content.

Correlation ID and Trace ID enable request tracing across module boundaries.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventPriority(str, Enum):
    """Priority levels for event queue ordering."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Numeric mapping for queue sorting (lower = higher priority)
_PRIORITY_ORDER = {
    EventPriority.CRITICAL: 0,
    EventPriority.HIGH: 1,
    EventPriority.NORMAL: 2,
    EventPriority.LOW: 3,
}


@dataclass
class Event:
    """
    Universal event object for the MarketMind Event Bus.

    All fields are immutable after creation except for internal use.
    New modules should create events via the publisher helpers.
    """

    type: str
    """Event type string (matches core.events constants)."""

    payload: dict[str, Any] = field(default_factory=dict)
    """Arbitrary data attached to the event. Schema depends on event type."""

    source: str = ""
    """Name of the module or service that created this event."""

    priority: EventPriority = EventPriority.NORMAL
    """Queue priority. HIGH/CRITICAL events are processed before NORMAL/LOW."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    """Unique event identifier (12-char hex)."""

    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(
            timespec="milliseconds"
        )
    )
    """ISO-8601 timestamp of when this event was created."""

    correlation_id: str = ""
    """Links related events together (e.g. a signal detection chain)."""

    trace_id: str = ""
    """Persistent trace across the entire lifecycle (e.g. a trade signal's life)."""

    version: str = "1.0"
    """Event schema version for future schema evolution."""

    # ── Internal (not part of the public event shape) ──

    _created_ns: int = field(
        default_factory=lambda: int(
            datetime.now(timezone.utc).timestamp() * 1_000_000_000
        ),
        repr=False,
    )
    """Nanosecond-precision creation time for performance tracking."""

    def __lt__(self, other: Event) -> bool:
        """
        Sort by priority (CRITICAL first), then by creation time.
        Used by the priority queue internally.
        """
        self_order = _PRIORITY_ORDER.get(self.priority, 2)
        other_order = _PRIORITY_ORDER.get(other.priority, 2)
        if self_order != other_order:
            return self_order < other_order
        return self._created_ns < other._created_ns

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event to a plain dict (for logging, WS broadcast)."""
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "version": self.version,
            "payload": self.payload,
        }
