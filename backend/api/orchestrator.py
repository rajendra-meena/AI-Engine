"""
MarketMind AI — Trading Orchestrator API Routes

Endpoints for the end-to-end trading pipeline:
- Analyze (full pipeline, no execution)
- Execute (pipeline + broker execution)
- Paper trade (pipeline + paper execution)
- Trace lookup
- Pipeline history
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from orchestrator.trading_orchestrator import TradingOrchestrator

router = APIRouter(tags=["orchestrator"])

_orchestrator: TradingOrchestrator | None = None


def set_orchestrator(orchestrator: TradingOrchestrator):
    global _orchestrator
    _orchestrator = orchestrator


def _get() -> TradingOrchestrator:
    assert _orchestrator is not None, "Orchestrator not initialized"
    return _orchestrator


@router.get("/api/orchestrator/status")
async def orchestrator_status():
    """Get orchestrator status summary."""
    return _get().get_status()


@router.post("/api/orchestrator/analyze")
async def orchestrator_analyze(params: dict[str, Any]):
    """
    Run the full analysis pipeline WITHOUT executing an order.

    This evaluates: AI → ML → Strategy → Planner → Risk Firewall.
    Risk Firewall may return BLOCKED — broker is never called.
    """
    try:
        result = await _get().analyze(
            symbol=params.get("symbol", ""),
            interval=params.get("interval", "15m"),
            exchange=params.get("exchange", "NSE"),
            execution_mode=params.get("execution_mode", "paper"),
            strategy_id=params.get("strategy_id"),
            user_id=params.get("user_id", ""),
            ai_score=params.get("ai_score"),
            ai_confidence=params.get("ai_confidence"),
            ai_decision=params.get("ai_decision"),
            ml_prediction=params.get("ml_prediction"),
            ml_probability=params.get("ml_probability"),
            market_price=params.get("market_price"),
            idempotency_key=params.get("idempotency_key"),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/orchestrator/paper-trade")
async def orchestrator_paper_trade(params: dict[str, Any]):
    """
    Run full pipeline with PAPER execution.

    Uses real market data, real AI, real ML, real Risk Firewall.
    Only the broker order is simulated.
    """
    try:
        result = await _get().analyze(
            symbol=params.get("symbol", ""),
            interval=params.get("interval", "15m"),
            exchange=params.get("exchange", "NSE"),
            execution_mode="paper",
            strategy_id=params.get("strategy_id"),
            user_id=params.get("user_id", ""),
            ai_score=params.get("ai_score"),
            ai_confidence=params.get("ai_confidence"),
            ai_decision=params.get("ai_decision"),
            ml_prediction=params.get("ml_prediction"),
            ml_probability=params.get("ml_probability"),
            market_price=params.get("market_price"),
            idempotency_key=params.get("idempotency_key"),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/orchestrator/validate")
async def orchestrator_validate(params: dict[str, Any]):
    """
    Validate a potential trade against the Risk Firewall only.

    This is a lightweight check that runs ONLY the risk firewall stage.
    Returns approval/block status without running the full pipeline.
    """
    try:
        result = await _get().analyze(
            symbol=params.get("symbol", ""),
            interval=params.get("interval", "15m"),
            ai_score=params.get("ai_score"),
            ai_confidence=params.get("ai_confidence"),
            ai_decision=params.get("ai_decision"),
            market_price=params.get("market_price"),
            execution_mode="manual",
        )
        return {
            "risk_status": result.get("risk_status"),
            "risk_score": result.get("risk_score"),
            "risk_grade": result.get("risk_grade"),
            "risk_reasons": result.get("risk_reasons"),
            "stages": result.get("stages", {}),
            "trace_id": result.get("trace_id"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/orchestrator/trace/{trace_id}")
async def orchestrator_trace(trace_id: str):
    """Get a specific pipeline execution trace."""
    result = _get().get_trace(trace_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return result


@router.get("/api/orchestrator/history")
async def orchestrator_history(limit: int = Query(50)):
    """Get pipeline execution history."""
    return {"traces": _get().get_history(limit), "count": limit}


@router.get("/api/orchestrator/last-decision")
async def orchestrator_last_decision():
    """Get the most recent pipeline decision."""
    result = _get().get_last_decision()
    if result is None:
        return {"decision": None, "message": "No decisions yet"}
    return {"decision": result}
