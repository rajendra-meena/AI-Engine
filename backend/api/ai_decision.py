"""AI Decision API routes."""

from fastapi import APIRouter, Query, HTTPException

from ai_decision.engine import AIDecisionEngine

router = APIRouter(tags=["ai"])

_engine: AIDecisionEngine | None = None


def set_ai_decision_engine(engine: AIDecisionEngine):
    global _engine
    _engine = engine


def _get() -> AIDecisionEngine:
    assert _engine is not None, "AIDecisionEngine not initialized"
    return _engine


@router.get("/api/ai/status")
async def ai_status():
    return _get().get_stats()


@router.get("/api/ai/latest")
async def ai_latest(symbol: str = Query("NIFTY 50")):
    snap = _get().latest(symbol)
    if snap is None:
        raise HTTPException(status_code=404, detail="No AI decision data")
    return snap


@router.get("/api/ai/history")
async def ai_history(symbol: str = Query("NIFTY 50"), count: int = Query(100)):
    return {"snapshots": _get().history(symbol, count)}
