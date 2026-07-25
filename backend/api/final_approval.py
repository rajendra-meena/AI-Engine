"""Final Approval API — human approval gate for live trading review."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from live.final_approval import FinalApprovalEngine

router = APIRouter(tags=["live-approval"])

_engine: FinalApprovalEngine | None = None


def set_final_approval_engine(engine: FinalApprovalEngine):
    global _engine
    _engine = engine


def _get() -> FinalApprovalEngine:
    assert _engine is not None, "FinalApprovalEngine not initialized"
    return _engine


@router.get("/api/live-approval/status")
async def approval_status():
    """Get latest approval status."""
    engine = _get()
    records = engine.get_all_records()
    if records:
        return records[-1].to_dict()
    return {"status": "no_record", "message": "Run approval check first"}


@router.post("/api/live-approval/run")
async def run_approval():
    """Run final approval evaluation."""
    # In production, retrieve dependencies from service locator
    engine = _get()
    record = engine.run()
    return record.to_dict()


@router.get("/api/live-approval/{approval_id}")
async def get_approval(approval_id: str):
    """Get approval record."""
    record = _get().get_record(approval_id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record.to_dict()


@router.get("/api/live-approval/history")
async def approval_history():
    """Get all approval records."""
    return {"approvals": [r.to_dict() for r in _get().get_all_records()]}


@router.get("/api/live-approval/checks")
async def approval_checks():
    """Get approval gate categories."""
    return {
        "gates": [
            {"name": "champion_integrity", "label": "Champion Integrity", "weight": 15},
            {"name": "shadow_validation", "label": "Shadow Validation", "weight": 20},
            {"name": "risk_engine", "label": "Risk Engine", "weight": 15},
            {"name": "runtime_safety", "label": "Runtime Safety", "weight": 10},
            {"name": "market_data", "label": "Market Data", "weight": 10},
            {"name": "broker_health", "label": "Broker Health", "weight": 5},
            {"name": "execution_safety", "label": "Execution Safety", "weight": 10},
            {"name": "loss_protection", "label": "Loss Protection", "weight": 10},
            {"name": "operational_safety", "label": "Operational Safety", "weight": 3},
            {"name": "auditability", "label": "Auditability", "weight": 2},
        ]
    }


@router.post("/api/live-approval/{approval_id}/approve")
async def approve_approval(
    approval_id: str,
    reviewer: str = Query("", description="Reviewer name"),
    note: str = Query("", description="Review note"),
):
    """Approve for live review. Does NOT enable LIVE trading."""
    record = _get().approve(approval_id, reviewer, note)
    if not record:
        raise HTTPException(status_code=400, detail="Approval failed")
    result = record.to_dict()
    result["warning"] = "Approval does NOT enable LIVE trading. LIVE mode remains disabled."
    return result


@router.post("/api/live-approval/{approval_id}/reject")
async def reject_approval(approval_id: str, reason: str = Query("")):
    """Reject approval."""
    record = _get().reject(approval_id, reason)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record.to_dict()


@router.post("/api/live-approval/{approval_id}/expire")
async def expire_approval(approval_id: str):
    """Expire an approval."""
    record = _get().expire(approval_id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record.to_dict()


@router.get("/api/live-approval/config-hash")
async def approval_config_hash():
    """Get current configuration hash (read-only snapshot)."""
    return {
        "message": "Configuration hash available via approval run.",
        "live_execution_enabled": False,
    }
