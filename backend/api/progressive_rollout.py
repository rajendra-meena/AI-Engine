"""Progressive Rollout API — Phase 49 multi-canary and rollout endpoints.

All endpoints require human approval for stage progression.
No unrestricted live trading endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from live.progressive_rollout import ProgressiveRolloutEngine, ProgressiveRolloutError
from live.rollout_stages import RolloutStage, STAGE_RISK_LIMITS

router = APIRouter(tags=["progressive-rollout"])

_engine: ProgressiveRolloutEngine | None = None


def _is_rollout_event(e: dict, rollout_id: str) -> bool:
    match_id = e.get("details", {}).get("rollout_id") == rollout_id
    match_type = "rollout" in e.get("event_type", "").lower()
    return match_id or match_type


def set_rollout_engine(engine: ProgressiveRolloutEngine):
    global _engine
    _engine = engine


def _get_engine() -> ProgressiveRolloutEngine:
    assert _engine is not None, "ProgressiveRolloutEngine not initialized"
    return _engine


# ── Status ──


@router.get("/api/live/rollout/status")
async def rollout_status():
    """Get current rollout status."""
    engine = _get_engine()
    return engine.get_status()


@router.get("/api/live/rollout/stages")
async def rollout_stages():
    """Get all rollout stages and their limits."""
    return {
        "stages": {
            s: STAGE_RISK_LIMITS.get(s, {"note": "non_trading_stage"})
            for s in [
                RolloutStage.CANARY_1, RolloutStage.CANARY_2, RolloutStage.CANARY_3,
                RolloutStage.LIMITED_ROLLOUT, RolloutStage.CONTROLLED_ROLLOUT,
            ]
        },
        "current_stage": _get_engine().get_status().get("current_stage", "locked"),
    }


@router.get("/api/live/rollout/history")
async def rollout_history(limit: int = 20):
    """Get rollout history."""
    engine = _get_engine()
    return {"history": engine.get_history(limit=limit)}


# ── Progression ──


@router.post("/api/live/rollout/request")
async def rollout_request(reviewer: str = "", reason: str = "",
                          target_stage: str = ""):
    """Request progression to a new rollout stage.

    Requires human approval to proceed.
    """
    engine = _get_engine()
    try:
        record = engine.request_progression(
            reviewer=reviewer, reason=reason, target_stage=target_stage,
        )
        return record.to_dict()
    except ProgressiveRolloutError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/live/rollout/{rollout_id}")
async def rollout_get(rollout_id: str):
    """Get a specific rollout record."""
    engine = _get_engine()
    record = engine.get_status()
    if record.get("rollout_id") != rollout_id:
        raise HTTPException(status_code=404, detail="Rollout not found")
    return record


@router.post("/api/live/rollout/{rollout_id}/approve")
async def rollout_approve(rollout_id: str, reviewer: str = "",
                          review_note: str = "", target_stage: str = ""):
    """Approve a progression request. Validates eligibility before approving."""
    engine = _get_engine()
    try:
        record = engine.approve_progression(
            rollout_id=rollout_id, reviewer=reviewer,
            review_note=review_note, target_stage=target_stage,
        )
        return record.to_dict()
    except ProgressiveRolloutError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/live/rollout/{rollout_id}/reject")
async def rollout_reject(rollout_id: str, reviewer: str = "", reason: str = ""):
    """Reject a progression request."""
    engine = _get_engine()
    try:
        record = engine.reject_progression(
            rollout_id=rollout_id, reviewer=reviewer, reason=reason,
        )
        return record.to_dict()
    except ProgressiveRolloutError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/live/rollout/{rollout_id}/rollback")
async def rollout_rollback(rollout_id: str, reason: str = ""):
    """Execute rollback from current stage."""
    engine = _get_engine()
    try:
        record = engine.execute_rollback(reason=reason)
        return record.to_dict()
    except ProgressiveRolloutError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Eligibility ──


@router.get("/api/live/rollout/{rollout_id}/eligibility")
async def rollout_eligibility(rollout_id: str, target_stage: str = ""):
    """Check eligibility for progression."""
    engine = _get_engine()
    if hasattr(engine, '_eligibility') and engine._eligibility:
        eligibility = engine._eligibility.check_eligibility(
            current_stage=engine.get_status().get("current_stage", ""),
            target_stage=target_stage,
        )
        return eligibility.to_dict()
    return {"eligible": False, "error": "Eligibility engine not configured"}


@router.get("/api/live/rollout/{rollout_id}/performance")
async def rollout_performance(rollout_id: str):
    """Get rollout performance data."""
    engine = _get_engine()
    return engine.get_performance()


@router.get("/api/live/rollout/{rollout_id}/canaries")
async def rollout_canaries(rollout_id: str):
    """Get canary sequence for this rollout."""
    engine = _get_engine()
    if hasattr(engine, '_tracker'):
        return engine._tracker.get_summary()
    return {"canaries": []}


@router.get("/api/live/rollout/{rollout_id}/audit")
async def rollout_audit(rollout_id: str):
    """Get audit events for this rollout."""
    engine = _get_engine()
    if engine._audit_log:
        entries = engine._audit_log.get_entries(limit=100)
        rollout_entries = [
            e for e in entries
            if _is_rollout_event(e, rollout_id)
        ]
        return {"audit_events": rollout_entries, "total": len(rollout_entries)}
    return {"audit_events": [], "total": 0}


@router.get("/api/live/rollout/limits")
async def rollout_limits():
    """Get immutable rollout thresholds."""
    engine = _get_engine()
    if hasattr(engine, '_rollback_ctrl'):
        return engine._rollback_ctrl.get_thresholds()
    return {"error": "Rollback controller not configured"}
