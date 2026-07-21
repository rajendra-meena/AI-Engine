"""
MarketMind AI — WebSocket Gateway

The main entry point for all WebSocket connections. Handles the WebSocket
handshake, message routing, Event Bus integration, and broadcasting.

Architecture:
    Client → FastAPI WS /ws → Gateway.handle_connection()
        │
        ├── Receive loop: parse client messages → route to handlers
        ├── Event Bus subscriber → broadcast relevant events to clients
        └── Heartbeat monitoring → cleanup idle connections
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from websocket.connection_manager import ConnectionManager
from websocket.message_types import (
    ClientMessageType,
    ServerMessageType,
    make_welcome,
    make_pong,
    make_error,
    make_market_data,
    make_engine_event,
    make_message,
)
from core.event_bus import EventBus, Event
from core.events import (
    ENGINE_STARTED,
    ENGINE_STOPPED,
    MARKET_DATA_UPDATED,
    DATA_FETCH_FAILED,
    MARKET_OPEN,
    MARKET_CLOSE,
    NEW_CANDLE,
    BREAKOUT,
    BREAKDOWN,
    SIGNAL_CREATED,
    SIGNAL_UPDATED,
    AI_DECISION,
)
from replay.events import FORWARDED_REPLAY_EVENTS
from core.symbols import is_valid_symbol
from utils.logger import log_info, log_warn, log_error


# Event types that get forwarded to WebSocket clients.
# Maps internal event type → WS channel name.
_FORWARDED_EVENTS: dict[str, str] = {
    MARKET_DATA_UPDATED: "market_data",
    DATA_FETCH_FAILED: "engine",
    ENGINE_STARTED: "engine",
    ENGINE_STOPPED: "engine",
    MARKET_OPEN: "market",
    MARKET_CLOSE: "market",
    NEW_CANDLE: "market_data",
    BREAKOUT: "patterns",
    BREAKDOWN: "patterns",
    SIGNAL_CREATED: "signals",
    SIGNAL_UPDATED: "signals",
    AI_DECISION: "ai",
}
# Merge replay events into the forward map
_FORWARDED_EVENTS.update(FORWARDED_REPLAY_EVENTS)


class WebSocketGateway:
    """
    Manages WebSocket connections, subscriptions, and Event Bus forwarding.

    Instantiate once at application startup with the Event Bus.

    Usage:
        gateway = WebSocketGateway(event_bus)
        await gateway.start()      # subscribes to Event Bus
        # In FastAPI route:
        await gateway.handle_connection(websocket)
        await gateway.stop()       # unsubscribes
    """

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._manager = ConnectionManager()
        self._running = False

    # ── Lifecycle ──

    async def start(self):
        """Start the gateway and subscribe to the Event Bus."""
        if self._running:
            return
        self._running = True
        self._event_bus.subscribe(
            "forward_to_websocket",
            self._on_internal_event,
            name="ws_gateway",
        )
        log_info("WebSocketGateway started")

    async def stop(self):
        """Stop the gateway and disconnect all clients."""
        self._running = False
        # Disconnect all clients
        count = await self._manager.get_active_count()
        log_info("WebSocketGateway stopping", active_clients=count)

    # ── Connection handler (called from FastAPI WS route) ──

    async def handle_connection(self, websocket: WebSocket):
        """
        Handle a single WebSocket connection lifecycle.

        This is called from the FastAPI WebSocket endpoint for each new connection.
        It accepts the connection, sends a welcome message, and enters the
        receive loop until the client disconnects.
        """
        client = await self._manager.connect(websocket)
        log_info("WebSocket client connected", id=client.id, ua=client.user_agent[:60])

        try:
            # Send welcome
            await self._manager.send(client.id, make_welcome(client.id))

            # Receive loop
            while self._running:
                raw = await websocket.receive_text()
                await self._handle_client_message(client.id, raw)

        except WebSocketDisconnect:
            log_info("WebSocket client disconnected", id=client.id)
        except Exception as e:
            log_warn("WebSocket client error", id=client.id, error=str(e))
        finally:
            await self._manager.disconnect(client.id)

    # ── Client message handlers ──

    async def _handle_client_message(self, client_id: str, raw: str):
        """Parse and route a single client message."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            await self._manager.send(client_id, make_error("PARSE_ERROR", "Invalid JSON"))
            return

        msg_type = data.get("type", "")
        payload = data.get("payload", {})

        if msg_type == ClientMessageType.PING.value:
            await self._manager.update_heartbeat(client_id)
            await self._manager.send(client_id, make_pong())

        elif msg_type == ClientMessageType.SUBSCRIBE.value:
            await self._handle_subscribe(client_id, payload)

        elif msg_type == ClientMessageType.UNSUBSCRIBE.value:
            await self._handle_unsubscribe(client_id, payload)

        elif msg_type == ClientMessageType.LIST_SUB.value:
            await self._send_subscriptions(client_id)

        else:
            await self._manager.send(
                client_id,
                make_error("UNKNOWN_TYPE", f"Unknown message type: {msg_type}"),
            )

    async def _handle_subscribe(self, client_id: str, payload: dict):
        """Handle a subscribe message from a client."""
        channels = payload.get("channels", [])
        symbols = payload.get("symbols", [])

        for ch in channels:
            await self._manager.add_subscription(client_id, ch)

        valid_symbols = []
        for sym in symbols:
            if is_valid_symbol(sym):
                await self._manager.add_symbol_subscription(client_id, sym)
                valid_symbols.append(sym)

        await self._manager.send(
            client_id,
            make_message(
                ServerMessageType.SUB_CONFIRMED,
                channel="system",
                payload={
                    "channels": channels,
                    "symbols": valid_symbols,
                },
            ),
        )

    async def _handle_unsubscribe(self, client_id: str, payload: dict):
        """Handle an unsubscribe message from a client."""
        channels = payload.get("channels", [])
        symbols = payload.get("symbols", [])

        for ch in channels:
            await self._manager.remove_subscription(client_id, ch)
        for sym in symbols:
            await self._manager.remove_symbol_subscription(client_id, sym)

        await self._manager.send(
            client_id,
            make_message(
                ServerMessageType.UNSUB_CONFIRMED,
                channel="system",
                payload={"channels": channels, "symbols": symbols},
            ),
        )

    async def _send_subscriptions(self, client_id: str):
        """Send the client their current subscriptions."""
        client = await self._manager.get_client(client_id)
        if client is None:
            return
        await self._manager.send(
            client_id,
            make_message(
                ServerMessageType.SUB_CONFIRMED,
                channel="system",
                payload={
                    "channels": list(client.subscriptions),
                    "symbols": list(client.subscribed_symbols),
                },
            ),
        )

    # ── Event Bus integration ──

    async def _on_internal_event(self, event: Event):
        """
        Called when a matching Event Bus event is published.
        Forwards to connected WebSocket clients.
        """
        if not self._running:
            return

        channel = _FORWARDED_EVENTS.get(event.type)
        if channel is None:
            return  # Not a forwarded event type

        # Build WS message
        if event.type == MARKET_DATA_UPDATED:
            ws_msg = make_market_data(event.payload.get("symbol", ""), event.payload)
        elif event.type in (ENGINE_STARTED, ENGINE_STOPPED, DATA_FETCH_FAILED):
            ws_msg = make_engine_event(event.type, event.payload)
        else:
            ws_msg = make_message(
                event.type,
                channel=channel,
                symbol=event.payload.get("symbol", ""),
                payload=event.payload,
            )

        # Broadcast to matching clients
        symbol = event.payload.get("symbol", "")
        if symbol:
            await self._manager.broadcast_to_symbol(symbol, ws_msg)

        await self._manager.broadcast_to_channel(channel, ws_msg)

    # ── Direct broadcast helpers ──

    async def broadcast_market_data(self, symbol: str, data: dict[str, Any]) -> int:
        """Directly broadcast market data to subscribed clients."""
        ws_msg = make_market_data(symbol, data)
        return await self._manager.broadcast_to_symbol(symbol, ws_msg)

    async def broadcast_to_all(self, message: dict[str, Any]) -> int:
        """Broadcast a message to ALL connected clients."""
        return await self._manager.broadcast(message)

    # ── Health / status ──

    async def get_connection_stats(self) -> dict[str, Any]:
        """Return connection statistics."""
        base = await self._manager.get_stats()
        base["gateway_running"] = self._running
        return base
