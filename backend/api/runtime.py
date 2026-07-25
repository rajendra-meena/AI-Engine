"""Runtime API — champion strategy execution and shadow trading control."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from trading.runtime_orchestrator import RuntimeOrchestrator

router = APIRouter(tags=["runtime"])

_orchestrator: RuntimeOrchestrator | None = None


def set_runtime_orchestrator(orch: RuntimeOrchestrator):
    global _orchestrator
    _orchestrator = orch


def _get() -> RuntimeOrchestrator:
    assert _orchestrator is not None, "RuntimeOrchestrator not initialized"
    return _orchestrator


@router.get("/api/runtime/status")
async def runtime_status():
    """Get runtime status overview."""
    return _get().get_status()


@router.get("/api/runtime/champion")
async def runtime_champion():
    """Get current champion strategy."""
    orch = _get()
    if orch._champion_resolver:
        champ = orch._champion_resolver.get_current_champion()
        return {"champion": champ}
    return {"champion": None}


@router.get("/api/runtime/mode")
async def runtime_mode():
    """Get current runtime mode."""
    return _get()._mode_manager.get_status()


@router.post("/api/runtime/mode")
async def set_runtime_mode(mode: str = "observe"):
    """Set runtime mode. Only OBSERVE and SHADOW allowed in Phase 39."""
    return _get()._mode_manager.set_mode(mode)


@router.get("/api/runtime/shadow/status")
async def shadow_status():
    """Get shadow trading performance."""
    orch = _get()
    if orch._shadow_tracker:
        return orch._shadow_tracker.get_performance()
    return {"message": "Shadow tracking not available"}


@router.get("/api/runtime/shadow/trades")
async def shadow_trades():
    """Get all shadow trades."""
    orch = _get()
    if orch._shadow_tracker:
        return {"trades": [t.to_dict() for t in orch._shadow_tracker.get_all_trades()]}
    return {"trades": []}


@router.get("/api/runtime/shadow/{trade_id}")
async def shadow_trade_detail(trade_id: str):
    """Get shadow trade detail."""
    orch = _get()
    if not orch._shadow_tracker:
        raise HTTPException(status_code=404, detail="Shadow tracking not available")
    trade = orch._shadow_tracker.get_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade.to_dict()


@router.post("/api/runtime/shadow/close/{trade_id}")
async def close_shadow_trade(trade_id: str):
    """Close a shadow trade (virtual only). No broker interaction."""
    orch = _get()
    if not orch._shadow_tracker:
        raise HTTPException(status_code=404, detail="Shadow tracking not available")
    success = orch._shadow_tracker.close_trade(trade_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not close trade")
    return {"success": True}
