"""SR Engine API routes."""

from fastapi import APIRouter, Query, HTTPException

from core.symbols import get_canonical_symbol
from support_resistance.engine import SREngine

router = APIRouter(tags=["sr"])

_engine: SREngine | None = None


def set_sr_engine(engine: SREngine):
    global _engine
    _engine = engine


def _get() -> SREngine:
    assert _engine is not None, "SREngine not initialized"
    return _engine


@router.get("/api/sr/status")
async def sr_status():
    return _get().get_stats()


@router.get("/api/sr/latest")
async def sr_latest(symbol: str = Query("NIFTY 50")):
    symbol = get_canonical_symbol(symbol)
    snap = _get().latest(symbol)
    if snap is None:
        raise HTTPException(status_code=404, detail="No SR data")
    return snap


@router.get("/api/sr/history")
async def sr_history(symbol: str = Query("NIFTY 50"), count: int = Query(100)):
    symbol = get_canonical_symbol(symbol)
    return {"snapshots": _get().history(symbol, count)}
