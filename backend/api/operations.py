"""Operations API — Phase 50 production reliability, recovery & monitoring.

All endpoints are read-only monitoring/reconciliation.
No live-trading enabling endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["operations"])

# Module-level globals (set via DI)
_health_monitor = None
_heartbeat = None
_alert_mgr = None
_recovery_mgr = None
_daily_rec = None
_dr_mgr = None
_config_monitor = None


def set_health_monitor(m):
    global _health_monitor
    _health_monitor = m


def set_heartbeat(h):
    global _heartbeat
    _heartbeat = h


def set_alert_manager(a):
    global _alert_mgr
    _alert_mgr = a


def set_recovery_manager(r):
    global _recovery_mgr
    _recovery_mgr = r


def set_daily_reconciliation(r):
    global _daily_rec
    _daily_rec = r


def set_disaster_recovery(d):
    global _dr_mgr
    _dr_mgr = d


def set_config_monitor(c):
    global _config_monitor
    _config_monitor = c


# ── Health & Heartbeat ──


@router.get("/api/operations/health")
async def ops_health():
    if _health_monitor:
        return _health_monitor.snapshot()
    return {"status": "unknown", "error": "Health monitor not configured"}


@router.get("/api/operations/heartbeat")
async def ops_heartbeat():
    if _heartbeat:
        return {"heartbeats": _heartbeat.get_summary()}
    return {"status": "unknown"}


@router.get("/api/operations/broker")
async def ops_broker():
    """Get broker watchdog status."""
    return {"status": "not_implemented", "message": "Broker watchdog check"}


@router.get("/api/operations/market-data")
async def ops_market_data():
    """Get market data watchdog status."""
    return {"status": "not_implemented", "message": "Market data watchdog check"}


@router.get("/api/operations/execution")
async def ops_execution():
    """Get execution watchdog status."""
    return {"status": "not_implemented", "message": "Execution watchdog check"}


@router.get("/api/operations/orders")
async def ops_orders():
    """Get order status overview."""
    return {"status": "not_implemented"}


@router.get("/api/operations/positions")
async def ops_positions():
    """Get position status overview."""
    return {"status": "not_implemented"}


@router.get("/api/operations/risk")
async def ops_risk():
    """Get risk watchdog status."""
    return {"status": "not_implemented", "message": "Risk watchdog check"}


@router.get("/api/operations/reconciliation")
async def ops_reconciliation():
    """Get reconciliation status."""
    if _daily_rec:
        reports = _daily_rec.get_reports(limit=5)
        return {"reports": reports, "total": len(reports)}
    return {"status": "not_configured"}


@router.get("/api/operations/recovery")
async def ops_recovery():
    """Get recovery status."""
    if _recovery_mgr:
        return {"state": _recovery_mgr.get_state()}
    return {"state": "not_configured"}


@router.get("/api/operations/alerts")
async def ops_alerts(limit: int = 50):
    """Get active alerts and alert history."""
    if _alert_mgr:
        return {
            "active": [a.to_dict() for a in _alert_mgr.get_active()],
            "history": _alert_mgr.get_history(limit=limit),
            "active_count": _alert_mgr.active_count(),
        }
    return {"active": [], "history": [], "active_count": 0}


@router.get("/api/operations/audit")
async def ops_audit(limit: int = 100):
    """Get operations-related audit events."""
    return {"audit_events": [], "total": 0}


@router.get("/api/operations/config-integrity")
async def ops_config_integrity():
    """Get config integrity status."""
    if _config_monitor:
        return _config_monitor.check_integrity().to_dict()
    return {"passed": True, "note": "Config integrity monitor not configured"}


@router.get("/api/operations/champion-integrity")
async def ops_champion_integrity():
    """Get champion integrity status."""
    return {"status": "not_implemented", "message": "Champion integrity check"}


@router.get("/api/operations/status")
async def ops_status():
    """Get aggregated operations status."""
    return {
        "health": _health_monitor.get_status() if _health_monitor else "unknown",
        "recovery_state": _recovery_mgr.get_state() if _recovery_mgr else "unknown",
        "active_alerts": _alert_mgr.active_count() if _alert_mgr else 0,
    }


# ── Actions ──


@router.post("/api/operations/reconcile")
async def ops_reconcile():
    """Run on-demand reconciliation."""
    if _daily_rec:
        report = _daily_rec.reconcile()
        return report.to_dict()
    return {"status": "not_configured"}


@router.post("/api/operations/acknowledge-alert")
async def ops_acknowledge_alert(alert_id: str = "", reviewer: str = ""):
    """Acknowledge an alert. Requires reviewer identity."""
    if not _alert_mgr:
        return {"status": "not_configured"}
    alert = _alert_mgr.acknowledge(alert_id, reviewer=reviewer)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert.to_dict()


@router.post("/api/operations/request-recovery")
async def ops_request_recovery(reviewer: str = ""):
    """Request human recovery review."""
    if _recovery_mgr:
        result = _recovery_mgr.request_human_recovery(reviewer=reviewer)
        return result
    return {"success": False, "error": "Recovery manager not configured"}
