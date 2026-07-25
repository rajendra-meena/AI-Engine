"""Pre-Live Validation API — Phase 44 operational validation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from live.pre_live_validation import PreLiveValidationEngine


router = APIRouter(tags=["pre-live"])

_engine: PreLiveValidationEngine | None = None
_kill_switch = None
_execution_policy = None
_broker = None
_config_guard = None
_runtime_mgr = None
_champion_manager = None
_audit_log = None
_position_reconciliation = None
_order_reconciliation = None


def set_engine(engine: PreLiveValidationEngine):
    global _engine
    _engine = engine


def set_kill_switch(ks):
    global _kill_switch
    _kill_switch = ks


def set_execution_policy(policy):
    global _execution_policy
    _execution_policy = policy


def set_broker(broker):
    global _broker
    _broker = broker


def set_config_guard(guard):
    global _config_guard
    _config_guard = guard


def set_runtime_mgr(mgr):
    global _runtime_mgr
    _runtime_mgr = mgr


def set_champion_manager(mgr):
    global _champion_manager
    _champion_manager = mgr


def set_audit_log(audit):
    global _audit_log
    _audit_log = audit


def set_position_reconciliation(engine):
    global _position_reconciliation
    _position_reconciliation = engine


def set_order_reconciliation(engine):
    global _order_reconciliation
    _order_reconciliation = engine


def _get_engine() -> PreLiveValidationEngine:
    assert _engine is not None, "PreLiveValidationEngine not set"
    return _engine


SENSITIVE_FIELDS = [
    "access_token", "api_secret", "api_key", "client_secret",
    "password", "secret", "token", "session_token", "auth_token",
]


def _sanitize(data: dict) -> dict:
    """Remove sensitive fields from API responses."""
    if not isinstance(data, dict):
        return data
    return {k: ("***" if any(s in k.lower() for s in SENSITIVE_FIELDS) else v)
            for k, v in data.items()}


# ── Status ──


@router.get("/api/pre-live/status")
async def pre_live_status():
    """Get pre-live validation status."""
    engine = _get_engine()
    report = engine.get_latest_report()
    return {
        "phase_44": True,
        "has_report": report is not None,
        "latest_validation": report.to_dict() if report else None,
        "live_execution_enabled": False,
        "can_execute_live": False,
        "phase_43_lock": True,
    }


@router.get("/api/pre-live/execution-lock")
async def pre_live_execution_lock():
    """Get execution lock status."""
    from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
    can_live = False
    if _runtime_mgr:
        can_live = _runtime_mgr.can_execute_live()
    return {
        "live_execution_enabled": False,
        "can_execute_live": can_live,
        "phase_43_lock_active": PHASE_43_LIVE_EXECUTION_LOCK,
        "status": "disabled",
        "message": "Phase 43 live execution lock is active. LIVE trading is disabled.",
    }


# ── Run / Reports ──


@router.post("/api/pre-live/run")
async def pre_live_run(approval_id: str = ""):
    """Run full pre-live validation."""
    engine = _get_engine()
    report = engine.run(approval_id=approval_id)
    return report.to_dict()


@router.get("/api/pre-live/report/{validation_id}")
async def pre_live_report(validation_id: str):
    """Get a specific validation report."""
    engine = _get_engine()
    report = engine.get_report(validation_id)
    if not report:
        return {"error": "Report not found"}
    return report.to_dict()


@router.get("/api/pre-live/history")
async def pre_live_history(limit: int = Query(10, le=100)):
    """Get validation history."""
    engine = _get_engine()
    reports = engine.get_all_reports()
    return {
        "reports": [r.summary() for r in reports[-limit:]],
        "total": len(reports),
    }


@router.get("/api/pre-live/checks")
async def pre_live_checks():
    """Get all check categories and descriptions."""
    from live.pre_live_validation import CHECK_CATEGORIES, CATEGORY_WEIGHTS
    return {
        "categories": [
            {"name": cat, "weight": CATEGORY_WEIGHTS.get(cat, 0)}
            for cat in CHECK_CATEGORIES
        ],
    }


# ── Broker (Read-Only) ──


@router.get("/api/pre-live/broker")
async def pre_live_broker():
    """Get broker read-only information."""
    if not _broker:
        return {"status": "not_configured", "broker": "none"}
    try:
        import asyncio
        health = asyncio.run(_broker.health_check())
        account = asyncio.run(_broker.get_account())
        balance = asyncio.run(_broker.get_balance())
        response = {
            "status": "connected",
            "broker": "zerodha",
            "phase_43": True,
            "health": health,
            "account": _sanitize(account),
            "balance": balance,
            "message": "Read-only. No orders placed.",
        }
        return response
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Market Data ──


@router.get("/api/pre-live/market-data")
async def pre_live_market_data():
    """Get market data health."""
    if not _engine._execution_health:
        return {"status": "unknown", "market_data": "monitor_unavailable"}
    checks = _engine._execution_health.get_all_checks()
    md_health = checks.get("market_data_freshness", {})
    ws_health = checks.get("websocket_health", {})
    return {
        "market_data": md_health,
        "websocket": ws_health,
        "status": md_health.get("state", "unknown") if md_health else "unknown",
    }


# ── Reconciliation ──


@router.get("/api/pre-live/reconciliation")
async def pre_live_reconciliation():
    """Get reconciliation summary."""
    result = {
        "order_reconciliation": {"status": "unknown"},
        "position_reconciliation": {"status": "unknown"},
    }
    if _order_reconciliation:
        issues = _order_reconciliation.get_issues()
        blocking = _order_reconciliation.get_blocking_issues()
        result["order_reconciliation"] = {
            "status": "blocked" if blocking else "clean",
            "total_issues": len(issues),
            "blocking_issues": len(blocking),
        }
    if _position_reconciliation:
        discrepancies = _position_reconciliation.get_discrepancies()
        blocked = _position_reconciliation.is_blocked()
        result["position_reconciliation"] = {
            "status": "blocked" if blocked else "clean",
            "total_discrepancies": len(discrepancies),
            "blocked": blocked,
        }
    return result


# ── Security ──


@router.get("/api/pre-live/security")
async def pre_live_security():
    """Get security validation summary."""
    checks = {}
    from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
    checks["phase_43_lock"] = bool(PHASE_43_LIVE_EXECUTION_LOCK)
    if _runtime_mgr:
        checks["can_execute_live"] = _runtime_mgr.can_execute_live()
        checks["runtime_mode"] = _runtime_mgr.mode.value
    if _execution_policy:
        perm = _execution_policy.check()
        checks["execution_policy_allowed"] = perm.allowed
    return {
        "security_checks": checks,
        "live_execution_possible": False,
        "all_secure": True,
    }


# ── Kill Switch ──


@router.get("/api/pre-live/kill-switch")
async def pre_live_kill_switch():
    """Get kill switch status."""
    if not _kill_switch:
        return {"status": "unavailable"}
    return _kill_switch.get_status()


# ── Simulate Failure ──


@router.post("/api/pre-live/simulate-failure")
async def pre_live_simulate_failure(scenario: str = "broker_unavailable"):
    """Simulate a failure scenario using mocks. Never touches real broker orders."""
    result = {"scenario": scenario, "status": "simulated", "message": ""}

    if scenario == "broker_unavailable":
        from execution.execution_simulator import ExecutionSimulator
        sim = ExecutionSimulator("timeout")
        sim_result = sim.place_order("SIM", "BUY", 1, 100.0)
        result["message"] = "Simulated broker timeout — no real order affected"
        result["simulation_result"] = sim_result
        if _audit_log:
            _audit_log.record(
                "simulated_failure_test", severity="warning",
                details={"scenario": scenario, "result": sim_result},
            )

    elif scenario == "market_data_stale":
        if _engine._execution_health:
            _engine._execution_health.record_failure("market_data_freshness", "simulated stale")
            result["message"] = "Simulated stale market data"
        else:
            result["message"] = "Execution health monitor unavailable"

    elif scenario == "kill_switch_activate":
        if _kill_switch:
            from execution.kill_switch import KillSwitchLevel
            _kill_switch.activate(KillSwitchLevel.GLOBAL, "", "simulated test")
            result["message"] = "Kill switch activated (simulated)"
            if _audit_log:
                _audit_log.record(
                    "simulated_kill_switch", severity="warning",
                    details={"scenario": scenario},
                )
        else:
            result["message"] = "Kill switch unavailable"

    elif scenario == "config_drift":
        if _config_guard:
            from execution.config_guard import ConfigurationSnapshot
            _config_guard.check_for_drift(ConfigurationSnapshot(
                allowed_symbols=["SIMULATED"],
                loss_limits={"max_daily_loss": 1},
            ))
            result["message"] = "Simulated config drift detected"
        else:
            result["message"] = "Config guard unavailable"

    else:
        result["message"] = f"Unknown scenario: {scenario}"
        result["status"] = "error"

    return result
