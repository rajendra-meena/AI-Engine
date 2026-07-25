"""Shadow Validation API — performance metrics, comparison, drift, validation reports."""

from __future__ import annotations

from fastapi import APIRouter

from trading.shadow_performance import ShadowPerformanceEngine
from trading.shadow_validation import ShadowValidationEngine

router = APIRouter(tags=["shadow-validation"])

_perf_engine = ShadowPerformanceEngine()
_val_engine = ShadowValidationEngine(_perf_engine)
_tracker_ref = None


def set_shadow_tracker(tracker):
    global _tracker_ref
    _tracker_ref = tracker


def _get_tracker():
    return _tracker_ref


@router.get("/api/runtime/shadow/performance")
async def shadow_performance():
    """Get shadow performance metrics."""
    tracker = _get_tracker()
    if not tracker:
        return {"message": "Shadow tracking not available"}
    metrics = _perf_engine.compute_metrics(tracker)
    return metrics.to_dict()


@router.get("/api/runtime/shadow/metrics")
async def shadow_metrics():
    """Get detailed shadow metrics."""
    tracker = _get_tracker()
    if not tracker:
        return {"message": "Shadow tracking not available"}
    m = _perf_engine.compute_metrics(tracker)
    return m.to_dict()


@router.get("/api/runtime/shadow/funnel")
async def shadow_funnel():
    """Get signal funnel."""
    tracker = _get_tracker()
    if not tracker:
        return {"message": "Not available"}
    m = _perf_engine.compute_metrics(tracker)
    return _perf_engine.compute_funnel(m)


@router.get("/api/runtime/shadow/sessions")
async def shadow_sessions():
    """Get per-session breakdown."""
    tracker = _get_tracker()
    if not tracker:
        return {"sessions": []}
    return {"sessions": _perf_engine.compute_sessions(tracker.get_closed_trades())}


@router.get("/api/runtime/shadow/breakdown/symbols")
async def shadow_symbols():
    tracker = _get_tracker()
    if not tracker:
        return {"symbols": []}
    return {"symbols": _perf_engine.breakdown_by(tracker.get_closed_trades(), "symbol")}


@router.get("/api/runtime/shadow/breakdown/directions")
async def shadow_directions():
    tracker = _get_tracker()
    if not tracker:
        return {"directions": []}
    return {"directions": _perf_engine.breakdown_by(tracker.get_closed_trades(), "direction")}


@router.get("/api/runtime/shadow/breakdown/timeframes")
async def shadow_timeframes():
    tracker = _get_tracker()
    if not tracker:
        return {"timeframes": []}
    return {"timeframes": _perf_engine.breakdown_by(tracker.get_closed_trades(), "timeframe")}


@router.get("/api/runtime/shadow/breakdown/regimes")
async def shadow_regimes():
    tracker = _get_tracker()
    if not tracker:
        return {"regimes": []}
    return {"regimes": _perf_engine.breakdown_by(tracker.get_closed_trades(), "market_regime")}


@router.get("/api/runtime/shadow/comparison")
async def shadow_comparison():
    """Get backtest vs OOS vs shadow comparison."""
    return {"message": "Set baseline via /api/runtime/shadow/validate to enable comparison"}


@router.get("/api/runtime/shadow/drift")
async def shadow_drift():
    """Get performance drift status."""
    return {"drift": "stable", "message": "Monitor validation reports for drift analysis"}


@router.post("/api/runtime/shadow/validate")
async def run_shadow_validate():
    """Run shadow validation and produce report."""
    tracker = _get_tracker()
    if not tracker:
        return {"message": "Shadow tracker not available"}
    report = _val_engine.validate(tracker)
    return report.to_dict()


@router.get("/api/runtime/shadow/validation/{val_id}")
async def get_shadow_validation(val_id: str):
    """Get a shadow validation report."""
    report = _val_engine.get_report(val_id)
    if not report:
        return {"error": "Not found"}
    return report.to_dict()


@router.get("/api/runtime/shadow/validation/history")
async def shadow_validation_history():
    """Get all shadow validation reports."""
    return {"reports": [r.to_dict() for r in _val_engine.get_all_reports()]}
