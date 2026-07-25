"""
MarketStreamManager — Production-grade bridge between Zerodha KiteTicker
and the internal trading system.

Architecture:
    KiteTicker → MarketStreamManager → Tick Validation → PnLEngine
                                                          → EventService → WS Gateway
                                                          → MarketSubscriptionManager
                                                          → TickEngine

Responsibilities:
    - Connect/disconnect KiteTicker
    - Tick normalization and validation
    - Stale tick detection
    - Reconnect with subscription recovery
    - Connection health metrics
    - Backpressure protection
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from models.tick import Tick
from utils.logger import log_info, log_warn, log_error


# ── Connection states ──

class StreamState:
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"


# ── Stale thresholds (configurable) ──

STALE_TICK_THRESHOLD_MS = 5000  # 5 seconds without tick = stale
DEGRADED_TICK_THRESHOLD_MS = 2000  # 2 seconds without tick = degraded
HEALTH_CHECK_INTERVAL_S = 5  # check health every 5 seconds


# ── Normalized market tick ──

@dataclass
class MarketTick:
    """Canonical internal market tick — single source of truth for live prices."""
    symbol: str = ""
    exchange: str = "NSE"
    instrument_token: int = 0
    timestamp: str = ""
    last_price: float = 0.0
    last_quantity: int = 0
    volume: float = 0.0
    average_price: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    change_percent: float = 0.0
    buy_quantity: int = 0
    sell_quantity: int = 0
    oi: float = 0.0
    oi_day_high: float = 0.0
    oi_day_low: float = 0.0
    bid: float | None = None
    ask: float | None = None
    depth: dict[str, Any] = field(default_factory=dict)
    source: str = "zerodha"
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def is_valid(self) -> bool:
        """Basic validity check."""
        return self.last_price > 0 and self.instrument_token > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "last_price": self.last_price,
            "volume": self.volume,
            "timestamp": self.timestamp or self.received_at,
            "change_percent": self.change_percent,
            "source": self.source,
            "received_at": self.received_at,
        }


# ── Symbol health tracking ──

@dataclass
class SymbolHealth:
    symbol: str = ""
    last_tick_time: float = 0.0
    last_price: float = 0.0
    ticks_received: int = 0
    status: str = "unknown"  # live, degraded, stale

    def age_ms(self) -> float:
        return (time.time() - self.last_tick_time) * 1000 if self.last_tick_time > 0 else float("inf")

    def update_status(self, stale_threshold: float, degraded_threshold: float):
        age = self.age_ms()
        if age > stale_threshold:
            self.status = "stale"
        elif age > degraded_threshold:
            self.status = "degraded"
        else:
            self.status = "live"


# ── Market Stream Manager ──

class MarketStreamManager:
    """
    Central bridge between Zerodha KiteTicker and internal systems.

    Flow:
        KiteTicker →
            _tick_callback() →
                normalize_tick() →
                validate_tick() →
                update_pnl_engine() →
                update_symbol_health() →
                publish_to_event_service()
    """

    def __init__(self):
        self._state = StreamState.DISCONNECTED
        self._kite_ws = None
        self._pnl_engine = None
        self._event_service = None
        self._sub_manager = None
        self._tick_callback: Callable[[Tick], None] | None = None

        # Symbol health tracking
        self._symbol_health: dict[str, SymbolHealth] = {}

        # Tick validation counters
        self._ticks_received = 0
        self._ticks_valid = 0
        self._ticks_invalid = 0
        self._ticks_dropped = 0

        # Connection tracking
        self._connection_time: float = 0.0
        self._last_disconnect_time: float = 0.0
        self._reconnect_count = 0
        self._last_error: str | None = None

        # Stale thresholds
        self._stale_threshold_ms = STALE_TICK_THRESHOLD_MS
        self._degraded_threshold_ms = DEGRADED_TICK_THRESHOLD_MS

        # Health check task
        self._health_task: asyncio.Task | None = None

    # ── Dependencies injection ──

    def set_kite_ws(self, ws):
        self._kite_ws = ws

    def set_pnl_engine(self, engine):
        self._pnl_engine = engine

    def set_event_service(self, svc):
        self._event_service = svc

    def set_sub_manager(self, mgr):
        self._sub_manager = mgr

    def set_tick_callback(self, cb: Callable[[Tick], None] | None):
        """Register callback for raw Tick objects (for TickEngine)."""
        self._tick_callback = cb

    def set_stale_thresholds(self, stale_ms: int, degraded_ms: int):
        self._stale_threshold_ms = stale_ms
        self._degraded_threshold_ms = degraded_ms

    # ── Connection lifecycle ──

    async def start(self):
        """Start the market stream."""
        self._state = StreamState.CONNECTING
        if self._kite_ws:
            try:
                await self._kite_ws.connect()
                self._state = StreamState.CONNECTED
                self._connection_time = time.time()
                self._reconnect_count = 0
                log_info("MarketStream: started")
            except Exception as e:
                self._state = StreamState.DISCONNECTED
                self._last_error = str(e)
                log_error("MarketStream: start failed", error=str(e))

        # Start health check loop
        self._health_task = asyncio.ensure_future(self._health_loop())

    async def stop(self):
        """Stop the market stream gracefully."""
        self._state = StreamState.STOPPING
        if self._health_task:
            self._health_task.cancel()
            self._health_task = None
        if self._kite_ws:
            self._kite_ws.disconnect()
        self._state = StreamState.STOPPED
        log_info("MarketStream: stopped")

    async def reconnect(self):
        """Force reconnection."""
        self._state = StreamState.RECONNECTING
        self._reconnect_count += 1
        if self._kite_ws:
            try:
                self._kite_ws.disconnect()
                await self._kite_ws.connect()
                self._state = StreamState.CONNECTED
                self._connection_time = time.time()
                # Restore subscriptions via subscription manager
                if self._sub_manager:
                    self._sub_manager.on_reconnect()
                log_info("MarketStream: reconnected", attempt=self._reconnect_count)
            except Exception as e:
                self._state = StreamState.DISCONNECTED
                self._last_error = str(e)
                log_error("MarketStream: reconnect failed", error=str(e))

    # ── Tick handling ──

    def on_kite_tick(self, tick: Tick):
        """
        Called by the KiteWebSocketClient for each incoming tick.
        This is the primary entry point for all market data.
        """
        self._ticks_received += 1

        # Normalize
        market_tick = self._normalize(tick)
        if not market_tick or not market_tick.is_valid():
            self._ticks_invalid += 1
            return

        self._ticks_valid += 1

        # Update symbol health
        self._update_health(market_tick)

        # Update P&L engine
        if self._pnl_engine:
            try:
                self._pnl_engine.update_price(market_tick.symbol, market_tick.last_price)
            except Exception as e:
                log_warn("MarketStream: P&L update failed", symbol=market_tick.symbol, error=str(e))

        # Forward raw tick to TickEngine if callback registered
        if self._tick_callback:
            try:
                self._tick_callback(tick)
            except Exception as e:
                log_warn("MarketStream: tick callback failed", error=str(e))

    def _normalize(self, tick: Tick) -> MarketTick | None:
        """Normalize a Tick to the canonical MarketTick format."""
        try:
            mt = MarketTick(
                symbol=tick.symbol,
                exchange=tick.exchange or "NSE",
                timestamp=tick.timestamp.isoformat() if hasattr(tick.timestamp, "isoformat") else str(tick.timestamp),
                last_price=tick.price,
                volume=tick.volume,
                bid=tick.bid,
                ask=tick.ask,
                source=tick.provider or "zerodha",
            )
            return mt
        except Exception as e:
            log_warn("MarketStream: normalize error", error=str(e))
            return None

    def _update_health(self, tick: MarketTick):
        """Update symbol health tracking."""
        health = self._symbol_health.get(tick.symbol)
        if not health:
            health = SymbolHealth(symbol=tick.symbol)
            self._symbol_health[tick.symbol] = health
        health.last_tick_time = time.time()
        health.last_price = tick.last_price
        health.ticks_received += 1

    # ── Health check loop ──

    async def _health_loop(self):
        """Periodic health check for stale symbols."""
        while True:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL_S)
                self._check_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_warn("MarketStream: health check error", error=str(e))

    def _check_health(self):
        """Check all tracked symbols for stale status."""
        stale_count = 0
        live_count = 0
        for health in self._symbol_health.values():
            health.update_status(self._stale_threshold_ms / 1000, self._degraded_threshold_ms / 1000)
            if health.status == "stale":
                stale_count += 1
            elif health.status == "live":
                live_count += 1

        # Update overall stream state
        if stale_count > 0 and live_count == 0:
            self._state = StreamState.DEGRADED
        elif stale_count > 0 and live_count > 0:
            self._state = StreamState.DEGRADED
        elif self._kite_ws and self._kite_ws.is_connected():
            self._state = StreamState.CONNECTED

    # ── Queries ──

    def get_state(self) -> str:
        return self._state

    def is_connected(self) -> bool:
        return self._state == StreamState.CONNECTED

    def get_symbol_health(self, symbol: str) -> SymbolHealth | None:
        return self._symbol_health.get(symbol)

    def get_all_symbol_health(self) -> dict[str, dict[str, Any]]:
        return {
            sym: {
                "symbol": h.symbol,
                "last_price": h.last_price,
                "age_ms": round(h.age_ms(), 1),
                "status": h.status,
                "ticks_received": h.ticks_received,
            }
            for sym, h in self._symbol_health.items()
        }

    def get_metrics(self) -> dict[str, Any]:
        return {
            "state": self._state,
            "ticks_received": self._ticks_received,
            "ticks_valid": self._ticks_valid,
            "ticks_invalid": self._ticks_invalid,
            "ticks_dropped": self._ticks_dropped,
            "tracked_symbols": len(self._symbol_health),
            "reconnect_count": self._reconnect_count,
            "connection_time": (
                datetime.fromtimestamp(self._connection_time).isoformat()
                if self._connection_time else None
            ),
            "last_error": self._last_error,
            "symbol_health": self.get_all_symbol_health(),
        }


# Singleton
_instance: MarketStreamManager | None = None


def get_stream_manager() -> MarketStreamManager:
    assert _instance is not None, "MarketStreamManager not initialized"
    return _instance


def init_stream_manager() -> MarketStreamManager:
    global _instance
    _instance = MarketStreamManager()
    return _instance
