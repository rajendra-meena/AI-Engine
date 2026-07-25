"""
Zerodha Kite Connect — WebSocket Ticker

Connects to Kite's WebSocket for real-time market data.
Handles auto-reconnect, heartbeat, and batched subscriptions.

Data flow:
    Kite WebSocket → KiteTicker
        → on_ticks callback
        → TickEngine.publish_tick()
        → CandleEngine (via StreamRouter)
        → AI Engine (via Event Bus)
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable

from kiteconnect import KiteTicker

from models.tick import Tick
from utils.logger import log_info, log_warn, log_error


# Max reconnection attempts before giving up
MAX_RECONNECT_ATTEMPTS = 10
# Base delay for exponential backoff (seconds)
RECONNECT_BASE_DELAY = 1.0
# Max reconnect delay cap
RECONNECT_MAX_DELAY = 60.0
# Heartbeat interval (seconds)
HEARTBEAT_INTERVAL = 30


class KiteWebSocketError(Exception):
    """Base exception for Kite WebSocket errors."""
    pass


class KiteWebSocketClient:
    """
    Manages the Kite WebSocket connection for real-time ticks.

    Automatically reconnects with exponential backoff.
    Normalizes ticks to the system Tick model.
    Supports subscribing/unsubscribing instrument tokens.
    """

    def __init__(self, api_key: str, access_token: str, tick_callback: Callable[[Tick], None] | None = None):
        self._api_key = api_key
        self._access_token = access_token
        self._tick_callback = tick_callback
        self._ticker: KiteTicker | None = None
        self._running = False
        self._connected = False
        self._reconnect_attempts = 0
        self._subscribed_tokens: list[int] = []
        self._last_heartbeat: datetime | None = None
        self._connection_time: datetime | None = None
        self._ticks_received = 0
        self._lock = Lock()
        self._connect_lock = asyncio.Lock()
        self._stats: dict[str, Any] = {
            "connected": False,
            "ticks_received": 0,
            "reconnect_attempts": 0,
            "subscribed_tokens": 0,
            "last_tick_time": None,
            "connection_time": None,
            "latency_ms": None,
        }

    # ── Connection ──

    async def connect(self):
        """Connect to Kite WebSocket."""
        async with self._connect_lock:
            if self._connected:
                return

            try:
                self._ticker = KiteTicker(
                    api_key=self._api_key,
                    access_token=self._access_token,
                )

                # Set callbacks
                self._ticker.on_ticks = self._on_ticks_wrapper
                self._ticker.on_connect = self._on_connect_wrapper
                self._ticker.on_close = self._on_close_wrapper
                self._ticker.on_error = self._on_error_wrapper
                self._ticker.on_reconnect = self._on_reconnect_wrapper
                self._ticker.on_noreconnect = self._on_noreconnect_wrapper

                # Configure auto reconnect
                self._ticker.auto_reconnect = True
                self._ticker.reconnect_max_tries = MAX_RECONNECT_ATTEMPTS
                self._ticker.reconnect_max_delay = RECONNECT_MAX_DELAY

                # Connect in a thread (KiteTicker is not async)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._ticker.connect)
                self._running = True
                self._connection_time = datetime.now(timezone.utc)
                self._stats["connection_time"] = self._connection_time.isoformat()

                log_info("KiteWebSocket: connected")
                return True

            except Exception as e:
                log_error("KiteWebSocket: connection failed", error=str(e))
                self._ticker = None
                raise KiteWebSocketError(f"WebSocket connection failed: {e}") from e

    def disconnect(self):
        """Disconnect from Kite WebSocket."""
        self._running = False
        self._connected = False
        try:
            if self._ticker:
                self._ticker.close()
                self._ticker = None
        except Exception as e:
            log_warn("KiteWebSocket: disconnect error", error=str(e))
        log_info("KiteWebSocket: disconnected")

    # ── Subscriptions ──

    def subscribe(self, tokens: list[int]):
        """Subscribe to instrument tokens (full mode by default)."""
        if not self._ticker or not self._connected:
            log_warn("KiteWebSocket: not connected, cannot subscribe")
            return

        with self._lock:
            # Add new tokens
            new_tokens = [t for t in tokens if t not in self._subscribed_tokens]
            if new_tokens:
                self._ticker.subscribe(new_tokens)
                self._ticker.set_mode(self._ticker.MODE_FULL, new_tokens)
                self._subscribed_tokens.extend(new_tokens)
                log_info("KiteWebSocket: subscribed", tokens=len(new_tokens))

    def unsubscribe(self, tokens: list[int]):
        """Unsubscribe from instrument tokens."""
        if not self._ticker or not self._connected:
            return

        with self._lock:
            self._ticker.unsubscribe(tokens)
            self._subscribed_tokens = [t for t in self._subscribed_tokens if t not in tokens]
            log_info("KiteWebSocket: unsubscribed", tokens=len(tokens))

    def resubscribe_all(self):
        """Resubscribe to all previously subscribed tokens."""
        with self._lock:
            if self._subscribed_tokens and self._ticker and self._connected:
                self._ticker.subscribe(self._subscribed_tokens)
                self._ticker.set_mode(self._ticker.MODE_FULL, self._subscribed_tokens)
                log_info("KiteWebSocket: resubscribed", count=len(self._subscribed_tokens))

    # ── Callbacks (called from KiteTicker threads) ──

    def _on_ticks_wrapper(self, ws, ticks):
        """Called when ticks arrive from Kite WebSocket."""
        self._ticks_received += len(ticks)
        self._stats["ticks_received"] = self._ticks_received
        self._stats["last_tick_time"] = datetime.now(timezone.utc).isoformat()

        for ktick in ticks:
            try:
                tick = self._normalize_tick(ktick)
                if tick and self._tick_callback:
                    self._tick_callback(tick)
            except Exception as e:
                log_error("KiteWebSocket: tick normalization error", error=str(e))

    def _on_connect_wrapper(self, ws, response):
        """Called when WebSocket connects."""
        self._connected = True
        self._reconnect_attempts = 0
        self._connection_time = datetime.now(timezone.utc)
        self._stats["connected"] = True
        self._stats["connection_time"] = self._connection_time.isoformat()
        log_info("KiteWebSocket: connected to Kite")

        # Resubscribe to all tokens
        self.resubscribe_all()

    def _on_close_wrapper(self, ws, code, reason):
        """Called when WebSocket closes."""
        self._connected = False
        self._stats["connected"] = False
        log_info("KiteWebSocket: closed", code=code, reason=reason)

    def _on_error_wrapper(self, ws, error):
        """Called on WebSocket error."""
        self._stats["last_error"] = str(error)
        log_error("KiteWebSocket: error", error=str(error))

    def _on_reconnect_wrapper(self, ws, attempts_count):
        """Called on reconnect attempt."""
        self._reconnect_attempts = attempts_count
        self._stats["reconnect_attempts"] = attempts_count
        log_info("KiteWebSocket: reconnecting", attempt=attempts_count)

    def _on_noreconnect_wrapper(self, ws):
        """Called when max reconnection attempts exceeded."""
        self._connected = False
        self._running = False
        self._stats["connected"] = False
        log_error("KiteWebSocket: max reconnect attempts exceeded")

    # ── Tick normalization ──

    def _normalize_tick(self, ktick: dict[str, Any]) -> Tick | None:
        """
        Convert a Kite tick dict to our system Tick model.

        Kite tick format:
        {
            "instrument_token": 12345,
            "last_price": 24500.0,
            "volume": 1000,
            "buy_quantity": 500,
            "sell_quantity": 400,
            "last_quantity": 10,
            "ohlc": {"open": 24400, "high": 24550, "low": 24350, "close": 24400},
            "depth": {"buy": [...], "sell": [...]},
            "timestamp": "2024-01-15 09:30:00",
            "change": 0.5,
        }
        """
        try:
            price = float(ktick.get("last_price", 0))
            if price <= 0:
                return None

            volume = float(ktick.get("volume", 0))
            timestamp_str = ktick.get("timestamp", "")

            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                except (ValueError, TypeError):
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            # Extract depth for bid/ask
            depth = ktick.get("depth", {})
            bids = depth.get("buy", [])
            asks = depth.get("sell", [])
            best_bid = bids[0].get("price", None) if bids else None
            best_ask = asks[0].get("price", None) if asks else None

            # Map instrument token to symbol (will be resolved by caller)
            token = ktick.get("instrument_token", 0)
            symbol = f"token:{token}"

            return Tick(
                symbol=symbol,
                price=price,
                timestamp=timestamp,
                volume=volume,
                bid=best_bid,
                ask=best_ask,
                provider="zerodha",
                exchange="NSE",
            )
        except Exception as e:
            log_error("KiteWebSocket: normalize tick error", error=str(e))
            return None

    # ── Status ──

    def is_connected(self) -> bool:
        return self._connected

    def get_stats(self) -> dict[str, Any]:
        """Return connection and tick statistics."""
        now = datetime.now(timezone.utc)
        latency = None
        if self._connection_time:
            latency = int((now - self._connection_time).total_seconds() * 1000)

        self._stats["latency_ms"] = latency
        self._stats["subscribed_tokens"] = len(self._subscribed_tokens)

        return dict(self._stats)

    def get_health(self) -> dict[str, Any]:
        """Return health status summary."""
        return {
            "connected": self._connected,
            "running": self._running,
            "ticks_received": self._ticks_received,
            "reconnect_attempts": self._reconnect_attempts,
            "last_tick_time": self._stats.get("last_tick_time"),
            "subscribed_tokens": len(self._subscribed_tokens),
        }
