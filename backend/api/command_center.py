"""Command Center API — Phase 52 unified operations control plane.

All endpoints are read-only GET. No live-trading enabling endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["command-center"])

_engine = None


def set_command_center_engine(engine):
    global _engine
    _engine = engine


def _get():
    assert _engine is not None, "CommandCenterEngine not initialized"
    return _engine


@router.get("/api/operations/command-center")
async def command_center_full():
    """Get full unified system snapshot."""
    return _get().build_snapshot().to_dict()


@router.get("/api/operations/command-center/status")
async def command_center_status():
    """Get unified system status."""
    engine = _get()
    return {"unified_status": engine.build_snapshot().unified_status}


@router.get("/api/operations/command-center/system")
async def command_center_system():
    """Get system health status."""
    return _get().get_system_status()


@router.get("/api/operations/command-center/safety")
async def command_center_safety():
    """Get safety lock status."""
    return _get().get_safety_status()


@router.get("/api/operations/command-center/trading")
async def command_center_trading():
    """Get trading status."""
    return _get().get_trading_status()


@router.get("/api/operations/command-center/risk")
async def command_center_risk():
    """Get risk status."""
    return _get().get_risk_status()


@router.get("/api/operations/command-center/market")
async def command_center_market():
    """Get market data status."""
    engine = _get()
    return engine.build_snapshot().market.to_dict()


@router.get("/api/operations/command-center/broker")
async def command_center_broker():
    """Get broker status."""
    engine = _get()
    return engine.build_snapshot().broker.to_dict()


@router.get("/api/operations/command-center/orders")
async def command_center_orders():
    """Get execution/order status."""
    engine = _get()
    return engine.build_snapshot().execution.to_dict()


@router.get("/api/operations/command-center/positions")
async def command_center_positions():
    """Get position status."""
    engine = _get()
    return engine.build_snapshot().positions.to_dict()


@router.get("/api/operations/command-center/canary")
async def command_center_canary():
    """Get canary status."""
    engine = _get()
    return engine.build_snapshot().canary.to_dict()


@router.get("/api/operations/command-center/rollout")
async def command_center_rollout():
    """Get rollout status."""
    return _get().get_rollout_status()


@router.get("/api/operations/command-center/reconciliation")
async def command_center_reconciliation():
    """Get reconciliation status."""
    return _get().get_reconciliation_status()


@router.get("/api/operations/command-center/incidents")
async def command_center_incidents():
    """Get incident summary."""
    return _get().get_incident_summary()


@router.get("/api/operations/command-center/recovery")
async def command_center_recovery():
    """Get recovery status."""
    engine = _get()
    return engine.build_snapshot().recovery.to_dict()


@router.get("/api/operations/command-center/integrity")
async def command_center_integrity():
    """Get config/champion integrity status."""
    engine = _get()
    return engine.build_snapshot().integrity.to_dict()


@router.get("/api/operations/command-center/metrics")
async def command_center_metrics():
    """Get operational metrics."""
    engine = _get()
    return engine.build_snapshot().metrics.to_dict()


@router.get("/api/operations/command-center/events")
async def command_center_events(limit: int = 50):
    """Get recent operational events."""
    return {"events": _get().get_recent_events(limit=limit)}
