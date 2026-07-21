"""
MarketMind AI — Tick API Routes

Endpoints for querying live tick data from the Tick Engine.
"""

from fastapi import APIRouter, HTTPException

from tick.engine import TickEngine

router = APIRouter(tags=["ticks"])

_tick_engine: TickEngine | None = None


def set_tick_engine(engine: TickEngine):
    global _tick_engine
    _tick_engine = engine


def _get_engine() -> TickEngine:
    assert _tick_engine is not None, "TickEngine not initialized"
    return _tick_engine


@router.get("/api/ticks/status")
async def tick_status():
    """Return Tick Engine status and statistics."""
    engine = _get_engine()
    return engine.get_stats()


@router.get("/api/ticks/latest")
async def ticks_latest():
    """Return the latest tick for every tracked symbol."""
    engine = _get_engine()
    ticks = engine.latest_ticks()
    return {
        "ticks": {sym: t.to_dict() for sym, t in ticks.items()},
    }


@router.get("/api/ticks/latest/{symbol}")
async def tick_latest_symbol(symbol: str):
    """Return the latest tick for a specific symbol."""
    engine = _get_engine()
    tick = engine.latest_tick(symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"No tick data for {symbol}")
    return tick.to_dict()
