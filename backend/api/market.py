"""
MarketMind AI — Market Data API Routes

Endpoints for fetching daily OHLC, intraday candles, and cache status.
All requests are delegated to the MarketDataService singleton.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Query

from core.constants import DAILY_LOOKBACK_DEFAULT_DAYS
from core import service_locator
from services.market_data_service import MarketDataService

router = APIRouter(tags=["market"])

# Singleton service instance — created once, reused across requests
_service: MarketDataService | None = None


def _get_service() -> MarketDataService:
    """Get or create the MarketDataService singleton."""
    global _service
    if _service is None:
        _service = MarketDataService()
    return _service


@router.get("/api/data")
async def get_data(
    symbol: str = Query("NIFTY 50", description="Index display name"),
    start: str = Query(None, description="Start date YYYY-MM-DD"),
    end: str = Query(None, description="End date YYYY-MM-DD"),
):
    """Fetch historical index data with dual-layer caching."""
    service = _get_service()
    today = date.today()
    end_date = date.fromisoformat(end) if end else today
    start_date = date.fromisoformat(start) if start else end_date - timedelta(days=DAILY_LOOKBACK_DEFAULT_DAYS)

    try:
        return await service.get_daily(symbol, start_date, end_date)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"symbol": symbol, "data": [], "error": str(e)}


@router.get("/api/intraday")
async def get_intraday(
    symbol: str = Query("NIFTY 50", description="Index display name"),
    interval: str = Query("15m", description="Intraday interval: 1m, 2m, 5m, 15m, 30m, 60m"),
    days: int = Query(3, description="Number of days of intraday data"),
):
    """Fetch intraday candles with disk caching."""
    service = _get_service()
    try:
        return await service.get_intraday(symbol, interval, days)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"symbol": symbol, "candles": [], "error": str(e)}


@router.get("/api/cache/status")
async def cache_status(
    symbol: str = Query("NIFTY 50", description="Index display name"),
):
    """Return cache metadata for a given symbol."""
    service = _get_service()
    return await service.get_cache_status(symbol)


@router.get("/api/provider/status")
async def provider_status():
    """Return the active market data provider's health and capabilities."""
    service = _get_service()
    return await service.provider_status()


@router.get("/api/cache/memory")
async def memory_cache_status():
    """Return in-memory cache statistics (hits, misses, hit ratio, entries)."""
    service = _get_service()
    return await service.get_memory_cache_stats()


@router.post("/api/engine/refresh")
async def engine_refresh(
    symbol: str = "NIFTY 50",
    interval: str = "15m",
    days: int = 3,
):
    """Trigger a live data refresh for a symbol via the engine."""
    engine = service_locator.ensure_live_engine()
    return await engine.refresh_symbol(symbol, interval, days)


@router.post("/api/engine/refresh-all")
async def engine_refresh_all(interval: str = "15m", days: int = 3):
    """Trigger a live data refresh for ALL tracked symbols."""
    engine = service_locator.ensure_live_engine()
    return await engine.refresh_all(interval, days)


@router.get("/api/engine/status")
async def engine_status():
    """Return the Live Market Data Engine status and metrics."""
    engine = service_locator.ensure_live_engine()
    return engine.get_engine_metrics()


@router.get("/api/stream/status")
async def stream_status():
    """Return the Market Stream Router status and statistics."""
    router = service_locator.stream_router
    if router is None:
        return {"running": False}
    return router.get_stats()


@router.get("/api/stream/consumers")
async def stream_consumers():
    """Return registered stream consumers."""
    router = service_locator.stream_router
    if router is None:
        return {"consumers": []}
    return {"consumers": router.list_consumers()}


@router.get("/api/websocket/status")
async def websocket_status():
    """Return WebSocket Gateway connection statistics."""
    gateway = service_locator.ensure_gateway()
    return await gateway.get_connection_stats()


@router.get("/api/engine/symbols")
async def engine_symbols():
    """Return per-symbol tracking status from the Live Engine."""
    engine = service_locator.ensure_live_engine()
    return {"symbols": engine.get_all_symbol_status()}
