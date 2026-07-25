"""Market Structure API routes."""

from fastapi import APIRouter, Query, HTTPException

from core.symbols import get_canonical_symbol
from market_structure.engine import MarketStructureEngine

router = APIRouter(tags=["structure"])

_engine: MarketStructureEngine | None = None


def set_market_structure_engine(engine: MarketStructureEngine):
    global _engine
    _engine = engine


def _get() -> MarketStructureEngine:
    assert _engine is not None, "MarketStructureEngine not initialized"
    return _engine


@router.get("/api/structure/status")
async def structure_status():
    return _get().get_stats()


@router.get("/api/structure/latest")
async def structure_latest(symbol: str = Query("NIFTY 50"), interval: str = Query("15m")):
    symbol = get_canonical_symbol(symbol)
    snap = _get().latest_snapshot(symbol, interval)
    if snap is None:
        raise HTTPException(status_code=404, detail="No structure data")
    return snap
