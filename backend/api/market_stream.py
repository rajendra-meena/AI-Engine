"""Market Stream API — stream status, health, subscriptions."""

from __future__ import annotations

from fastapi import APIRouter

from trading.market_stream import get_stream_manager

router = APIRouter(tags=["market-stream"])


@router.get("/api/market-stream/status")
async def market_stream_status():
    """Get market stream status and metrics."""
    mgr = get_stream_manager()
    return mgr.get_metrics()


@router.get("/api/market-stream/subscriptions")
async def market_stream_subscriptions():
    """Get active symbol subscriptions."""
    mgr = get_stream_manager()
    return {
        "symbols": mgr.get_all_symbol_health(),
        "total": len(mgr.get_all_symbol_health()),
    }


@router.get("/api/market-stream/health")
async def market_stream_health():
    """Get market stream health check."""
    mgr = get_stream_manager()
    return {
        "state": mgr.get_state(),
        "connected": mgr.is_connected(),
        "tracked_symbols": len(mgr.get_all_symbol_health()),
    }


@router.post("/api/market-stream/reconnect")
async def market_stream_reconnect():
    """Force market stream reconnection. Does NOT place any orders."""
    mgr = get_stream_manager()
    await mgr.reconnect()
    return {"success": True, "state": mgr.get_state()}
