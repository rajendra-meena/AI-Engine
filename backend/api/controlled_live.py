"""Controlled Live API — Phase 55 one-trade controlled live execution.

All safety decisions are server-side. No unrestricted live endpoints.
Phase 55 adds: real-status, order, position, protection, post-trade endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from live.controlled_live_integration import ControlledLiveIntegration

router = APIRouter(tags=["controlled-live"])

_integration: ControlledLiveIntegration | None = None


def set_controlled_live_integration(integration: ControlledLiveIntegration):
    global _integration
    _integration = integration


def _get() -> ControlledLiveIntegration:
    assert _integration is not None, "ControlledLiveIntegration not initialized"
    return _integration


# ── Status ──


@router.get("/api/live/controlled/status")
async def controlled_status():
    """Get controlled live status."""
    return _get().get_status()


@router.get("/api/live/controlled/real-status")
async def controlled_real_status():
    """Phase 55: Get real live status with warnings."""
    return _get().get_real_status()


@router.get("/api/live/controlled/preflight")
async def controlled_preflight():
    """Get preflight status."""
    return {"status": "preflight_check"}


@router.get("/api/live/controlled/execution")
async def controlled_execution():
    """Get execution status."""
    return _get().get_execution()


@router.get("/api/live/controlled/order")
async def controlled_order():
    """Phase 55: Get order status."""
    status = _get().get_status()
    return {
        "broker_order_id": status.get("broker_order_id", ""),
        "broker_status": status.get("broker_status", ""),
        "order_reconciled": status.get("order_reconciled", False),
        "position_reconciled": status.get("position_reconciled", False),
    }


@router.get("/api/live/controlled/position")
async def controlled_position():
    """Phase 55: Get position monitoring status."""
    status = _get().get_status()
    return {
        "state": status.get("state", ""),
        "position_reconciled": status.get("position_reconciled", False),
        "protective_order_status": status.get("protective_order_status", "not_verified"),
    }


@router.get("/api/live/controlled/protection")
async def controlled_protection():
    """Phase 55: Get protective order (SL/Target) status."""
    return _get().get_protection_status()


@router.get("/api/live/controlled/post-trade")
async def controlled_post_trade():
    """Phase 55: Get post-trade evaluation results."""
    return _get().get_post_trade_evaluation()


@router.get("/api/live/controlled/reconciliation")
async def controlled_reconciliation():
    """Get reconciliation status."""
    return {"status": "reconciliation_check"}


@router.get("/api/live/controlled/risk")
async def controlled_risk():
    """Get risk status."""
    return {"status": "risk_monitoring"}


@router.get("/api/live/controlled/audit")
async def controlled_audit():
    """Phase 55: Get audit events."""
    return {"events": _get().get_audit_events(limit=100)}


# ── Actions ──


@router.post("/api/live/controlled/activate")
async def controlled_activate(reviewer: str = "", reason: str = ""):
    """Activate controlled live mode.

    Phase 55: Also validates environment safety before activating.
    Requires human reviewer + reason.
    Validates all prerequisites before activating.
    One trade maximum per activation.
    """
    result = _get().activate(reviewer=reviewer, reason=reason)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Activation failed"))
    return result


@router.post("/api/live/controlled/authorize")
async def controlled_authorize(reviewer: str = "", reason: str = ""):
    """Phase 55: Create a new authorization for controlled live.

    Alias for activate with stronger semantics.
    """
    return await controlled_activate(reviewer=reviewer, reason=reason)


@router.post("/api/live/controlled/execute")
async def controlled_execute(
    symbol: str = "", side: str = "BUY", quantity: int = 0,
    price: float | None = None, stop_loss: float | None = None,
    target: float | None = None, signal_id: str = "",
):
    """Execute one controlled live trade through all safety gates.

    Phase 55: Server-side hard limits always enforced.
    Frontend values cannot override safety limits.

    After execution: trades_remaining becomes 0.
    New activation required for another trade.
    """
    # Phase 55: Server-side limit enforcement (never trust frontend)
    if quantity > 1:
        raise HTTPException(status_code=400, detail="Quantity cannot exceed 1")
    if price and (price * quantity) > 10000:
        raise HTTPException(status_code=400, detail="Notional value cannot exceed ₹10,000")

    result = await _get().execute_trade(
        symbol=symbol, side=side, quantity=quantity,
        price=price, stop_loss=stop_loss, target=target,
        signal_id=signal_id,
    )
    if not result.get("success") and result.get("state") != "completed":
        raise HTTPException(status_code=400, detail=result.get("error", "Execution failed"))
    return result


@router.post("/api/live/controlled/stop")
async def controlled_stop(reviewer: str = "", reason: str = ""):
    """Emergency stop controlled live execution.

    Blocks entries, cancels orders, creates incident.
    Requires human recovery.
    """
    result = await _get().emergency_stop(reviewer=reviewer, reason=reason)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Stop failed"))
    return result


@router.post("/api/live/controlled/reconcile")
async def controlled_reconcile():
    """Phase 55: Run reconciliation."""
    return await _get().reconcile()
