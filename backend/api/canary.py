"""Canary API — Phase 47 controlled canary execution endpoints.

Complete request/approve/arm/precheck/execute workflow.
No unrestricted live trading endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from live.canary_lifecycle import CanaryLifecycleManager, CanaryLifecycleError

router = APIRouter(tags=["canary"])

_lifecycle: CanaryLifecycleManager | None = None


def set_canary_lifecycle(mgr: CanaryLifecycleManager):
    global _lifecycle
    _lifecycle = mgr


def _get_lifecycle() -> CanaryLifecycleManager:
    assert _lifecycle is not None, "CanaryLifecycleManager not initialized"
    return _lifecycle


# ── Status ──


@router.get("/api/live/canary/status")
async def canary_status():
    """Get canary overall status."""
    lifecycle = _get_lifecycle()
    return lifecycle.get_status()


@router.get("/api/live/canary/history")
async def canary_history(limit: int = 20):
    """Get canary authorization history."""
    lifecycle = _get_lifecycle()
    return {
        "history": lifecycle.get_history(limit=limit),
        "total": len(lifecycle.get_all_authorizations()),
    }


# ── Authorization CRUD ──


@router.post("/api/live/canary/request")
async def canary_request(
    reviewer: str = "",
    reason: str = "",
    symbol: str = "",
    direction: str = "BUY",
    quantity: int = 0,
    price: float | None = None,
    stop_loss: float | None = None,
    target: float | None = None,
    strategy_version: str = "",
):
    """Request a new canary authorization. Requires human approval to proceed."""
    lifecycle = _get_lifecycle()
    try:
        auth = lifecycle.request(
            reviewer=reviewer, reason=reason,
            symbol=symbol, direction=direction, quantity=quantity,
            price=price, stop_loss=stop_loss, target=target,
            strategy_version=strategy_version,
        )
        return auth.to_dict()
    except CanaryLifecycleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/live/canary/{authorization_id}")
async def canary_get(authorization_id: str):
    """Get authorization detail."""
    lifecycle = _get_lifecycle()
    auth = lifecycle.get_authorization(authorization_id)
    if not auth:
        raise HTTPException(status_code=404, detail="Authorization not found")
    return auth.to_dict()


@router.post("/api/live/canary/{authorization_id}/approve")
async def canary_approve(authorization_id: str, reviewer: str = ""):
    """Approve a canary authorization request.

    Binds config hash and champion version at approval time.
    """
    lifecycle = _get_lifecycle()
    try:
        auth = lifecycle.approve(authorization_id, reviewer=reviewer)
        return auth.to_dict()
    except CanaryLifecycleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/live/canary/{authorization_id}/arm")
async def canary_arm(authorization_id: str, reviewer: str = ""):
    """Arm an approved authorization.

    Validates config hash and champion haven't changed since approval.
    """
    lifecycle = _get_lifecycle()
    try:
        auth = lifecycle.arm(authorization_id, reviewer=reviewer)
        return auth.to_dict()
    except CanaryLifecycleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/live/canary/{authorization_id}/precheck")
async def canary_precheck(authorization_id: str):
    """Run final precheck for an authorization. Real-time validation."""
    lifecycle = _get_lifecycle()
    try:
        result = lifecycle.precheck(authorization_id)
        return result.to_dict() if hasattr(result, 'to_dict') else result
    except CanaryLifecycleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/live/canary/{authorization_id}/execute")
async def canary_execute(authorization_id: str, confirmation_token: str = ""):
    """Execute the authorized canary trade.

    Runs the full execution pipeline. Only MARKET orders. MAX_TRADES = 1.
    """
    lifecycle = _get_lifecycle()
    try:
        import asyncio
        result = await lifecycle.execute(authorization_id, confirmation_token=confirmation_token)
        return result
    except CanaryLifecycleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/live/canary/{authorization_id}/cancel")
async def canary_cancel(authorization_id: str, reason: str = ""):
    """Cancel an authorization."""
    lifecycle = _get_lifecycle()
    try:
        auth = lifecycle.cancel(authorization_id, reason=reason)
        return auth.to_dict()
    except CanaryLifecycleError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Order, Position, Reconciliation Queries ──


@router.get("/api/live/canary/{authorization_id}/order")
async def canary_order(authorization_id: str):
    """Get order status for an authorization."""
    lifecycle = _get_lifecycle()
    auth = lifecycle.get_authorization(authorization_id)
    if not auth:
        raise HTTPException(status_code=404, detail="Authorization not found")
    return {
        "authorization_id": authorization_id,
        "state": auth.state,
        "broker_order_id": auth.broker_order_id or None,
        "order_id": auth.order_id or None,
        "symbol": auth.approved_symbol,
        "direction": auth.approved_direction,
        "quantity": auth.approved_quantity,
        "price": auth.price,
        "stop_loss": auth.stop_loss,
        "target": auth.target,
    }


@router.get("/api/live/canary/{authorization_id}/position")
async def canary_position(authorization_id: str):
    """Get position status for an authorization."""
    lifecycle = _get_lifecycle()
    auth = lifecycle.get_authorization(authorization_id)
    if not auth:
        raise HTTPException(status_code=404, detail="Authorization not found")
    broker_positions = []
    if hasattr(lifecycle, '_broker') and lifecycle._broker:
        try:
            import asyncio
            broker_positions = asyncio.run(lifecycle._broker.get_positions())
        except Exception:
            pass
    return {
        "authorization_id": authorization_id,
        "state": auth.state,
        "broker_order_id": auth.broker_order_id,
        "pnl": auth.pnl,
        "broker_positions": broker_positions[:5] if broker_positions else [],
    }


@router.get("/api/live/canary/{authorization_id}/reconciliation")
async def canary_reconciliation(authorization_id: str):
    """Get reconciliation status for an authorization."""
    lifecycle = _get_lifecycle()
    auth = lifecycle.get_authorization(authorization_id)
    if not auth:
        raise HTTPException(status_code=404, detail="Authorization not found")
    return {
        "authorization_id": authorization_id,
        "state": auth.state,
        "broker_order_id": auth.broker_order_id,
        "failure_reason": auth.failure_reason or None,
        "history": auth.history[-10:],
    }


@router.get("/api/live/canary/{authorization_id}/audit")
async def canary_audit(authorization_id: str):
    """Get audit events for an authorization."""
    lifecycle = _get_lifecycle()
    auth = lifecycle.get_authorization(authorization_id)
    if not auth:
        raise HTTPException(status_code=404, detail="Authorization not found")
    if lifecycle._audit_log:
        entries = lifecycle._audit_log.get_entries(limit=100)
        auth_entries = [
            e for e in entries
            if e.get("details", {}).get("authorization_id") == authorization_id
        ]
        return {"audit_events": auth_entries, "total": len(auth_entries)}
    return {"audit_events": [], "total": 0}
