"""
MarketMind AI — WebSocket Message Types

Standard message format for all WebSocket communication.
Every message sent to or received from a client follows this schema.

Client → Server message types:
    subscribe       — Subscribe to channels/symbols
    unsubscribe     — Unsubscribe from channels/symbols
    ping            — Heartbeat ping
    list_sub        — List active subscriptions

Server → Client message types:
    market_data     — Market data update (candles, reference levels)
    engine_event    — Live engine event (refreshed, error)
    signal          — Trade signal update (future)
    error           — Error notification
    pong            — Heartbeat pong
    welcome         — Connection confirmation
    sub_confirmed   — Subscription confirmed
    unsub_confirmed — Unsubscription confirmed
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ClientMessageType(str, Enum):
    """Message types a client can send to the server."""

    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"
    LIST_SUB = "list_sub"


class ServerMessageType(str, Enum):
    """Message types the server can send to clients."""

    WELCOME = "welcome"
    MARKET_DATA = "market_data"
    ENGINE_EVENT = "engine_event"
    SIGNAL = "signal"
    ERROR = "error"
    PONG = "pong"
    SUB_CONFIRMED = "sub_confirmed"
    UNSUB_CONFIRMED = "unsub_confirmed"


def make_message(
    msg_type: ServerMessageType | str,
    channel: str = "",
    symbol: str = "",
    payload: dict[str, Any] | None = None,
    **extra,
) -> dict[str, Any]:
    """
    Build a standardized server → client message.

    Args:
        msg_type: Message type enum or string
        channel: Channel name (e.g. "market_data", "signals")
        symbol: Optional symbol this message relates to
        payload: Message payload data
        **extra: Additional top-level fields

    Returns:
        dict with id, type, channel, symbol, timestamp, payload, version
    """
    import uuid
    from datetime import datetime, timezone

    return {
        "id": uuid.uuid4().hex[:12],
        "type": msg_type.value if isinstance(msg_type, ServerMessageType) else msg_type,
        "channel": channel,
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "payload": payload or {},
        "version": "1.0",
        **extra,
    }


def make_welcome(client_id: str) -> dict[str, Any]:
    """Build a welcome message for a newly connected client."""
    return make_message(
        ServerMessageType.WELCOME,
        payload={
            "client_id": client_id,
            "protocol_version": "1.0",
            "server_time": __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .isoformat(),
        },
    )


def make_pong() -> dict[str, Any]:
    """Build a heartbeat pong response."""
    return make_message(ServerMessageType.PONG)


def make_error(code: str, detail: str) -> dict[str, Any]:
    """Build an error message."""
    return make_message(
        ServerMessageType.ERROR,
        payload={"code": code, "detail": detail},
    )


def make_market_data(symbol: str, data: dict[str, Any]) -> dict[str, Any]:
    """Build a market data update message."""
    return make_message(
        ServerMessageType.MARKET_DATA,
        channel="market_data",
        symbol=symbol,
        payload=data,
    )


def make_engine_event(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    """Build an engine event message."""
    return make_message(
        ServerMessageType.ENGINE_EVENT,
        channel="engine",
        payload={"event_type": event_type, "data": data},
    )
