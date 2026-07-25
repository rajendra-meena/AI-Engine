"""Trading Context API routes."""

from fastapi import APIRouter, Query, HTTPException

from core.symbols import get_canonical_symbol
from trading_context.engine import TradingContextEngine

router = APIRouter(tags=["context"])

_engine: TradingContextEngine | None = None


def set_trading_context_engine(engine: TradingContextEngine):
    global _engine
    _engine = engine


def _get() -> TradingContextEngine:
    assert _engine is not None, "TradingContextEngine not initialized"
    return _engine


@router.get("/api/context/status")
async def context_status():
    return _get().get_stats()


@router.get("/api/context/latest")
async def context_latest(symbol: str = Query("NIFTY 50"), interval: str = Query("15m")):
    symbol = get_canonical_symbol(symbol)
    snap = _get().latest(symbol, interval)
    if snap is None:
        raise HTTPException(status_code=404, detail="No context data")
    return snap


@router.get("/api/context/history")
async def context_history(symbol: str = Query("NIFTY 50"), interval: str = Query("15m"), count: int = Query(100)):
    symbol = get_canonical_symbol(symbol)
    return {"snapshots": _get().history(symbol, interval, count)}
