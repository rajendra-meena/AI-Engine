"""Live Activation API — Phase 45 controlled live activation endpoints.

All endpoints are read-only or require explicit human action.
No endpoint automatically places a trade or enables auto-trading.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
from live.live_execution_gate import LiveExecutionGate

router = APIRouter(tags=["live-activation"])

_gate: ControlledLiveActivationGate | None = None
_live_execution_gate: LiveExecutionGate | None = None


def set_activation_gate(gate: ControlledLiveActivationGate):
    global _gate
    _gate = gate


def set_live_execution_gate(gate: LiveExecutionGate):
    global _live_execution_gate
    _live_execution_gate = gate


def _get_gate() -> ControlledLiveActivationGate:
    assert _gate is not None, "ControlledLiveActivationGate not initialized"
    return _gate


def _get_exec_gate() -> LiveExecutionGate | None:
    return _live_execution_gate


# ── Status ──


@router.get("/api/live-activation/status")
async def activation_status():
    """Get current activation state and full status."""
    gate = _get_gate()
    return gate.get_status()


@router.get("/api/live-activation/prerequisites")
async def activation_prerequisites():
    """Get current prerequisite check results (runs checks)."""
    gate = _get_gate()
    prereqs = gate.validate_prerequisites()
    return {
        "prerequisites": [p.to_dict() for p in prereqs],
        "passed": sum(1 for p in prereqs if p.passed),
        "total": len(prereqs),
    }


# ── Validation ──


@router.post("/api/live-activation/validate")
async def activation_validate(reviewer: str = "", reason: str = ""):
    """Run all 28 prerequisite checks.

    If all pass and state is LOCKED, transitions to READY.
    Does NOT arm or start live execution.
    """
    gate = _get_gate()
    try:
        result = gate.validate(reviewer=reviewer, reason=reason)
        return result
    except ActivationGateError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Activation Workflow ──


@router.post("/api/live-activation/arm")
async def activation_arm(reviewer: str = "", reason: str = "",
                         activation_duration_minutes: int = 30):
    """Arm the system for live activation.

    Requires:
    - reviewer identity (non-empty)
    - reason (non-empty)
    - all 28 prerequisites passing

    Returns confirmation_token needed for /start.
    """
    gate = _get_gate()
    try:
        result = gate.arm(
            reviewer=reviewer,
            reason=reason,
            activation_duration_minutes=activation_duration_minutes,
        )
        return result
    except ActivationGateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/live-activation/start")
async def activation_start(confirmation_token: str = ""):
    """Begin the activation window. Transitions ARMED→ACTIVE.

    Requires the confirmation_token returned by /arm.
    Only then can live orders be authorized.
    """
    gate = _get_gate()
    try:
        result = gate.start(confirmation_token=confirmation_token)
        return result
    except ActivationGateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/live-activation/pause")
async def activation_pause(reason: str = ""):
    """Pause new live orders. Transitions ACTIVE→PAUSED."""
    gate = _get_gate()
    try:
        result = gate.pause(reason=reason)
        return result
    except ActivationGateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/live-activation/revoke")
async def activation_revoke(reason: str = ""):
    """Revoke activation. Transitions → REVOKED."""
    gate = _get_gate()
    try:
        result = gate.revoke(reason=reason)
        return result
    except ActivationGateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/live-activation/kill-switch")
async def activation_kill_switch(reason: str = ""):
    """Emergency kill switch. Transitions → KILL_SWITCHED.

    Blocks all new live orders immediately.
    Triggers KillSwitch and EmergencyShutdown.
    Requires explicit recovery.
    """
    gate = _get_gate()
    try:
        result = gate.kill_switch(reason=reason)
        return result
    except ActivationGateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/live-activation/recover")
async def activation_recover(reviewer: str = "", reason: str = ""):
    """Recover from terminal states. Transitions → LOCKED.

    Requires explicit human reviewer identity.
    """
    gate = _get_gate()
    try:
        result = gate.recover(reviewer=reviewer, reason=reason)
        return result
    except ActivationGateError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── History & Audit ──


@router.get("/api/live-activation/history")
async def activation_history(limit: int = 20):
    """Get activation history."""
    gate = _get_gate()
    return {
        "history": gate.get_history(limit=limit),
        "total": len(gate.get_all_records()),
    }


@router.get("/api/live-activation/audit")
async def activation_audit(limit: int = 100):
    """Get activation-related audit events."""
    gate = _get_gate()
    record = gate.get_record()
    # Collect audit log entries that mention activation
    if gate._audit_log:
        entries = gate._audit_log.get_entries(limit=limit)
        activation_entries = [
            e for e in entries
            if (
                e.get("details", {}).get("activation_id") == record.activation_id
                or "activation" in e.get("event_type", "").lower()
            )
        ]
        return {"audit_events": activation_entries, "total": len(activation_entries)}
    return {"audit_events": [], "total": 0}
