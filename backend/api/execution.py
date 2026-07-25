"""Execution Infrastructure API — Phase 43: no live order placement."""

from __future__ import annotations

from fastapi import APIRouter, Query

from execution.kill_switch import KillSwitch, KillSwitchLevel
from execution.execution_policy import ExecutionPolicyEngine
from execution.execution_audit import ExecutionAuditLog
from execution.execution_simulator import ExecutionSimulator
from execution.execution_health import ExecutionHealthMonitor
from execution.reconciliation import OrderReconciliationEngine
from execution.position_reconciliation import PositionReconciliationEngine
from execution.config_guard import ConfigGuard
from execution.emergency import EmergencyShutdown
from execution.idempotency import IdempotencyGuard
from execution.broker_adapter import ZerodhaAdapter


router = APIRouter(tags=["execution"])

_policy: ExecutionPolicyEngine | None = None
_kill_switch: KillSwitch | None = None
_audit: ExecutionAuditLog | None = None
_health: ExecutionHealthMonitor | None = None
_order_reconciliation: OrderReconciliationEngine | None = None
_position_reconciliation: PositionReconciliationEngine | None = None
_config_guard: ConfigGuard | None = None
_emergency: EmergencyShutdown | None = None
_idempotency: IdempotencyGuard | None = None
_broker: ZerodhaAdapter | None = None


def set_policy_engine(engine: ExecutionPolicyEngine):
    global _policy
    _policy = engine


def set_kill_switch(ks: KillSwitch):
    global _kill_switch
    _kill_switch = ks


def set_audit_log(audit: ExecutionAuditLog):
    global _audit
    _audit = audit


def set_health_monitor(health: ExecutionHealthMonitor):
    global _health
    _health = health


def set_order_reconciliation(engine: OrderReconciliationEngine):
    global _order_reconciliation
    _order_reconciliation = engine


def set_position_reconciliation(engine: PositionReconciliationEngine):
    global _position_reconciliation
    _position_reconciliation = engine


def set_config_guard(guard: ConfigGuard):
    global _config_guard
    _config_guard = guard


def set_emergency_shutdown(emergency: EmergencyShutdown):
    global _emergency
    _emergency = emergency


def set_idempotency(guard: IdempotencyGuard):
    global _idempotency
    _idempotency = guard


def set_broker(broker: ZerodhaAdapter):
    global _broker
    _broker = broker


def _get_policy() -> ExecutionPolicyEngine:
    assert _policy is not None, "ExecutionPolicyEngine not set"
    return _policy


def _get_kill_switch() -> KillSwitch:
    assert _kill_switch is not None, "KillSwitch not set"
    return _kill_switch


def _get_audit() -> ExecutionAuditLog:
    assert _audit is not None, "ExecutionAuditLog not set"
    return _audit


# ── Status ──


@router.get("/api/execution/status")
async def execution_status():
    """Get execution infrastructure status."""
    ks_status = _kill_switch.get_status() if _kill_switch else {"active": False}
    policy_result = _policy.check().to_dict() if _policy else {"allowed": False}
    health_status = _health.get_status() if _health else {"overall": "unknown"}
    emergency_status = _emergency.get_status() if _emergency else {"active": False}
    config_status = _config_guard.get_status() if _config_guard else {"drift_detected": False}

    return {
        "phase_43_lock": True,
        "live_execution_possible": False,
        "can_execute_live": False,
        "kill_switch": ks_status,
        "policy": policy_result,
        "health": health_status,
        "emergency": emergency_status,
        "config_guard": config_status,
        "reconciliation_blocked": (
            _order_reconciliation and len(_order_reconciliation.get_blocking_issues()) > 0
        ) or (
            _position_reconciliation and _position_reconciliation.is_blocked()
        ),
    }


@router.get("/api/execution/health")
async def execution_health():
    """Get execution health monitor status."""
    if not _health:
        return {"overall": "unknown", "healthy": False}
    return _health.get_status()


# ── Policy ──


@router.get("/api/execution/policy")
async def execution_policy(
    symbol: str = Query("", description="Symbol to check"),
    side: str = Query("", description="Trade side"),
    quantity: int = Query(0, description="Trade quantity"),
    price: float | None = Query(None, description="Trade price"),
    stop_loss: float | None = Query(None, description="Stop loss price"),
    target: float | None = Query(None, description="Target price"),
):
    """Get current execution policy. Allowed is always False in Phase 43."""
    if not _policy:
        return {"allowed": False, "reason": "Policy engine unavailable"}
    return _policy.check(
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        stop_loss=stop_loss,
        target=target,
    ).to_dict()


# ── Kill Switch ──


@router.get("/api/execution/kill-switch")
async def kill_switch_status():
    """Get kill switch status."""
    if not _kill_switch:
        return {"active": False}
    return _kill_switch.get_status()


@router.post("/api/execution/kill-switch/activate")
async def activate_kill_switch(reason: str = "manual"):
    """Activate global kill switch. Blocks all execution."""
    if not _kill_switch:
        return {"error": "Kill switch unavailable"}
    result = _kill_switch.activate(KillSwitchLevel.GLOBAL, "", reason)
    if _audit:
        _audit.record("kill_switch_activated", severity="critical", reason=reason)
    return result


@router.post("/api/execution/kill-switch/reset")
async def reset_kill_switch():
    """Reset global kill switch."""
    if not _kill_switch:
        return {"error": "Kill switch unavailable"}
    _kill_switch.reset(KillSwitchLevel.GLOBAL)
    if _audit:
        _audit.record("kill_switch_reset", severity="warning")
    return {"success": True}


# ── Audit ──


@router.get("/api/execution/audit")
async def execution_audit(limit: int = Query(100, le=1000)):
    """Get execution audit log."""
    if not _audit:
        return {"entries": [], "total": 0}
    return {"entries": _audit.get_entries(limit), "total": _audit.count()}


# ── Orders ──


@router.get("/api/execution/orders")
async def execution_orders(limit: int = Query(100, le=1000)):
    """Get execution orders. Phase 43: no live orders exist."""
    # In Phase 43, this returns the audit trail filtered for order events
    if not _audit:
        return {"orders": [], "total": 0}
    entries = _audit.get_entries(limit)
    order_events = [e for e in entries if "order" in e.get("event_type", "").lower()]
    return {"orders": order_events, "total": len(order_events)}


@router.get("/api/execution/order/{order_id}")
async def execution_order(order_id: str):
    """Get a specific order by ID."""
    if not _audit:
        return {"error": "Audit log unavailable"}
    entries = _audit.get_entries(1000)
    order_events = [
        e for e in entries
        if e.get("order_id") == order_id
    ]
    return {
        "order_id": order_id,
        "events": order_events,
        "event_count": len(order_events),
    }


# ── Reconciliation ──


@router.get("/api/execution/reconciliation")
async def order_reconciliation():
    """Get order reconciliation status."""
    if not _order_reconciliation:
        return {"issues": [], "blocking": [], "total": 0}
    return {
        "issues": [i.to_dict() for i in _order_reconciliation.get_issues()],
        "blocking": [i.to_dict() for i in _order_reconciliation.get_blocking_issues()],
        "total": _order_reconciliation.count(),
    }


@router.get("/api/execution/positions/reconciliation")
async def position_reconciliation():
    """Get position reconciliation status."""
    if not _position_reconciliation:
        return {"discrepancies": [], "blocked": False, "total": 0}
    return {
        "discrepancies": [d.to_dict() for d in _position_reconciliation.get_discrepancies()],
        "blocked": _position_reconciliation.is_blocked(),
        "total": _position_reconciliation.count(),
    }


# ── Config Guard ──


@router.get("/api/execution/config-hash")
async def config_hash():
    """Get configuration guard status."""
    if not _config_guard:
        return {"status": "unavailable"}
    return _config_guard.get_status()


# ── Emergency ──


@router.post("/api/execution/emergency/stop")
async def emergency_stop(reason: str = "Manual emergency stop"):
    """Trigger emergency stop. Activates kill switch and blocks execution."""
    if not _emergency:
        return {"error": "Emergency shutdown unavailable"}
    result = _emergency.emergency_stop(
        triggered_by="api",
        reason=reason,
        kill_switch=_kill_switch,
        audit_log=_audit,
    )
    return {"emergency_stop": result.to_dict()}


@router.post("/api/execution/emergency/recover")
async def emergency_recover():
    """Begin recovery from emergency stop."""
    if not _emergency:
        return {"error": "Emergency shutdown unavailable"}
    success = _emergency.recover(audit_log=_audit)
    return {"success": success}


# ── Simulation ──


@router.post("/api/execution/simulate")
async def execution_simulate(mode: str = "happy_path"):
    """Run broker simulator for testing. Never connects to a real broker."""
    sim = ExecutionSimulator(mode)
    result = sim.place_order("SIMULATED", "BUY", 1, 100.0)
    scenario = sim.get_scenario_info()
    return {
        "mode": mode,
        "scenario": scenario,
        "result": result,
        "note": "Simulated only. No real order placed. Phase 43: live execution disabled.",
    }


@router.get("/api/execution/simulate/scenarios")
async def simulation_scenarios():
    """Get available simulation scenarios."""
    from execution.execution_simulator import SIMULATION_SCENARIOS
    return {"scenarios": SIMULATION_SCENARIOS}
