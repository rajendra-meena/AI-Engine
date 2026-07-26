"""AI Performance Analytics API routes — Phase 57 endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException

from ai_performance.database import init_ai_performance_tables, _get_db
from ai_performance.trade_evaluator import TradeEvaluator
from ai_performance.strategy_engine import StrategyPerformanceEngine
from ai_performance.calibration_engine import ConfidenceCalibrationEngine
from ai_performance.pattern_analyzer import PatternPerformanceAnalyzer
from ai_performance.market_condition import MarketConditionAnalyzer
from ai_performance.mistake_classifier import MistakeClassifier
from ai_performance.dataset_builder import AIPerformanceDatasetBuilder

router = APIRouter(tags=["ai_performance"])

_tables_initialized = False


def _ensure_tables():
    global _tables_initialized
    if not _tables_initialized:
        init_ai_performance_tables()
        _tables_initialized = True


def _get_learning_data():
    """Fetch predictions, outcomes, and feedbacks from learning database."""
    from learning.engine import _get_db as get_learning_db
    try:
        ldb = get_learning_db()
        rows = ldb.execute(
            "SELECT pj.*, po.*, tf.* FROM prediction_journal pj "
            "LEFT JOIN prediction_outcome po ON po.prediction_id = pj.id "
            "LEFT JOIN trade_feedback tf ON tf.prediction_id = pj.id "
            "ORDER BY pj.created_at DESC"
        ).fetchall()
        predictions = [dict(r) for r in rows]
        ldb.close()
        return predictions
    except Exception:
        return []


def _organize_outcomes_feedbacks(predictions: list[dict]) -> tuple[dict, dict]:
    """Split flat prediction rows into outcomes and feedbacks dicts keyed by id."""
    outcomes: dict = {}
    feedbacks: dict = {}
    for p in predictions:
        pid = p.get("id") or p.get("prediction_id", "")
        if any(k in p for k in ("actual_return", "max_favorable_excursion", "error_category")):
            outcomes[pid] = p
        if any(k in p for k in ("entry_slippage", "gross_pnl", "net_pnl")):
            feedbacks[pid] = p
    return outcomes, feedbacks


@router.get("/api/ai/performance/overview")
async def ai_performance_overview():
    """Aggregate trade evaluation stats."""
    _ensure_tables()
    db = _get_db()
    try:
        total = db.execute("SELECT COUNT(*) as c FROM ai_perf_trade_evaluation").fetchone()
        avg_score = db.execute("SELECT AVG(overall_score) as a FROM ai_perf_trade_evaluation").fetchone()
        by_class = db.execute(
            "SELECT outcome_class, COUNT(*) as c FROM ai_perf_trade_evaluation GROUP BY outcome_class"
        ).fetchall()
        return {
            "total_evaluated": total["c"] if total else 0,
            "avg_score": round(avg_score["a"], 1) if avg_score and avg_score["a"] else 0,
            "outcome_distribution": {r["outcome_class"]: r["c"] for r in by_class} if by_class else {},
        }
    finally:
        db.close()


@router.get("/api/ai/performance/strategies")
async def ai_performance_strategies():
    """Per-strategy performance metrics."""
    _ensure_tables()
    predictions = _get_learning_data()
    outcomes, feedbacks = _organize_outcomes_feedbacks(predictions)
    strategies = StrategyPerformanceEngine.compute_all_strategies(predictions, outcomes, feedbacks)
    return {"strategies": strategies}


@router.get("/api/ai/performance/patterns")
async def ai_performance_patterns():
    """Per-pattern performance."""
    _ensure_tables()
    predictions = _get_learning_data()
    outcomes, feedbacks = _organize_outcomes_feedbacks(predictions)
    patterns = PatternPerformanceAnalyzer.compute_pattern_performance(predictions, outcomes, feedbacks)
    return {"patterns": patterns}


@router.get("/api/ai/performance/market")
async def ai_performance_market():
    """Market condition performance breakdown."""
    _ensure_tables()
    predictions = _get_learning_data()
    outcomes, _ = _organize_outcomes_feedbacks(predictions)
    conditions = MarketConditionAnalyzer.compute_condition_performance(predictions, outcomes)
    return {"conditions": conditions}


@router.get("/api/ai/performance/calibration")
async def ai_performance_calibration():
    """Confidence calibration (reliability curve + ECE + bias)."""
    predictions = _get_learning_data()
    outcomes, _ = _organize_outcomes_feedbacks(predictions)

    calibration = ConfidenceCalibrationEngine.compute_calibration_error(predictions, outcomes)
    confidence_acc = ConfidenceCalibrationEngine.compute_confidence_accuracy(predictions, outcomes)
    calibration["confidence_accuracy"] = confidence_acc
    return calibration


@router.get("/api/ai/performance/mistakes")
async def ai_performance_mistakes():
    """Mistake classification summary + details."""
    _ensure_tables()
    predictions = _get_learning_data()
    outcomes, feedbacks = _organize_outcomes_feedbacks(predictions)
    mistakes = MistakeClassifier.classify_batch(predictions, outcomes, feedbacks)
    summary = MistakeClassifier.get_mistake_summary(mistakes)
    return {"summary": summary, "mistakes": mistakes}


@router.get("/api/ai/performance/trades")
async def ai_performance_trades(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    outcome_class: str | None = Query(None),
):
    """Trade evaluations with filtering."""
    _ensure_tables()
    db = _get_db()
    try:
        where = ""
        params: list = []
        if outcome_class:
            where = "WHERE outcome_class = ?"
            params.append(outcome_class)

        count_row = db.execute(f"SELECT COUNT(*) as c FROM ai_perf_trade_evaluation {where}", params).fetchone()
        total = count_row["c"] if count_row else 0

        rows = db.execute(
            f"SELECT * FROM ai_perf_trade_evaluation {where} ORDER BY evaluated_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        return {"trades": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}
    finally:
        db.close()


@router.get("/api/ai/performance/dashboard")
async def ai_performance_dashboard():
    """Full dashboard data for performance overview."""
    predictions = _get_learning_data()
    outcomes, feedbacks = _organize_outcomes_feedbacks(predictions)

    strategies = StrategyPerformanceEngine.compute_all_strategies(predictions, outcomes, feedbacks)
    patterns = PatternPerformanceAnalyzer.compute_pattern_performance(predictions, outcomes, feedbacks)
    conditions = MarketConditionAnalyzer.compute_condition_performance(predictions, outcomes)
    calibration = ConfidenceCalibrationEngine.compute_calibration_error(predictions, outcomes)
    confidence_acc = ConfidenceCalibrationEngine.compute_confidence_accuracy(predictions, outcomes)
    mistakes = MistakeClassifier.classify_batch(predictions, outcomes, feedbacks)
    mistake_summary = MistakeClassifier.get_mistake_summary(mistakes)

    _ensure_tables()
    db = _get_db()
    try:
        total = db.execute("SELECT COUNT(*) as c FROM ai_perf_trade_evaluation").fetchone()
        avg_score = db.execute("SELECT AVG(overall_score) as a FROM ai_perf_trade_evaluation").fetchone()
        by_class = db.execute(
            "SELECT outcome_class, COUNT(*) as c FROM ai_perf_trade_evaluation GROUP BY outcome_class"
        ).fetchall()
    finally:
        db.close()

    return {
        "overview": {
            "total_evaluated": total["c"] if total else 0,
            "avg_score": round(avg_score["a"], 1) if avg_score and avg_score["a"] else 0,
            "outcome_distribution": {r["outcome_class"]: r["c"] for r in by_class} if by_class else {},
        },
        "strategies": strategies,
        "patterns": patterns,
        "market_conditions": conditions,
        "calibration": {**calibration, "confidence_accuracy": confidence_acc},
        "mistakes": {"summary": mistake_summary, "mistakes": mistakes[:20]},
        "trades_count": (total["c"] if total else 0),
    }


@router.post("/api/ai/performance/evaluate")
async def ai_performance_evaluate():
    """Trigger full re-evaluation of all un-evaluated trades."""
    _ensure_tables()
    predictions = _get_learning_data()
    outcomes, feedbacks = _organize_outcomes_feedbacks(predictions)

    db = _get_db()
    count = 0
    try:
        for p in predictions:
            pid = p.get("id") or p.get("prediction_id", "")
            # Skip if already evaluated
            existing = db.execute(
                "SELECT id FROM ai_perf_trade_evaluation WHERE prediction_id = ?", (pid,)
            ).fetchone()
            if existing:
                continue
            o = outcomes.get(pid)
            f = feedbacks.get(pid)
            evaluation = TradeEvaluator.evaluate_single(p, o, f)
            if evaluation.get("overall_score", 0) > 0:
                TradeEvaluator.store_evaluation(db, pid, evaluation)
                count += 1
    finally:
        db.close()

    return {"success": True, "evaluated": count}


@router.get("/api/ai/performance/export")
async def ai_performance_export(
    fmt: str = Query("json", regex="^(json|csv)$"),
    limit: int = Query(1000, le=10000),
):
    """Export evaluation dataset for offline training."""
    _ensure_tables()
    db = _get_db()
    try:
        if fmt == "csv":
            data = AIPerformanceDatasetBuilder.export_dataset(db, "csv", limit)
            from fastapi.responses import Response
            return Response(content=data, media_type="text/csv",
                            headers={"Content-Disposition": "attachment; filename=ai_performance_dataset.csv"})
        else:
            data = AIPerformanceDatasetBuilder.export_dataset(db, "json", limit)
            return {"records": data, "count": len(data) if isinstance(data, list) else 0}
    finally:
        db.close()
