"""AI Decision Analysis API — analysis only, never places orders."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ai_decision.decision_service import DecisionService

router = APIRouter(tags=["ai"])

_service: DecisionService | None = None


def set_decision_service(svc: DecisionService):
    global _service
    _service = svc


def _get() -> DecisionService:
    assert _service is not None, "DecisionService not initialized"
    return _service


@router.get("/api/ai/decision/latest")
async def ai_decision_latest(symbol: str = Query("NIFTY 50")):
    """Get the latest AI decision for a symbol."""
    decision = _get().get_latest(symbol)
    if not decision:
        return {"decision": None, "message": "No decision yet"}
    return decision.to_dict()


@router.get("/api/ai/decision/{decision_id}")
async def ai_decision_by_id(decision_id: str):
    """Get a specific AI decision by ID."""
    decision = _get().get_decision(decision_id)
    if not decision:
        return {"error": "Not found"}
    return decision.to_dict()


@router.get("/api/ai/decision/history")
async def ai_decision_history(limit: int = Query(50)):
    """Get AI decision history."""
    return {"decisions": _get().get_history(limit)}


@router.post("/api/ai/decision/analyze")
async def ai_analyze(params: dict[str, Any]):
    """
    Analyze current market state and produce an AI decision.

    This is analysis only. It NEVER places a broker order.
    Returns: BUY/SELL/WAIT with evidence and reasoning.
    """
    svc = _get()
    decision = svc.analyze(
        symbol=params.get("symbol", "NIFTY 50"),
        interval=params.get("interval", "15m"),
        context_snap=params.get("context_snap"),
        indicator_snap=params.get("indicator_snap"),
        structure_snap=params.get("structure_snap"),
        pattern_snap=params.get("pattern_snap"),
        mtf_snap=params.get("mtf_snap"),
        sr_snap=params.get("sr_snap"),
        stream_state=params.get("stream_state", "connected"),
        candle_timestamp=params.get("candle_timestamp"),
    )
    if not decision:
        return {"decision": None, "message": "Duplicate — skipped"}
    result = decision.to_dict()
    result["note"] = "Analysis only. No broker order was placed."
    return result
