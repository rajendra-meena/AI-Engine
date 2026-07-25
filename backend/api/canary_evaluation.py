"""Canary Evaluation API — Phase 48 post-trade evaluation and rollout governance.

All endpoints are read-only or require explicit human review.
No live-trading enabling endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from live.canary_evaluation import CanaryEvaluationEngine
from live.rollout_governance import RolloutGovernanceEngine

router = APIRouter(tags=["canary-evaluation"])

_evaluation: CanaryEvaluationEngine | None = None
_governance: RolloutGovernanceEngine | None = None


def set_evaluation_engine(engine: CanaryEvaluationEngine):
    global _evaluation
    _evaluation = engine


def set_governance_engine(engine: RolloutGovernanceEngine):
    global _governance
    _governance = engine


def _get_evaluation() -> CanaryEvaluationEngine:
    assert _evaluation is not None, "CanaryEvaluationEngine not initialized"
    return _evaluation


def _get_governance() -> RolloutGovernanceEngine:
    assert _governance is not None, "RolloutGovernanceEngine not initialized"
    return _governance


# ── Evaluation ──


@router.get("/api/live/canary/evaluation/status")
async def evaluation_status():
    """Get evaluation engine status."""
    engine = _get_evaluation()
    return {
        "total_evaluations": len(engine.get_all_reports()),
    }


@router.post("/api/live/canary/evaluation/{canary_id}/run")
async def evaluation_run(canary_id: str):
    """Run full evaluation for a completed canary."""
    engine = _get_evaluation()
    report = engine.evaluate(canary_id)
    return report.to_dict()


@router.get("/api/live/canary/evaluation/{evaluation_id}")
async def evaluation_get(evaluation_id: str):
    """Get a specific evaluation report."""
    engine = _get_evaluation()
    report = engine.get_report(evaluation_id)
    if not report:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return report.to_dict()


@router.get("/api/live/canary/evaluation/history")
async def evaluation_history(limit: int = 20):
    """Get evaluation history."""
    engine = _get_evaluation()
    return {
        "history": engine.get_history(limit=limit),
        "total": len(engine.get_all_reports()),
    }


@router.get("/api/live/canary/evaluation/{evaluation_id}/reconciliation")
async def evaluation_reconciliation(evaluation_id: str):
    """Get reconciliation details from an evaluation."""
    engine = _get_evaluation()
    report = engine.get_report(evaluation_id)
    if not report:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    # Return order + position reconciliation category results
    results = {}
    for cat in report.category_results:
        if cat.category in ("order_reconciliation", "position_reconciliation"):
            results[cat.category] = cat.to_dict()
    return {"reconciliation": results, "hard_fails": report.hard_fails}


@router.get("/api/live/canary/evaluation/{evaluation_id}/execution-quality")
async def evaluation_execution_quality(evaluation_id: str):
    """Get execution quality details."""
    engine = _get_evaluation()
    report = engine.get_report(evaluation_id)
    if not report:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    results = {}
    for cat in report.category_results:
        if cat.category in ("fill_quality", "execution_latency"):
            results[cat.category] = cat.to_dict()
    return {
        "execution_quality": results,
        "slippage_pct": report.slippage_pct,
        "latency_ms": report.latency_ms,
    }


@router.get("/api/live/canary/evaluation/{evaluation_id}/risk")
async def evaluation_risk(evaluation_id: str):
    """Get risk compliance details."""
    engine = _get_evaluation()
    report = engine.get_report(evaluation_id)
    if not report:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    results = {}
    for cat in report.category_results:
        if cat.category in ("risk_compliance", "sl_target_integrity"):
            results[cat.category] = cat.to_dict()
    return {"risk": results}


@router.get("/api/live/canary/evaluation/{evaluation_id}/audit")
async def evaluation_audit(evaluation_id: str):
    """Get audit integrity details."""
    engine = _get_evaluation()
    report = engine.get_report(evaluation_id)
    if not report:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    results = {}
    for cat in report.category_results:
        if cat.category == "audit_integrity":
            results[cat.category] = cat.to_dict()
    return {"audit": results}


# ── Rollout Governance ──


@router.post("/api/live/canary/rollout/{evaluation_id}/review")
async def rollout_review(evaluation_id: str, reviewer: str = "",
                         review_note: str = "", decision: str = ""):
    """Submit human review for a canary evaluation.

    Required: reviewer, review_note, decision.
    Decision must be one of: accept_canary, reject_canary, request_more_data, rollback.
    """
    gov_engine = _get_governance()
    try:
        gov = gov_engine.submit_human_review(
            evaluation_id=evaluation_id,
            reviewer=reviewer,
            review_note=review_note,
            decision=decision,
        )
        return gov.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/live/canary/rollout/status")
async def rollout_status():
    """Get rollout governance status."""
    gov_engine = _get_governance()
    return {
        "total_reviews": len(gov_engine.get_history()),
        "multi_canary_stats": gov_engine.get_multi_canary_stats(),
    }


@router.get("/api/live/canary/rollout/history")
async def rollout_history(limit: int = 20):
    """Get rollout governance history."""
    gov_engine = _get_governance()
    return {
        "history": gov_engine.get_history(limit=limit),
        "total": len(gov_engine.get_history(limit=10000)),
    }
