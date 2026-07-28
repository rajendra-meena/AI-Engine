"""AI Decision API routes — Phase 55 + Phase 56 endpoints."""

from fastapi import APIRouter, Query, HTTPException

from core.symbols import get_canonical_symbol
from ai_decision.engine import AIDecisionEngine
from ai_decision.modules.detailed_confidence import DetailedConfidenceEngine
from ai_decision.modules.trade_quality import TradeQualityScorer
from ai_decision.modules.mtf_agreement import MultiTFAgreement
from ai_decision.modules.false_signal import FalseSignalDetector
from ai_decision.modules.signal_validator import SignalValidator
from ai_decision.modules.confidence_adjuster import DynamicConfidenceAdjuster
from ai_decision.modules.ai_explainer import AIExplainer
from ai_decision.modules.trade_approval import TradeApprovalEngine
from ai_decision.modules.dataset_builder import LearningDatasetBuilder
from ai_decision.modules.orchestrator import EnhancedOrchestrator

router = APIRouter(tags=["ai"])

_engine: AIDecisionEngine | None = None


def set_ai_decision_engine(engine: AIDecisionEngine):
    global _engine
    _engine = engine


def _get() -> AIDecisionEngine:
    assert _engine is not None, "AIDecisionEngine not initialized"
    return _engine


def _snap_kwargs(snap: dict | None) -> dict:
    """Extract sub-snapshot kwargs from a full AI decision snapshot."""
    if not snap:
        return {}
    ms = snap.get("market_snapshot", {})
    return {
        "decision_snap": snap,
        "context_snap": snap.get("evidence", {}),
        "indicator_snap": ms,
        "structure_snap": ms,
        "pattern_snap": ms,
        "mtf_snap": ms,
        "sr_snap": ms,
        "market_snapshot": ms,
    }


@router.get("/api/ai/status")
async def ai_status():
    return _get().get_stats()


@router.get("/api/ai/barrier-diagnostics")
async def ai_barrier_diagnostics():
    """Version-barrier diagnostics for the AI decision engine."""
    engine = _get()
    stats = engine.get_stats()
    return {
        "units": stats.get("units", 0),
        "barrier_diagnostics": stats.get("barrier_diagnostics", {}),
        "total_decisions": stats.get("total_decisions", 0),
    }


@router.get("/api/ai/latest")
async def ai_latest(symbol: str = Query("NIFTY 50")):
    symbol = get_canonical_symbol(symbol)
    snap = _get().latest(symbol)
    if snap is None:
        raise HTTPException(status_code=404, detail="No AI decision data")
    return snap


@router.get("/api/ai/history")
async def ai_history(symbol: str = Query("NIFTY 50"), count: int = Query(100)):
    symbol = get_canonical_symbol(symbol)
    return {"snapshots": _get().history(symbol, count)}


# ── Phase 56 Endpoints ──


@router.get("/api/ai/confidence")
async def ai_confidence(symbol: str = Query("NIFTY 50")):
    """Return detailed confidence breakdown (10 factors)."""
    symbol = get_canonical_symbol(symbol)
    snap = _get().latest(symbol)
    kwargs = _snap_kwargs(snap)
    return DetailedConfidenceEngine.evaluate(
        context_snap=kwargs.get("context_snap"),
        indicator_snap=kwargs.get("indicator_snap"),
        structure_snap=kwargs.get("structure_snap"),
        pattern_snap=kwargs.get("pattern_snap"),
        mtf_snap=kwargs.get("mtf_snap"),
        sr_snap=kwargs.get("sr_snap"),
        decision_snap=kwargs.get("decision_snap"),
    )


@router.get("/api/ai/decision")
async def ai_enriched_decision(symbol: str = Query("NIFTY 50")):
    """Return enriched decision with all Phase 56 data."""
    symbol = get_canonical_symbol(symbol)
    snap = _get().latest(symbol)
    if snap is None:
        raise HTTPException(status_code=404, detail="No AI decision data")
    kwargs = _snap_kwargs(snap)
    enriched = EnhancedOrchestrator.orchestrate(
        score_result={"score": snap.get("score", 0), "grade": snap.get("score_grade", "VERY_LOW")},
        confidence_result={"confidence": snap.get("confidence", 0), "grade": snap.get("confidence_grade", "VERY_LOW")},
        risk_result={"risk_level": snap.get("risk_level", "EXTREME"), "risk_score": snap.get("risk_score", 0)},
        trade_plan={"direction": snap.get("trade_plan", {}).get("direction", "NONE"), "plan_valid": snap.get("trade_plan", {}).get("valid", False)},
        context_snap=kwargs.get("context_snap"),
        indicator_snap=kwargs.get("indicator_snap"),
        structure_snap=kwargs.get("structure_snap"),
        pattern_snap=kwargs.get("pattern_snap"),
        mtf_snap=kwargs.get("mtf_snap"),
        sr_snap=kwargs.get("sr_snap"),
        decision_snap=snap,
        market_snapshot=kwargs.get("market_snapshot"),
    )
    return enriched


@router.get("/api/ai/quality")
async def ai_quality(symbol: str = Query("NIFTY 50")):
    """Return trade quality score and grade."""
    symbol = get_canonical_symbol(symbol)
    snap = _get().latest(symbol)
    kwargs = _snap_kwargs(snap)
    return TradeQualityScorer.evaluate(
        decision_snap=kwargs.get("decision_snap"),
        context_snap=kwargs.get("context_snap"),
        indicator_snap=kwargs.get("indicator_snap"),
        pattern_snap=kwargs.get("pattern_snap"),
        sr_snap=kwargs.get("sr_snap"),
        mtf_snap=kwargs.get("mtf_snap"),
    )


@router.get("/api/ai/explain")
async def ai_explain(symbol: str = Query("NIFTY 50")):
    """Return WHY BUY / WHY SELL / WHY NO TRADE explanations."""
    symbol = get_canonical_symbol(symbol)
    snap = _get().latest(symbol)
    kwargs = _snap_kwargs(snap)
    return AIExplainer.explain(
        decision_snap=kwargs.get("decision_snap"),
        context_snap=kwargs.get("context_snap"),
        indicator_snap=kwargs.get("indicator_snap"),
        structure_snap=kwargs.get("structure_snap"),
        pattern_snap=kwargs.get("pattern_snap"),
        mtf_snap=kwargs.get("mtf_snap"),
        sr_snap=kwargs.get("sr_snap"),
    )


@router.get("/api/ai/agreement")
async def ai_agreement(symbol: str = Query("NIFTY 50")):
    """Return MTF agreement percentage."""
    symbol = get_canonical_symbol(symbol)
    snap = _get().latest(symbol)
    kwargs = _snap_kwargs(snap)
    return MultiTFAgreement.evaluate(mtf_snap=kwargs.get("mtf_snap"))


@router.get("/api/ai/rejections")
async def ai_rejections(symbol: str = Query("NIFTY 50")):
    """Return false signal detections."""
    symbol = get_canonical_symbol(symbol)
    snap = _get().latest(symbol)
    kwargs = _snap_kwargs(snap)
    return FalseSignalDetector.detect(
        context_snap=kwargs.get("context_snap"),
        indicator_snap=kwargs.get("indicator_snap"),
        structure_snap=kwargs.get("structure_snap"),
        sr_snap=kwargs.get("sr_snap"),
    )


@router.post("/api/ai/validate")
async def ai_validate(symbol: str = Query("NIFTY 50")):
    """Run full validation pipeline and return results."""
    symbol = get_canonical_symbol(symbol)
    snap = _get().latest(symbol)
    kwargs = _snap_kwargs(snap)

    signal_val = SignalValidator.validate(
        decision_snap=kwargs.get("decision_snap"),
        context_snap=kwargs.get("context_snap"),
        indicator_snap=kwargs.get("indicator_snap"),
        structure_snap=kwargs.get("structure_snap"),
        pattern_snap=kwargs.get("pattern_snap"),
        mtf_snap=kwargs.get("mtf_snap"),
        sr_snap=kwargs.get("sr_snap"),
    )

    quality = TradeQualityScorer.evaluate(
        decision_snap=kwargs.get("decision_snap"),
        context_snap=kwargs.get("context_snap"),
        indicator_snap=kwargs.get("indicator_snap"),
        pattern_snap=kwargs.get("pattern_snap"),
        sr_snap=kwargs.get("sr_snap"),
        mtf_snap=kwargs.get("mtf_snap"),
    )

    approve = TradeApprovalEngine.approve(
        detailed_confidence=kwargs.get("detailed_confidence"),
        trade_quality=quality,
        mtf_agreement=MultiTFAgreement.evaluate(kwargs.get("mtf_snap")),
        risk_result={"risk_level": (snap or {}).get("risk_level", "EXTREME")},
        signal_validations=signal_val,
        false_signal_check=FalseSignalDetector.detect(
            context_snap=kwargs.get("context_snap"),
            indicator_snap=kwargs.get("indicator_snap"),
            structure_snap=kwargs.get("structure_snap"),
            sr_snap=kwargs.get("sr_snap"),
        ),
        decision_snap=snap,
    )

    return {"signal_validations": signal_val, "trade_quality": quality, "approval": approve}


@router.get("/api/ai/approval")
async def ai_approval(symbol: str = Query("NIFTY 50")):
    """Return final trade approval status."""
    symbol = get_canonical_symbol(symbol)
    snap = _get().latest(symbol)
    kwargs = _snap_kwargs(snap)
    quality = TradeQualityScorer.evaluate(
        decision_snap=kwargs.get("decision_snap"),
        context_snap=kwargs.get("context_snap"),
        indicator_snap=kwargs.get("indicator_snap"),
        pattern_snap=kwargs.get("pattern_snap"),
        sr_snap=kwargs.get("sr_snap"),
        mtf_snap=kwargs.get("mtf_snap"),
    )
    return TradeApprovalEngine.approve(
        detailed_confidence=DetailedConfidenceEngine.evaluate(
            context_snap=kwargs.get("context_snap"),
            indicator_snap=kwargs.get("indicator_snap"),
            structure_snap=kwargs.get("structure_snap"),
            pattern_snap=kwargs.get("pattern_snap"),
            mtf_snap=kwargs.get("mtf_snap"),
            sr_snap=kwargs.get("sr_snap"),
            decision_snap=snap,
        ),
        trade_quality=quality,
        mtf_agreement=MultiTFAgreement.evaluate(kwargs.get("mtf_snap")),
        risk_result={"risk_level": (snap or {}).get("risk_level", "EXTREME")},
        signal_validations=SignalValidator.validate(
            decision_snap=kwargs.get("decision_snap"),
            context_snap=kwargs.get("context_snap"),
            indicator_snap=kwargs.get("indicator_snap"),
            structure_snap=kwargs.get("structure_snap"),
            pattern_snap=kwargs.get("pattern_snap"),
            mtf_snap=kwargs.get("mtf_snap"),
            sr_snap=kwargs.get("sr_snap"),
        ),
        false_signal_check=FalseSignalDetector.detect(
            context_snap=kwargs.get("context_snap"),
            indicator_snap=kwargs.get("indicator_snap"),
            structure_snap=kwargs.get("structure_snap"),
            sr_snap=kwargs.get("sr_snap"),
        ),
        decision_snap=snap,
    )


@router.get("/api/ai/dataset/stats")
async def ai_dataset_stats():
    """Return training dataset statistics."""
    from learning.database import _get_db as get_db
    db = get_db()
    stats = LearningDatasetBuilder.get_stats(db)
    db.close()
    return stats


@router.post("/api/ai/dataset/export")
async def ai_dataset_export(limit: int = Query(1000), offset: int = Query(0)):
    """Export training dataset for model training."""
    from learning.database import _get_db as get_db
    db = get_db()
    records = LearningDatasetBuilder.export_records(db, limit, offset)
    db.close()
    return {"records": records, "count": len(records)}
