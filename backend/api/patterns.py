"""Pattern Recognition API routes."""

from fastapi import APIRouter, Query, HTTPException

from patterns.engine import PatternEngine

router = APIRouter(tags=["patterns"])

_engine: PatternEngine | None = None


def set_pattern_engine(engine: PatternEngine):
    global _engine
    _engine = engine


def _get() -> PatternEngine:
    assert _engine is not None, "PatternEngine not initialized"
    return _engine


@router.get("/api/patterns/status")
async def pattern_status():
    return _get().get_stats()


@router.get("/api/patterns/latest")
async def pattern_latest(symbol: str = Query("NIFTY 50"), interval: str = Query("15m")):
    snap = _get().latest_snapshot(symbol, interval)
    if snap is None:
        raise HTTPException(status_code=404, detail="No pattern data")
    return snap
