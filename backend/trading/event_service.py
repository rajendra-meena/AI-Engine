"""
Real-time Event Service — Connects trade lifecycle events to WebSocket gateway.

Bridges:
  Trade Lifecycle Manager → Event Bus → WebSocket Gateway → Frontend
  Market Ticks → P&L Engine → WebSocket Gateway → Frontend
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.event_bus import EventBus
from core.event_model import Event, EventPriority
from trading.lifecycle_events import (
    ORDER_CREATED,
    ORDER_SUBMITTED,
    ORDER_ACKNOWLEDGED,
    ORDER_PARTIAL_FILL,
    ORDER_FILLED,
    ORDER_REJECTED,
    ORDER_CANCELLED,
    TRADE_CREATED,
    TRADE_UPDATED,
    TRADE_CLOSED,
    POSITION_OPENED,
    POSITION_UPDATED,
    POSITION_CLOSED,
    PNL_UPDATED,
    RECONCILIATION_WARNING,
    RECONCILIATION_COMPLETED,
)
from trading.pnl_engine import PortfolioPnL


class LifecycleEventService:
    """
    Publishes lifecycle events to the Event Bus for WebSocket broadcast.
    Acts as the bridge between backend state changes and frontend updates.
    """

    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus = event_bus

    def set_event_bus(self, bus: EventBus):
        self._event_bus = bus

    def _publish(self, event_type: str, payload: dict[str, Any], priority: EventPriority = EventPriority.NORMAL):
        if not self._event_bus:
            return
        try:
            import asyncio
            event = Event(
                type=event_type,
                source="lifecycle_event_service",
                payload=payload,
                priority=priority,
            )
            asyncio.ensure_future(self._event_bus.publish(event))
        except Exception:
            pass

    # ── Order events ──

    def order_created(self, order: dict[str, Any]):
        self._publish(ORDER_CREATED, {"order": order, "timestamp": _now()})

    def order_submitted(self, order: dict[str, Any]):
        self._publish(ORDER_SUBMITTED, {"order": order, "timestamp": _now()})

    def order_acknowledged(self, order: dict[str, Any]):
        self._publish(ORDER_ACKNOWLEDGED, {"order": order, "timestamp": _now()})

    def order_partial_fill(self, order: dict[str, Any]):
        self._publish(ORDER_PARTIAL_FILL, {"order": order, "timestamp": _now()})

    def order_filled(self, order: dict[str, Any]):
        self._publish(ORDER_FILLED, {"order": order, "timestamp": _now()})

    def order_rejected(self, order: dict[str, Any]):
        self._publish(ORDER_REJECTED, {"order": order, "timestamp": _now()})

    def order_cancelled(self, order: dict[str, Any]):
        self._publish(ORDER_CANCELLED, {"order": order, "timestamp": _now()})

    # ── Trade events ──

    def trade_created(self, trade: dict[str, Any]):
        self._publish(TRADE_CREATED, {"trade": trade, "timestamp": _now()})

    def trade_updated(self, trade: dict[str, Any]):
        self._publish(TRADE_UPDATED, {"trade": trade, "timestamp": _now()})

    def trade_closed(self, trade: dict[str, Any]):
        self._publish(TRADE_CLOSED, {"trade": trade, "timestamp": _now()})

    # ── Position events ──

    def position_opened(self, position: dict[str, Any]):
        self._publish(POSITION_OPENED, {"position": position, "timestamp": _now()})

    def position_updated(self, position: dict[str, Any]):
        self._publish(POSITION_UPDATED, {"position": position, "timestamp": _now()})

    def position_closed(self, position: dict[str, Any]):
        self._publish(POSITION_CLOSED, {"position": position, "timestamp": _now()})

    # ── P&L events ──

    def pnl_updated(self, pnl: PortfolioPnL):
        self._publish(PNL_UPDATED, pnl.to_dict(), priority=EventPriority.LOW)

    # ── Reconciliation events ──

    def reconciliation_warning(self, warnings: list[dict]):
        self._publish(RECONCILIATION_WARNING, {"warnings": warnings, "timestamp": _now()})

    def reconciliation_completed(self, result: dict[str, Any]):
        self._publish(RECONCILIATION_COMPLETED, result)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
