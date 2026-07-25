"""Execution Gateway API — controlled execution endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from execution.gateway import ExecutionGateway

router = APIRouter(tags=["execution"])

_gateway: ExecutionGateway | None = None


def set_execution_gateway(gw: ExecutionGateway):
    global _gateway
    _gateway = gw


def _get() -> ExecutionGateway:
    assert _gateway is not None, "ExecutionGateway not initialized"
    return _gateway


@router.get("/api/execution/status")
async def execution_status():
    """Get execution gateway status overview."""
    return _get().get_status()


@router.get("/api/execution/mode")
async def execution_mode():
    """Get current execution mode."""
    gw = _get()
    return {"mode": gw.get_mode(), "live_armed": gw.get_arming_status()["live_armed"]}


@router.post("/api/execution/mode")
async def set_execution_mode(mode: str = Query(..., description="disabled, paper, or live")):
    """Set execution mode. NEVER defaults to LIVE."""
    gw = _get()
    if mode == "live":
        return {"success": False, "message": "Use /api/execution/arm-live to enable LIVE mode"}
    success = gw.set_mode(mode)
    return {"success": success, "mode": gw.get_mode()}


@router.post("/api/execution/arm-live")
async def arm_live_execution():
    """Arm LIVE execution. Returns a short-lived confirmation token."""
    gw = _get()
    gw.set_mode("live")
    result = gw.arm_live()
    return result


@router.post("/api/execution/disarm-live")
async def disarm_live_execution():
    """Disarm LIVE execution."""
    _get().disarm_live()
    return {"success": True, "message": "LIVE execution disarmed"}


@router.get("/api/execution/arming-status")
async def execution_arming_status():
    """Get live arming status."""
    return _get().get_arming_status()


@router.post("/api/execution/validate")
async def validate_execution(params: dict[str, Any]):
    """Validate whether a trade can be executed without executing."""
    gw = _get()
    side = params.get("side", "BUY")
    price = params.get("price")
    quantity = params.get("quantity", 1)
    stop_loss = params.get("stop_loss")
    target = params.get("target")
    live_token = params.get("live_token", "")

    checks = gw._run_safety_checks(side, price, quantity, stop_loss, target, live_token)
    failed = [k for k, v in checks.items() if not v]
    return {
        "execution_permitted": len(failed) == 0,
        "safety_checks": checks,
        "failed_checks": failed,
        "mode": gw.get_mode(),
        "live_armed": gw.is_live_armed() if gw.get_mode() == "live" else False,
    }


@router.post("/api/execution/execute")
async def execute_trade(params: dict[str, Any]):
    """
    Execute a trade through the controlled gateway.

    This is the ONLY execution entry point.
    Requires an approved TradePlan. All safety checks are enforced.
    """
    gw = _get()
    result = gw.execute(
        symbol=params.get("symbol", ""),
        side=params.get("side", "BUY"),
        quantity=params.get("quantity", 1),
        price=params.get("price"),
        stop_loss=params.get("stop_loss"),
        target=params.get("target"),
        trade_plan_id=params.get("trade_plan_id", ""),
        trace_id=params.get("trace_id", ""),
        idempotency_key=params.get("idempotency_key", ""),
        live_token=params.get("live_token", ""),
    )
    return result.to_dict()


@router.get("/api/execution/{execution_id}")
async def get_execution(execution_id: str):
    """Get a specific execution record."""
    result = _get().get_execution(execution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Execution not found")
    return result.to_dict()


@router.get("/api/execution/history")
async def execution_history(limit: int = Query(50)):
    """Get execution history."""
    return {"executions": _get().get_history(limit)}
