"""
MarketMind AI — Indicator API Routes
"""

from fastapi import APIRouter, Query, HTTPException

from indicators.engine import IndicatorEngine

router = APIRouter(tags=["indicators"])

_indicator_engine: IndicatorEngine | None = None


def set_indicator_engine(engine: IndicatorEngine):
    global _indicator_engine
    _indicator_engine = engine


def _get_engine() -> IndicatorEngine:
    assert _indicator_engine is not None, "IndicatorEngine not initialized"
    return _indicator_engine


@router.get("/api/indicators/status")
async def indicator_status():
    """Return Indicator Engine statistics."""
    engine = _get_engine()
    return engine.get_stats()


@router.get("/api/indicators/latest")
async def indicator_latest(
    symbol: str = Query("NIFTY 50"),
    interval: str = Query("15m"),
):
    """Return the latest indicator snapshot for a symbol/interval."""
    engine = _get_engine()
    snap = engine.latest_snapshot(symbol, interval)
    if snap is None:
        raise HTTPException(status_code=404, detail="No indicators available")
    return snap
