"""
MarketMind AI — Candle API Routes

Endpoints for querying candles built by the Candle Aggregation Engine.
"""

from fastapi import APIRouter, Query, HTTPException

from candles.engine import CandleEngine

router = APIRouter(tags=["candles"])

_candle_engine: CandleEngine | None = None


def set_candle_engine(engine: CandleEngine):
    global _candle_engine
    _candle_engine = engine


def _get_engine() -> CandleEngine:
    assert _candle_engine is not None, "CandleEngine not initialized"
    return _candle_engine


@router.get("/api/candles/status")
async def candle_status():
    """Return Candle Engine statistics."""
    engine = _get_engine()
    return engine.get_stats()


@router.get("/api/candles/timeframes")
async def candle_timeframes():
    """Return supported timeframes."""
    engine = _get_engine()
    return {"timeframes": engine.timeframes()}


@router.get("/api/candles/latest")
async def candle_latest(
    symbol: str = Query("NIFTY 50"),
    interval: str = Query("15m"),
):
    """Return the most recent completed candle."""
    engine = _get_engine()
    candle = engine.latest(symbol, interval)
    if candle is None:
        raise HTTPException(status_code=404, detail="No candle found")
    return candle


@router.get("/api/candles/history")
async def candle_history(
    symbol: str = Query("NIFTY 50"),
    interval: str = Query("15m"),
    count: int = Query(100),
):
    """Return recent completed candles."""
    engine = _get_engine()
    return {"candles": engine.history(symbol, interval, count)}


@router.get("/api/candles/active")
async def candle_active(
    symbol: str = Query("NIFTY 50"),
    interval: str = Query("15m"),
):
    """Return the currently forming candle (not yet closed)."""
    engine = _get_engine()
    ac = engine.active_candle(symbol, interval)
    if ac is None:
        raise HTTPException(status_code=404, detail="No active candle")
    return ac
