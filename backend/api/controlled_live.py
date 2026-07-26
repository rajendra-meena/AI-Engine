"""Controlled Live API — Phase 54 one-trade controlled live execution.

All safety decisions are server-side. No unrestricted live endpoints.
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
    """Get order status."""
    status = _get().get_status()
    return {
        "broker_order_id": status.get("broker_order_id", ""),
        "broker_status": status.get("broker_status", ""),
    }


@router.get("/api/live/controlled/position")
async def controlled_position():
    """Get position status."""
    return {"status": "position_monitoring"}


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
    """Get audit events."""
    return {"events": []}


# ── Actions ──


@router.post("/api/live/controlled/activate")
async def controlled_activate(reviewer: str = "", reason: str = ""):
    """Activate controlled live mode.

    Requires human reviewer + reason.
    Validates all prerequisites before activating.
    One trade maximum per activation.
    """
    result = _get().activate(reviewer=reviewer, reason=reason)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Activation failed"))
    return result


@router.post("/api/live/controlled/execute")
async def controlled_execute(
    symbol: str = "", side: str = "BUY", quantity: int = 0,
    price: float | None = None, stop_loss: float | None = None,
    target: float | None = None, signal_id: str = "",
):
    """Execute one controlled live trade through all safety gates.

    After execution: trades_remaining becomes 0.
    New activation required for another trade.
    """
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
    """Run reconciliation."""
    return await _get().reconcile()
