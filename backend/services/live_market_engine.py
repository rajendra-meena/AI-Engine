"""
MarketMind AI — Live Market Data Engine

The centralized coordinator for all live market data acquisition.

Architecture:
    Application / API Routes
        │
        ▼
    LiveMarketDataEngine  ← coordinates WHAT to fetch and WHEN
        │
        ▼
    MarketDataService     ← handles HOW to fetch (cache, provider, retries)
        │
        ▼
    ProviderFactory → YahooProvider

Responsibilities:
    - Lifecycle management (start/stop)
    - Coordinate data refreshes per symbol/interval
    - Track provider health, latency, last-update timestamps
    - Publish events on the Event Bus about data state
    - Central place for future scheduling/trigger logic

This engine does NOT:
    - Contain trading logic
    - Run background loops (that's Phase 9+)
    - Know about WebSockets (that's Phase 9+)
    - Implement indicator calculations
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from services.market_data_service import MarketDataService
from core.event_bus import EventBus
from core.events import (
    MARKET_DATA_UPDATED,
    PROVIDER_HEALTH_CHANGED,
    CACHE_REFRESHED,
    DATA_FETCH_FAILED,
    ENGINE_STARTED,
    ENGINE_STOPPED,
)
from core.symbols import list_display_names
from core.intervals import INTERVAL_KEYS
from data.exceptions import ProviderError
from utils.logger import log_info, log_warn, log_error


@dataclass
class SymbolStatus:
    """Tracks the latest state of data for a single symbol."""

    symbol: str
    last_intraday_update: datetime | None = None
    last_daily_update: datetime | None = None
    last_reference_update: datetime | None = None
    last_error: str | None = None
    last_error_time: datetime | None = None
    update_count: int = 0
    error_count: int = 0


@dataclass
class EngineMetrics:
    """Aggregate engine performance metrics."""

    total_refreshes: int = 0
    total_errors: int = 0
    total_events_published: int = 0
    start_time: datetime | None = None
    last_refresh_time: datetime | None = None
    avg_refresh_time_ms: float = 0.0
    _refresh_times: list[float] = field(default_factory=list)

    def record_refresh(self, duration_ms: float):
        self.total_refreshes += 1
        self.last_refresh_time = datetime.now(timezone.utc)
        self._refresh_times.append(duration_ms)
        # Keep only last 100 for average
        if len(self._refresh_times) > 100:
            self._refresh_times = self._refresh_times[-100:]
        self.avg_refresh_time_ms = round(
            sum(self._refresh_times) / len(self._refresh_times), 1
        )

    def record_error(self):
        self.total_errors += 1


class LiveMarketDataEngine:
    """
    Coordinates live market data acquisition for the application.

    Instantiate once at application startup with the Event Bus and
    MarketDataService, then call start().

    Usage:
        engine = LiveMarketDataEngine(event_bus, market_service)
        await engine.start()
        result = await engine.refresh_symbol("NIFTY 50", "15m")
        status = engine.get_symbol_status("NIFTY 50")
    """

    def __init__(
        self,
        event_bus: EventBus,
        market_service: MarketDataService | None = None,
    ):
        self._event_bus = event_bus
        self._service = market_service or MarketDataService()
        self._metrics = EngineMetrics()
        self._symbols: dict[str, SymbolStatus] = {}
        self._running = False

        # Initialize symbol tracking for all known symbols
        for s in list_display_names():
            self._symbols[s] = SymbolStatus(symbol=s)

    # ── Lifecycle ──

    async def start(self):
        """Start the engine. Initialises provider and publishes ENGINE_STARTED."""
        if self._running:
            log_warn("LiveMarketDataEngine already running")
            return

        self._running = True
        self._metrics.start_time = datetime.now(timezone.utc)

        # Initialize the provider connection through MarketDataService
        try:
            status = await self._service.provider_status()
            log_info(
                "LiveMarketDataEngine started",
                provider=status.get("provider"),
                status=status.get("status"),
                symbols=len(self._symbols),
            )
        except Exception as e:
            log_warn("LiveMarketDataEngine started (provider degraded)", error=str(e))

        await self._publish_event(
            ENGINE_STARTED,
            {
                "start_time": self._metrics.start_time.isoformat(),
                "symbols": list(self._symbols.keys()),
            },
        )

    async def stop(self):
        """Stop the engine and publish ENGINE_STOPPED."""
        self._running = False
        await self._publish_event(
            ENGINE_STOPPED,
            {
                "uptime_seconds": self.uptime_seconds,
                "total_refreshes": self._metrics.total_refreshes,
            },
        )
        log_info(
            "LiveMarketDataEngine stopped", refreshes=self._metrics.total_refreshes
        )

    @property
    def uptime_seconds(self) -> float:
        if self._metrics.start_time is None:
            return 0.0
        return (datetime.now(timezone.utc) - self._metrics.start_time).total_seconds()

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Data refresh ──

    async def refresh_symbol(
        self,
        symbol: str,
        interval: str = "15m",
        days: int = 3,
    ) -> dict[str, Any]:
        """
        Fetch the latest market data for a symbol.

        This is the primary method for refreshing live data. It:
          1. Calls MarketDataService.get_intraday() (hits memory cache → CSV → provider)
          2. Records timing and status
          3. Publishes MARKET_DATA_UPDATED event

        Returns:
            The same dict as MarketDataService.get_intraday()
        """
        if not self._running:
            log_warn("Engine not running, starting inline", symbol=symbol)
            await self.start()

        start_ns = time.time()

        try:
            result = await self._service.get_intraday(symbol, interval, days)
            elapsed_ms = round((time.time() - start_ns) * 1000, 1)

            # Update symbol status
            sym = self._symbols.get(symbol)
            if sym:
                sym.last_intraday_update = datetime.now(timezone.utc)
                sym.update_count += 1

            # Record metrics
            self._metrics.record_refresh(elapsed_ms)

            log_info(
                "Live data refreshed",
                symbol=symbol,
                interval=interval,
                candles=len(result.get("candles", [])),
                cached=result.get("cached"),
                elapsed_ms=elapsed_ms,
            )

            # Publish event
            await self._publish_event(
                MARKET_DATA_UPDATED,
                {
                    "symbol": symbol,
                    "interval": interval,
                    "candles_count": len(result.get("candles", [])),
                    "cached": result.get("cached"),
                    "elapsed_ms": elapsed_ms,
                    "daily_refs_available": result.get("dailyRefs") is not None,
                },
            )

            return result

        except ProviderError as e:
            elapsed_ms = round((time.time() - start_ns) * 1000, 1)
            self._metrics.record_error()

            sym = self._symbols.get(symbol)
            if sym:
                sym.last_error = str(e)
                sym.last_error_time = datetime.now(timezone.utc)
                sym.error_count += 1

            log_error(
                "Live data refresh failed",
                symbol=symbol,
                error=str(e),
                elapsed_ms=elapsed_ms,
            )

            await self._publish_event(
                DATA_FETCH_FAILED,
                {
                    "symbol": symbol,
                    "interval": interval,
                    "error": str(e),
                    "elapsed_ms": elapsed_ms,
                },
            )

            return {"symbol": symbol, "candles": [], "error": str(e)}

    async def refresh_all(
        self,
        interval: str = "15m",
        days: int = 3,
    ) -> dict[str, Any]:
        """
        Refresh data for ALL known symbols sequentially.

        Returns:
            A summary dict with per-symbol results.
        """
        results = {}
        for symbol in self._symbols:
            results[symbol] = await self.refresh_symbol(symbol, interval, days)

        await self._publish_event(
            CACHE_REFRESHED,
            {
                "symbols_refreshed": len(results),
                "interval": interval,
            },
        )

        return results

    # ── Daily data refresh ──

    async def refresh_daily(self, symbol: str) -> dict[str, Any]:
        """Refresh daily OHLC data for a symbol."""
        try:
            result = await self._service.get_daily(symbol)
            sym = self._symbols.get(symbol)
            if sym:
                sym.last_daily_update = datetime.now(timezone.utc)
            return result
        except ProviderError as e:
            log_error("Daily refresh failed", symbol=symbol, error=str(e))
            return {"symbol": symbol, "data": [], "error": str(e)}

    # ── Provider health ──

    async def check_provider_health(self) -> dict[str, Any]:
        """Check provider health and publish if status changed."""
        status = await self._service.provider_status()
        await self._publish_event(PROVIDER_HEALTH_CHANGED, status)
        return status

    # ── Status queries ──

    def get_symbol_status(self, symbol: str) -> dict[str, Any] | None:
        """Return the tracked status for a single symbol."""
        sym = self._symbols.get(symbol)
        if sym is None:
            return None
        return {
            "symbol": sym.symbol,
            "last_intraday_update": (
                sym.last_intraday_update.isoformat()
                if sym.last_intraday_update
                else None
            ),
            "last_daily_update": (
                sym.last_daily_update.isoformat() if sym.last_daily_update else None
            ),
            "last_error": sym.last_error,
            "last_error_time": (
                sym.last_error_time.isoformat() if sym.last_error_time else None
            ),
            "update_count": sym.update_count,
            "error_count": sym.error_count,
        }

    def get_all_symbol_status(self) -> list[dict[str, Any]]:
        """Return tracked status for ALL symbols."""
        return [self.get_symbol_status(s) for s in self._symbols]

    def get_engine_metrics(self) -> dict[str, Any]:
        """Return engine performance metrics."""
        return {
            "running": self._running,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "tracked_symbols": len(self._symbols),
            "total_refreshes": self._metrics.total_refreshes,
            "total_errors": self._metrics.total_errors,
            "total_events_published": self._metrics.total_events_published,
            "last_refresh_time": (
                self._metrics.last_refresh_time.isoformat()
                if self._metrics.last_refresh_time
                else None
            ),
            "avg_refresh_time_ms": self._metrics.avg_refresh_time_ms,
            "start_time": (
                self._metrics.start_time.isoformat()
                if self._metrics.start_time
                else None
            ),
        }

    # ── Internal helpers ──

    async def _publish_event(self, event_type: str, payload: dict):
        """Publish an event on the Event Bus."""
        from core.event_model import Event

        event = Event(
            type=event_type,
            source="live_market_engine",
            payload=payload,
        )
        success = await self._event_bus.publish(event)
        if success:
            self._metrics.total_events_published += 1
