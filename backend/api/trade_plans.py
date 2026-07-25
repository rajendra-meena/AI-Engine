"""Trade Plan API — analysis only, never places broker orders."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from trading.trade_plan import TradePlan, TradePlanner

router = APIRouter(tags=["trade-plans"])

_planner: TradePlanner | None = None
_plans: dict[str, TradePlan] = {}
_history: list[TradePlan] = []


def set_trade_planner(planner: TradePlanner):
    global _planner
    _planner = planner


def _get() -> TradePlanner:
    assert _planner is not None, "TradePlanner not initialized"
    return _planner


@router.post("/api/trade-plans/analyze")
async def analyze_trade_plan(params: dict[str, Any]):
    """
    Analyze an AI decision and produce a complete TradePlan.

    This is analysis ONLY. No broker order is placed.
    The TradePlan is validated through Strategy qualification and Risk Firewall.
    """
    from ai_decision.decision_service import AIDecision

    ai_decision = AIDecision(
        decision_id=params.get("decision_id", ""),
        trace_id=params.get("trace_id", ""),
        symbol=params.get("symbol", ""),
        direction=params.get("direction", "WAIT"),
        decision=params.get("decision", "NO_TRADE"),
        score=params.get("score", 0),
        confidence=params.get("confidence", 0),
        data_freshness=params.get("data_freshness", "live"),
        market_snapshot=params.get("market_snapshot", {}),
    )

    plan = _get().build_plan(
        decision=ai_decision,
        price=params.get("price"),
        context_snap=params.get("context_snap"),
        indicator_snap=params.get("indicator_snap"),
        structure_snap=params.get("structure_snap"),
        mtf_snap=params.get("mtf_snap"),
        sr_snap=params.get("sr_snap"),
        capital=params.get("capital", 100000.0),
        risk_percent_config=params.get("risk_percent", 2.0),
    )

    _plans[plan.plan_id] = plan
    _history.append(plan)

    result = plan.to_dict()
    result["note"] = "Analysis only. No broker order was placed."
    return result


@router.get("/api/trade-plans/latest")
async def latest_trade_plan(symbol: str = Query("NIFTY 50")):
    """Get the latest TradePlan for a symbol."""
    for plan in reversed(_history):
        if plan.symbol == symbol:
            return plan.to_dict()
    return {"plan": None, "message": "No trade plan yet"}


@router.get("/api/trade-plans/{plan_id}")
async def get_trade_plan(plan_id: str):
    """Get a specific TradePlan by ID."""
    plan = _plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="TradePlan not found")
    return plan.to_dict()


@router.get("/api/trade-plans/history")
async def trade_plan_history(limit: int = Query(50)):
    """Get TradePlan history."""
    return {"plans": [p.to_dict() for p in _history[-limit:]]}
