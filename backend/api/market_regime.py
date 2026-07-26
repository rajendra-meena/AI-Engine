"""Market Regime API routes — Phase 58 endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException

from market_regime.engine import RegimeEngine
from market_regime.strategy_router import StrategyRouter
from market_regime.regime_detector import RegimeDetector, REGIME_LIST
from market_regime.regime_transition import RegimeTransitionEngine
from market_regime.explanation_engine import RegimeExplanationEngine
from market_regime.confidence_modifier import RegimeConfidenceModifier
from market_regime.performance_analytics import RegimePerformanceAnalytics
from market_regime.strategy_comparison import StrategyComparisonEngine
from market_regime.snapshot import RegimeSnapshot
from market_regime.database import init_regime_tables, _get_db

router = APIRouter(tags=["regime"])

_engine: RegimeEngine | None = None
_tables_initialized = False


def set_regime_engine(engine: RegimeEngine):
    global _engine
    _engine = engine


def _get() -> RegimeEngine:
    assert _engine is not None, "RegimeEngine not initialized"
    return _engine


def _ensure_tables():
    global _tables_initialized
    if not _tables_initialized:
        init_regime_tables()
        _tables_initialized = True


def _load_predictions():
    """Fetch predictions with outcomes from learning database."""
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


def _organize(predictions: list[dict]) -> tuple[dict, dict]:
    outcomes: dict = {}
    feedbacks: dict = {}
    for p in predictions:
        pid = p.get("id") or p.get("prediction_id", "")
        if any(k in p for k in ("actual_return", "max_favorable_excursion")):
            outcomes[pid] = p
        if any(k in p for k in ("entry_slippage", "gross_pnl")):
            feedbacks[pid] = p
    return outcomes, feedbacks


@router.get("/api/regime/current")
async def regime_current(symbol: str = Query("NIFTY 50")):
    """Get current detected regime with strategy recommendation."""
    snap = _get().latest(symbol)
    if snap is None:
        raise HTTPException(status_code=404, detail="No regime data available")
    rec = StrategyRouter.get_best_strategy(snap.get("regime", ""))
    snap["strategy_recommendation"] = rec
    return snap


@router.get("/api/regime/history")
async def regime_history(symbol: str = Query("NIFTY 50"), count: int = Query(100, le=500)):
    """Regime detection history."""
    return {"snapshots": _get().history(symbol, count)}


@router.get("/api/regime/transitions")
async def regime_transitions(symbol: str = Query("NIFTY 50"), count: int = Query(50, le=200)):
    """Regime transition history."""
    _ensure_tables()
    db = _get_db()
    try:
        rows = db.execute(
            "SELECT * FROM regime_transition_history WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?",
            (symbol, count),
        ).fetchall()
        return {"transitions": [dict(r) for r in rows]}
    finally:
        db.close()


@router.get("/api/regime/strategies")
async def regime_strategies(symbol: str = Query("NIFTY 50")):
    """Get recommended strategies for current regime."""
    snap = _get().latest(symbol)
    if snap is None:
        raise HTTPException(status_code=404, detail="No regime data available")
    regime = snap.get("regime", "")
    rec = StrategyRouter.get_best_strategy(regime)
    rec["current_regime"] = regime
    rec["regime_confidence"] = snap.get("confidence", 0)
    return rec


@router.get("/api/regime/performance")
async def regime_performance():
    """Win rate, PnL, drawdown per regime."""
    _ensure_tables()
    db = _get_db()
    try:
        perf = RegimePerformanceAnalytics.compute_regime_performance(db)
        return {"regimes": perf}
    finally:
        db.close()


@router.get("/api/regime/comparison")
async def regime_comparison():
    """Strategy comparison across all strategies."""
    predictions = _load_predictions()
    outcomes, feedbacks = _organize(predictions)
    comparison = StrategyComparisonEngine.compare_all(predictions, outcomes, feedbacks)
    return {"comparison": comparison}


@router.get("/api/regime/explain")
async def regime_explain(symbol: str = Query("NIFTY 50")):
    """Get human-readable regime explanation."""
    snap = _get().latest(symbol)
    if snap is None:
        raise HTTPException(status_code=404, detail="No regime data available")

    regime = snap.get("regime", "")
    reg_conf = snap.get("confidence", 0)
    factors = snap.get("supporting_factors", [])
    rec = StrategyRouter.get_best_strategy(regime)

    snap_obj = RegimeSnapshot(
        symbol=symbol,
        regime=regime,
        confidence=reg_conf,
        supporting_factors=tuple(factors),
        stability_score=snap.get("stability_score", 0),
        regime_age_bars=snap.get("regime_age_bars", 0),
    )

    explanation = RegimeExplanationEngine.explain(snap_obj, rec)
    return explanation.to_dict()


@router.post("/api/regime/analyze")
async def regime_analyze(symbol: str = Query("NIFTY 50")):
    """Force re-analysis and return current regime."""
    snap = _get().latest(symbol)
    if snap is None:
        raise HTTPException(status_code=404, detail="No regime data")
    return snap


@router.get("/api/regime/list")
async def regime_list():
    """Return all 14 regime types with descriptions."""
    from market_regime.explanation_engine import FACTOR_DESCRIPTIONS
    regimes = []
    for name in REGIME_LIST:
        from market_regime.strategy_router import REGIME_STRATEGY_MAP
        rec = REGIME_STRATEGY_MAP.get(name, {})
        regimes.append({
            "name": name,
            "category": "UNKNOWN",
            "display_name": name.replace("_", " ").title(),
            "primary_strategy": rec.get("primary", ""),
            "description": FACTOR_DESCRIPTIONS.get(name, name.replace("_", " ").lower()),
        })
    return {"regimes": regimes}


@router.get("/api/regime/confidence-adjustment")
async def regime_confidence_adjustment(
    symbol: str = Query("NIFTY 50"),
    base_confidence: int = Query(50, ge=0, le=100),
):
    """Get regime-based confidence adjustment."""
    snap = _get().latest(symbol)
    regime = snap.get("regime") if snap else None
    reg_conf = snap.get("confidence", 50) if snap else 50
    adjustment = RegimeConfidenceModifier.adjust(base_confidence, regime, reg_conf)
    adjustment["current_regime"] = regime
    return adjustment
