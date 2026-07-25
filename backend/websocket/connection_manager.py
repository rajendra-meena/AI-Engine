"""
MarketMind AI — WebSocket Connection Manager

Tracks all active WebSocket client connections, their subscriptions,
heartbeat state, and connection metadata.

Thread-safe via asyncio.Lock. All public methods are awaitable.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


@dataclass
class Client:
    """Represents a single connected WebSocket client."""

    id: str
    websocket: WebSocket
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    subscriptions: set[str] = field(default_factory=set)
    subscribed_symbols: set[str] = field(default_factory=set)
    messages_sent: int = 0
    messages_received: int = 0
    user_agent: str = ""

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.connected_at

    @property
    def is_idle(self, timeout: float = 60.0) -> bool:
        return (time.time() - self.last_heartbeat) > timeout


class ConnectionManager:
    """
    Manages all active WebSocket client connections.

    Usage:
        manager = ConnectionManager()
        client = await manager.connect(websocket)
        await manager.send(client.id, message)
        await manager.broadcast(message)
        await manager.disconnect(client.id)
    """

    def __init__(self):
        self._clients: dict[str, Client] = {}
        self._lock = asyncio.Lock()

    # ── Connection lifecycle ──

    async def connect(self, websocket: WebSocket) -> Client:
        """Accept a new WebSocket connection and register the client."""
        await websocket.accept()
        client_id = uuid.uuid4().hex[:12]

        async with self._lock:
            client = Client(
                id=client_id,
                websocket=websocket,
                user_agent=websocket.headers.get("user-agent", ""),
            )
            self._clients[client_id] = client

        return client

    async def disconnect(self, client_id: str) -> bool:
        """Remove a client. Returns True if found. Does NOT close the WS."""
        async with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                return True
            return False

    # ── Sending ──

    async def send(self, client_id: str, message: dict[str, Any]) -> bool:
        """Send a JSON message to a specific client. Returns True on success."""
        async with self._lock:
            client = self._clients.get(client_id)
            if client is None:
                return False

        try:
            await client.websocket.send_json(message)
            client.messages_sent += 1
            return True
        except Exception:
            # Client disconnected unexpectedly
            await self.disconnect(client_id)
            return False

    async def broadcast(self, message: dict[str, Any]) -> int:
        """Send a message to ALL connected clients. Returns count of successes."""
        async with self._lock:
            client_ids = list(self._clients.keys())

        success_count = 0
        for cid in client_ids:
            if await self.send(cid, message):
                success_count += 1
        return success_count

    async def broadcast_to_symbol(self, symbol: str, message: dict[str, Any]) -> int:
        """Send a message to clients subscribed to a specific symbol."""
        async with self._lock:
            targets = [
                cid
                for cid, c in self._clients.items()
                if symbol in c.subscribed_symbols
            ]

        success_count = 0
        for cid in targets:
            if await self.send(cid, message):
                success_count += 1
        return success_count

    async def broadcast_to_channel(self, channel: str, message: dict[str, Any]) -> int:
        """Send a message to clients subscribed to a specific channel."""
        async with self._lock:
            targets = [
                cid for cid, c in self._clients.items() if channel in c.subscriptions
            ]

        success_count = 0
        for cid in targets:
            if await self.send(cid, message):
                success_count += 1
        return success_count

    # ── Subscriptions ──

    async def add_subscription(self, client_id: str, channel: str) -> bool:
        """Subscribe a client to a channel."""
        async with self._lock:
            client = self._clients.get(client_id)
            if client is None:
                return False
            client.subscriptions.add(channel)
            return True

    async def remove_subscription(self, client_id: str, channel: str) -> bool:
        """Unsubscribe a client from a channel."""
        async with self._lock:
            client = self._clients.get(client_id)
            if client is None:
                return False
            client.subscriptions.discard(channel)
            return True

    async def add_symbol_subscription(self, client_id: str, symbol: str) -> bool:
        """Subscribe a client to updates for a specific symbol."""
        async with self._lock:
            client = self._clients.get(client_id)
            if client is None:
                return False
            client.subscribed_symbols.add(symbol)
            return True

    async def remove_symbol_subscription(self, client_id: str, symbol: str) -> bool:
        """Unsubscribe a client from a specific symbol."""
        async with self._lock:
            client = self._clients.get(client_id)
            if client is None:
                return False
            client.subscribed_symbols.discard(symbol)
            return True

    # ── Heartbeat ──

    async def update_heartbeat(self, client_id: str) -> bool:
        """Update a client's heartbeat timestamp."""
        async with self._lock:
            client = self._clients.get(client_id)
            if client is None:
                return False
            client.last_heartbeat = time.time()
            client.messages_received += 1
            return True

    # ── Status ──

    async def get_client(self, client_id: str) -> Client | None:
        """Get a client by ID."""
        async with self._lock:
            return self._clients.get(client_id)

    async def get_active_count(self) -> int:
        """Return the number of currently connected clients."""
        async with self._lock:
            return len(self._clients)

    async def get_stats(self) -> dict[str, Any]:
        """Return aggregate connection statistics."""
        async with self._lock:
            total_sent = sum(c.messages_sent for c in self._clients.values())
            total_recv = sum(c.messages_received for c in self._clients.values())
            total_subs = sum(len(c.subscriptions) for c in self._clients.values())
            total_symbol_subs = sum(
                len(c.subscribed_symbols) for c in self._clients.values()
            )
            uptimes = [c.uptime_seconds for c in self._clients.values()]

        return {
            "active_connections": len(self._clients),
            "total_messages_sent": total_sent,
            "total_messages_received": total_recv,
            "total_subscriptions": total_subs,
            "total_symbol_subscriptions": total_symbol_subs,
            "avg_uptime_seconds": (
                round(sum(uptimes) / len(uptimes), 1) if uptimes else 0.0
            ),
            "max_uptime_seconds": round(max(uptimes), 1) if uptimes else 0.0,
        }

    async def cleanup_idle(self, timeout: float = 120.0) -> int:
        """Disconnect clients that haven't sent a heartbeat within timeout."""
        async with self._lock:
            idle = [
                cid
                for cid, c in self._clients.items()
                if (time.time() - c.last_heartbeat) > timeout
            ]
            for cid in idle:
                try:
                    await self._clients[cid].websocket.close()
                except Exception:
                    pass
                del self._clients[cid]
            return len(idle)
