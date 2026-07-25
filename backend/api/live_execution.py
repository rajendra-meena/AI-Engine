"""Live Execution API — Phase 46 controlled live execution endpoints.

All endpoints are read-only, validation-only, or require explicit human action.
No unrestricted live trading endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from live.execution_controller import Phase46ExecutionController
from live.broker_session import BrokerSessionManager
from live.preflight import PreflightValidator
from live.dry_run_executor import DryRunExecutor
from live.canary import CanaryExecutionManager
from live.execution_limits import ExecutionRiskLimiter
from live.order_reconciliation import LiveOrderReconciliation
from live.position_reconciliation import LivePositionReconciliation

router = APIRouter(tags=["live-execution"])

_controller: Phase46ExecutionController | None = None
_broker_session: BrokerSessionManager | None = None
_preflight: PreflightValidator | None = None
_dry_run: DryRunExecutor | None = None
_canary: CanaryExecutionManager | None = None
_limits: ExecutionRiskLimiter | None = None
_order_recon: LiveOrderReconciliation | None = None
_position_recon: LivePositionReconciliation | None = None


def set_controller(c): global _controller; _controller = c  # noqa
def set_broker_session(s): global _broker_session; _broker_session = s  # noqa
def set_preflight(p): global _preflight; _preflight = p  # noqa
def set_dry_run(d): global _dry_run; _dry_run = d  # noqa
def set_canary(c): global _canary; _canary = c  # noqa
def set_limits(l): global _limits; _limits = l  # noqa
def set_order_recon(r): global _order_recon; _order_recon = r  # noqa
def set_position_recon(r): global _position_recon; _position_recon = r  # noqa


def _get_controller() -> Phase46ExecutionController:
    assert _controller is not None, "Phase46ExecutionController not initialized"
    return _controller


SENSITIVE_FIELDS = [
    "access_token", "api_secret", "api_key", "client_secret",
    "password", "secret", "token", "session_token", "auth_token",
]


def _sanitize(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    return {k: ("***" if any(s in k.lower() for s in SENSITIVE_FIELDS) else v)
            for k, v in data.items()}


# ── Status ──


@router.get("/api/live-execution/status")
async def live_execution_status():
    """Get full live execution status."""
    controller = _get_controller()
    return controller.get_status()


@router.get("/api/live-execution/broker-session")
async def live_execution_broker_session():
    """Get broker session validation status."""
    global _broker_session
    if not _broker_session:
        return {"status": "not_configured"}
    import asyncio
    status = await _broker_session.get_status()
    return _sanitize(status)


@router.post("/api/live-execution/preflight")
async def live_execution_preflight(
    symbol: str = "", side: str = "BUY", quantity: int = 0,
    price: float | None = None, stop_loss: float | None = None,
    target: float | None = None, signal_id: str = "",
    strategy_version: str = "",
):
    """Run preflight validation for a potential order."""
    global _preflight
    if not _preflight:
        return {"error": "Preflight validator not configured"}
    result = _preflight.validate(
        symbol=symbol, side=side, quantity=quantity,
        price=price, stop_loss=stop_loss, target=target,
        signal_id=signal_id, strategy_version=strategy_version,
    )
    return result.to_dict()


@router.post("/api/live-execution/dry-run")
async def live_execution_dry_run(
    symbol: str = "", side: str = "BUY", quantity: int = 0,
    price: float | None = None, stop_loss: float | None = None,
    target: float | None = None, signal_id: str = "",
    strategy_version: str = "",
):
    """Run a complete dry-run execution. Never sends to broker."""
    global _dry_run
    if not _dry_run:
        return {"error": "Dry run executor not configured"}
    result = _dry_run.execute(
        symbol=symbol, side=side, quantity=quantity,
        price=price, stop_loss=stop_loss, target=target,
        signal_id=signal_id, strategy_version=strategy_version,
    )
    return result.to_dict()


# ── Canary ──


@router.post("/api/live-execution/canary/arm")
async def live_execution_canary_arm(reviewer: str = "", reason: str = ""):
    """Arm canary mode with explicit human confirmation."""
    global _canary
    if not _canary:
        return {"error": "Canary manager not configured"}
    result = _canary.arm(reviewer=reviewer, reason=reason)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Arm failed"))
    return result


@router.post("/api/live-execution/canary/disarm")
async def live_execution_canary_disarm():
    """Disarm canary mode."""
    global _canary
    if not _canary:
        return {"error": "Canary manager not configured"}
    return _canary.disarm()


@router.get("/api/live-execution/canary/status")
async def live_execution_canary_status():
    """Get canary mode status."""
    global _canary
    if not _canary:
        return {"status": "not_configured"}
    return _canary.get_status()


# ── Orders ──


@router.get("/api/live-execution/orders")
async def live_execution_orders(limit: int = 50):
    """Get all live execution orders."""
    controller = _get_controller()
    return {
        "executions": controller.get_executions(limit=limit),
        "total": len(controller.get_executions(limit=1000)),
    }


@router.get("/api/live-execution/orders/{execution_id}")
async def live_execution_order(execution_id: str):
    """Get a specific execution detail."""
    controller = _get_controller()
    exec_result = controller.get_execution(execution_id)
    if not exec_result:
        raise HTTPException(status_code=404, detail="Execution not found")
    return exec_result.to_dict()


@router.get("/api/live-execution/positions")
async def live_execution_positions():
    """Get position reconciliation status."""
    global _position_recon
    if not _position_recon:
        return {"status": "not_configured"}
    return {
        "blocked": _position_recon.is_blocked(),
        "results": _position_recon.get_results(limit=20),
    }


@router.post("/api/live-execution/reconcile")
async def live_execution_reconcile():
    """Run reconciliation for orders and positions."""
    results = {
        "order": {"status": "not_configured"},
        "position": {"status": "not_configured"},
    }
    if _order_recon:
        results["order"] = {
            "blocked": _order_recon.is_blocked(),
            "results": _order_recon.get_results(limit=10),
        }
    if _position_recon:
        results["position"] = {
            "blocked": _position_recon.is_blocked(),
            "results": _position_recon.get_results(limit=10),
        }
    return results


@router.post("/api/live-execution/emergency-cancel")
async def live_execution_emergency_cancel(reason: str = "manual_emergency"):
    """Emergency cancel all open orders. Blocks new entries."""
    global _broker_session
    from live.emergency_cancel import EmergencyCancelManager
    cancel_mgr = EmergencyCancelManager()
    if _broker_session and hasattr(_broker_session, '_broker') and _broker_session._broker:
        import asyncio
        result = await cancel_mgr.cancel_all_open_orders(
            broker=_broker_session._broker,
            reason=reason,
        )
        return result.to_dict()
    return {"error": "Broker not available for emergency cancel"}


@router.get("/api/live-execution/limits")
async def live_execution_limits():
    """Get current execution limit configuration."""
    global _limits
    if not _limits:
        return {"status": "not_configured"}
    return _limits.get_status()


@router.get("/api/live-execution/audit")
async def live_execution_audit(limit: int = 100):
    """Get execution audit events."""
    controller = _get_controller()
    from execution.execution_audit import ExecutionAuditLog
    if hasattr(controller, '_audit_log') and controller._audit_log:
        entries = controller._audit_log.get_entries(limit=limit)
        live_entries = [
            e for e in entries
            if "live" in e.get("event_type", "").lower()
            or "preflight" in e.get("event_type", "").lower()
            or e.get("details", {}).get("component") in (
                "execution_controller", "preflight", "canary",
                "broker_session", "dry_run",
            )
        ]
        return {"audit_events": live_entries, "total": len(live_entries)}
    return {"audit_events": [], "total": 0}
