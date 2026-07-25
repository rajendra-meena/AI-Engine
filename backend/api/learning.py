"""
MarketMind AI — Learning & Trade Feedback API Routes
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from learning import engine as lrn
from learning.database import init_learning_tables

router = APIRouter(tags=["learning"])

_tables_initialized = False


def ensure_tables():
    global _tables_initialized
    if not _tables_initialized:
        init_learning_tables()
        _tables_initialized = True


@router.get("/api/learning/dashboard")
async def learning_dashboard():
    """Get learning dashboard overview metrics."""
    ensure_tables()
    return {
        "performance": lrn.get_performance_metrics(),
        "calibration": lrn.get_calibration_data(),
        "regime_performance": lrn.get_regime_performance(),
        "error_analysis": lrn.get_error_analysis(),
        "blocked_analysis": lrn.get_blocked_trade_analysis(),
        "recommendations_pending": len(lrn.get_recommendations("NEW")),
    }


@router.get("/api/learning/predictions")
async def learning_predictions(
    limit: int = Query(100),
    offset: int = Query(0),
    symbol: str | None = Query(None),
    regime: str | None = Query(None),
):
    """Get prediction journal entries."""
    ensure_tables()
    return {
        "predictions": lrn.get_predictions(limit, offset, symbol, regime),
        "total": lrn.get_performance_metrics()["total_predictions"],
    }


@router.post("/api/learning/predictions")
async def create_prediction(pred: dict[str, Any]):
    """Record a new prediction in the journal."""
    ensure_tables()
    pid = lrn.record_prediction(
        symbol=pred.get("symbol", ""),
        interval=pred.get("interval", "15m"),
        decision=pred.get("decision", "NO_TRADE"),
        score=pred.get("score", 0),
        confidence=pred.get("confidence", 0),
        direction=pred.get("direction"),
        exchange=pred.get("exchange", "NSE"),
        risk_score=pred.get("risk_score"),
        risk_level=pred.get("risk_level"),
        entry_price=pred.get("entry_price"),
        stop_loss=pred.get("stop_loss"),
        target=pred.get("target"),
        risk_reward=pred.get("risk_reward"),
        strategy_id=pred.get("strategy_id"),
        model_id=pred.get("model_id"),
        market_regime=pred.get("market_regime"),
        trend=pred.get("trend"),
        institutional_bias=pred.get("institutional_bias"),
        mtf_alignment=pred.get("mtf_alignment"),
        volatility=pred.get("volatility"),
        momentum=pred.get("momentum"),
        feature_snapshot=pred.get("feature_snapshot"),
        indicator_snapshot=pred.get("indicator_snapshot"),
        pattern_snapshot=pred.get("pattern_snapshot"),
        structure_snapshot=pred.get("structure_snapshot"),
        sr_snapshot=pred.get("sr_snapshot"),
        regime=pred.get("regime"),
        user_id=pred.get("user_id", ""),
    )
    return {"success": True, "prediction_id": pid}


@router.post("/api/learning/predictions/{pid}/outcome")
async def record_prediction_outcome(pid: str, outcome: dict[str, Any]):
    """Record outcome for a prediction."""
    ensure_tables()
    lrn.record_outcome(
        prediction_id=pid,
        outcome_5m=outcome.get("outcome_5m"),
        outcome_15m=outcome.get("outcome_15m"),
        outcome_30m=outcome.get("outcome_30m"),
        outcome_60m=outcome.get("outcome_60m"),
        outcome_session=outcome.get("outcome_session"),
        outcome_eod=outcome.get("outcome_eod"),
        max_favorable=outcome.get("max_favorable_excursion"),
        max_adverse=outcome.get("max_adverse_excursion"),
        target_hit=outcome.get("target_hit"),
        stop_loss_hit=outcome.get("stop_loss_hit"),
        actual_direction=outcome.get("actual_direction"),
        actual_return=outcome.get("actual_return"),
        maximum_return=outcome.get("maximum_return"),
        maximum_drawdown=outcome.get("maximum_drawdown"),
        error_category=outcome.get("error_category"),
        error_reason=outcome.get("error_reason"),
    )
    lrn.update_calibration()
    return {"success": True}


@router.get("/api/learning/performance")
async def learning_performance():
    """Get aggregate learning performance metrics."""
    ensure_tables()
    return lrn.get_performance_metrics()


@router.get("/api/learning/regimes")
async def learning_regimes():
    """Get performance breakdown by market regime."""
    ensure_tables()
    return {"regimes": lrn.get_regime_performance()}


@router.get("/api/learning/errors")
async def learning_errors():
    """Get error analysis distribution."""
    ensure_tables()
    return {"errors": lrn.get_error_analysis()}


@router.get("/api/learning/calibration")
async def learning_calibration():
    """Get confidence calibration data."""
    ensure_tables()
    return {"buckets": lrn.get_calibration_data()}


@router.post("/api/learning/calibration/refresh")
async def refresh_calibration():
    """Recalculate calibration buckets."""
    ensure_tables()
    lrn.update_calibration()
    return {"success": True}


@router.get("/api/learning/recommendations")
async def learning_recommendations(status: str | None = Query(None)):
    """Get learning recommendations."""
    ensure_tables()
    return {"recommendations": lrn.get_recommendations(status)}


@router.post("/api/learning/recommendations/{rid}/approve")
async def approve_recommendation(rid: str):
    """Approve a learning recommendation."""
    ensure_tables()
    lrn.update_recommendation_status(rid, "APPROVED")
    return {"success": True}


@router.post("/api/learning/recommendations/{rid}/reject")
async def reject_recommendation(rid: str, reason: str = Query("")):
    """Reject a learning recommendation."""
    ensure_tables()
    lrn.update_recommendation_status(rid, "REJECTED", reason)
    return {"success": True}


@router.get("/api/learning/blocked")
async def learning_blocked():
    """Get blocked trade analysis."""
    ensure_tables()
    return lrn.get_blocked_trade_analysis()


@router.post("/api/learning/run")
async def run_learning():
    """Trigger learning run — recalculate calibration, generate recommendations."""
    ensure_tables()
    lrn.update_calibration()
    return {
        "success": True,
        "message": "Learning run completed",
        "calibration_updated": True,
    }
