"""
MarketMind AI — Learning & Trade Feedback API Routes

Connects the Learning Engine to the live trading pipeline.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from learning import engine as lrn
from learning import integration as lri
from learning.database import init_learning_tables

router = APIRouter(tags=["learning"])

_tables_initialized = False


def ensure_tables():
    global _tables_initialized
    if not _tables_initialized:
        init_learning_tables()
        _tables_initialized = True


# ── Dashboard ──


@router.get("/api/learning/dashboard")
async def learning_dashboard():
    """Get learning dashboard overview with all metrics."""
    ensure_tables()
    return {
        "performance": lrn.get_performance_metrics(),
        "calibration": lrn.get_calibration_data(),
        "regime_performance": lrn.get_regime_performance(),
        "error_analysis": lrn.get_error_analysis(),
        "blocked_analysis": lrn.get_blocked_trade_analysis(),
        "ai_vs_ml": lri.get_ai_vs_ml_comparison(),
        "data_quality": lri.check_data_quality(),
        "recommendations_pending": len(lrn.get_recommendations("NEW")),
    }


# ── Predictions ──


@router.get("/api/learning/predictions")
async def learning_predictions(
    limit: int = Query(100),
    offset: int = Query(0),
    symbol: str | None = Query(None),
    regime: str | None = Query(None),
):
    """Get prediction journal entries with outcomes."""
    ensure_tables()
    results = lrn.get_predictions(limit, offset, symbol, regime)
    total = lrn.get_performance_metrics()["total_predictions"]
    return {"predictions": results, "total": total, "limit": limit, "offset": offset}


@router.post("/api/learning/predictions")
async def create_prediction(pred: dict[str, Any]):
    """Record a prediction with full integration traceability."""
    ensure_tables()
    pid = lri.journal_ai_prediction(
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
        model_version=pred.get("model_version"),
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
        ml_prediction=pred.get("ml_prediction"),
        ml_confidence=pred.get("ml_confidence"),
        prediction_source=pred.get("prediction_source", "ai_engine"),
        correlation_id=pred.get("correlation_id"),
        user_id=pred.get("user_id", ""),
    )
    return {"success": True, "prediction_id": pid}


@router.get("/api/learning/predictions/{pid}")
async def get_prediction(pid: str):
    """Get a single prediction with full details."""
    ensure_tables()
    predictions = lrn.get_predictions(limit=1, offset=0)
    for p in predictions:
        if p["id"] == pid:
            return p
    return {"error": "Not found"}


# ── Outcomes ──


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
        time_exit=outcome.get("time_exit"),
        manual_exit=outcome.get("manual_exit"),
        expired=outcome.get("expired"),
        actual_direction=outcome.get("actual_direction"),
        actual_return=outcome.get("actual_return"),
        maximum_return=outcome.get("maximum_return"),
        maximum_drawdown=outcome.get("maximum_drawdown"),
        error_category=outcome.get("error_category"),
        error_reason=outcome.get("error_reason"),
    )
    lrn.update_calibration()
    return {"success": True}


@router.get("/api/learning/outcomes")
async def learning_outcomes(limit: int = Query(100), offset: int = Query(0)):
    """Get all prediction outcomes."""
    ensure_tables()
    predictions = lrn.get_predictions(limit, offset)
    outcomes = [p for p in predictions if p.get("actual_return") is not None]
    return {"outcomes": outcomes, "total": len(outcomes)}


# ── Performance ──


@router.get("/api/learning/performance")
async def learning_performance():
    """Get aggregate learning performance metrics."""
    ensure_tables()
    return lrn.get_performance_metrics()


# ── Regimes ──


@router.get("/api/learning/regimes")
async def learning_regimes():
    """Get performance breakdown by market regime."""
    ensure_tables()
    return {"regimes": lrn.get_regime_performance()}


# ── Errors ──


@router.get("/api/learning/errors")
async def learning_errors():
    """Get error analysis distribution."""
    ensure_tables()
    return {"errors": lrn.get_error_analysis()}


# ── Calibration ──


@router.get("/api/learning/calibration")
async def learning_calibration():
    """Get confidence calibration data."""
    ensure_tables()
    return {"buckets": lrn.get_calibration_data()}


@router.post("/api/learning/calibration/refresh")
async def refresh_calibration():
    """Recalculate calibration buckets from all prediction data."""
    ensure_tables()
    lrn.update_calibration()
    return {"success": True, "buckets": lrn.get_calibration_data()}


# ── AI vs ML ──


@router.get("/api/learning/ai-vs-ml")
async def learning_ai_vs_ml():
    """Compare AI predictions vs ML predictions vs actual outcomes."""
    ensure_tables()
    return lri.get_ai_vs_ml_comparison()


# ── Blocked Trades ──


@router.get("/api/learning/blocked")
async def learning_blocked():
    """Get blocked trade analysis."""
    ensure_tables()
    return lrn.get_blocked_trade_analysis()


@router.post("/api/learning/blocked")
async def record_blocked_trade(blocked: dict[str, Any]):
    """Record a blocked trade from the Risk Firewall."""
    ensure_tables()
    bid = lri.record_blocked_trade(
        prediction_id=blocked.get("prediction_id"),
        symbol=blocked.get("symbol", ""),
        direction=blocked.get("direction"),
        intended_entry=blocked.get("intended_entry"),
        intended_sl=blocked.get("intended_sl"),
        intended_tp=blocked.get("intended_tp"),
        intended_quantity=blocked.get("intended_quantity", 0),
        ai_score=blocked.get("ai_score"),
        ai_confidence=blocked.get("ai_confidence"),
        strategy=blocked.get("strategy"),
        blocked_by=blocked.get("blocked_by", "unknown"),
        block_reason=blocked.get("block_reason", ""),
        risk_score=blocked.get("risk_score"),
        market_regime=blocked.get("market_regime"),
        correlation_id=blocked.get("correlation_id"),
    )
    return {"success": True, "blocked_id": bid}


# ── Trade Feedback ──


@router.post("/api/learning/trade-feedback")
async def record_trade_feedback(feedback: dict[str, Any]):
    """Record trade feedback from an executed order."""
    ensure_tables()
    tfid = lri.record_trade_feedback(
        prediction_id=feedback.get("prediction_id", ""),
        entry_price=feedback.get("entry_price", 0),
        exit_price=feedback.get("exit_price"),
        quantity=feedback.get("quantity", 0),
        direction=feedback.get("direction", "BUY"),
        entry_slippage=feedback.get("entry_slippage"),
        exit_slippage=feedback.get("exit_slippage"),
        commission=feedback.get("commission", 0),
        taxes=feedback.get("taxes", 0),
        brokerage=feedback.get("brokerage", 0),
        gross_pnl=feedback.get("gross_pnl"),
        net_pnl=feedback.get("net_pnl"),
        planned_risk=feedback.get("planned_risk"),
        actual_risk=feedback.get("actual_risk"),
        planned_rr=feedback.get("planned_rr"),
        actual_rr=feedback.get("actual_rr"),
        holding_duration=feedback.get("holding_duration"),
        exit_reason=feedback.get("exit_reason"),
        risk_firewall_result=feedback.get("risk_firewall_result"),
    )
    return {"success": True, "feedback_id": tfid}


# ── Recommendations ──


@router.get("/api/learning/recommendations")
async def learning_recommendations(
    status: str | None = Query(None),
    limit: int = Query(50),
):
    """Get learning recommendations, optionally filtered by status."""
    ensure_tables()
    recs = lrn.get_recommendations(status)[:limit]
    return {"recommendations": recs, "total": len(recs)}


@router.post("/api/learning/recommendations/{rid}/approve")
async def approve_recommendation(rid: str):
    """Approve a learning recommendation for implementation."""
    ensure_tables()
    lrn.update_recommendation_status(rid, "APPROVED")
    return {"success": True}


@router.post("/api/learning/recommendations/{rid}/reject")
async def reject_recommendation(rid: str, reason: str = Query("")):
    """Reject a learning recommendation with optional reason."""
    ensure_tables()
    lrn.update_recommendation_status(rid, "REJECTED", reason)
    return {"success": True}


@router.post("/api/learning/recommendations")
async def create_recommendation(rec: dict[str, Any]):
    """Create a new learning recommendation."""
    ensure_tables()
    rid = lri.create_learning_recommendation(
        title=rec.get("title", ""),
        finding=rec.get("finding", ""),
        evidence=rec.get("evidence", ""),
        sample_count=rec.get("sample_count", 0),
        confidence=rec.get("confidence", 0),
        expected_impact=rec.get("expected_impact", ""),
        risk=rec.get("risk", ""),
        recommendation=rec.get("recommendation", ""),
        category=rec.get("category", ""),
        action=rec.get("action"),
    )
    return {"success": True, "recommendation_id": rid}


# ── Data Quality ──


@router.get("/api/learning/data-quality")
async def learning_data_quality():
    """Check data integrity across all learning tables."""
    ensure_tables()
    return lri.check_data_quality()


# ── Learning Run ──


@router.post("/api/learning/run")
async def run_learning():
    """Trigger learning run: recalculate calibration + generate analyses."""
    ensure_tables()
    lrn.update_calibration()
    return {
        "success": True,
        "message": "Learning run completed",
        "calibration_updated": True,
    }
