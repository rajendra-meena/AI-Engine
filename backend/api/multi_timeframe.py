"""Multi-Timeframe API routes."""

from fastapi import APIRouter, Query, HTTPException

from multi_timeframe.engine import MTFEngine

router = APIRouter(tags=["mtf"])

_engine: MTFEngine | None = None


def set_mtf_engine(engine: MTFEngine):
    global _engine
    _engine = engine


def _get() -> MTFEngine:
    assert _engine is not None, "MTFEngine not initialized"
    return _engine


@router.get("/api/mtf/status")
async def mtf_status():
    return _get().get_stats()


@router.get("/api/mtf/latest")
async def mtf_latest(symbol: str = Query("NIFTY 50")):
    snap = _get().latest(symbol)
    if snap is None:
        raise HTTPException(status_code=404, detail="No MTF data")
    return snap


@router.get("/api/mtf/history")
async def mtf_history(symbol: str = Query("NIFTY 50"), count: int = Query(100)):
    return {"snapshots": _get().history(symbol, count)}
