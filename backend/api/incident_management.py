"""Incident Management API — Phase 51 observability and incident response.

All mutation endpoints require reviewer identity, reason, and notes.
No live-trading enabling endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["incident-management"])

_incident_mgr = None
_event_bus = None
_runbook_engine = None
_metrics = None


def set_incident_manager(m):
    global _incident_mgr
    _incident_mgr = m


def set_event_bus(b):
    global _event_bus
    _event_bus = b


def set_runbook_engine(r):
    global _runbook_engine
    _runbook_engine = r


def set_metrics(m):
    global _metrics
    _metrics = m


# ── Incidents ──


@router.get("/api/operations/incidents")
async def get_incidents():
    """Get all incidents."""
    if _incident_mgr:
        return {"incidents": [i.to_dict() for i in _incident_mgr.get_all()]}
    return {"incidents": []}


@router.get("/api/operations/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Get a specific incident."""
    if not _incident_mgr:
        raise HTTPException(status_code=503, detail="Incident manager not configured")
    inc = _incident_mgr.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc.to_dict()


@router.get("/api/operations/incidents/open")
async def get_open_incidents():
    """Get all open incidents."""
    if _incident_mgr:
        return {"incidents": [i.to_dict() for i in _incident_mgr.get_open()]}
    return {"incidents": []}


@router.get("/api/operations/incidents/critical")
async def get_critical_incidents():
    """Get all critical/emergency incidents."""
    if _incident_mgr:
        return {"incidents": [i.to_dict() for i in _incident_mgr.get_critical()]}
    return {"incidents": []}


@router.get("/api/operations/incidents/history")
async def get_incident_history(limit: int = 50):
    """Get incident history."""
    if _incident_mgr:
        return {"history": _incident_mgr.get_history(limit=limit)}
    return {"history": []}


@router.post("/api/operations/incidents/{incident_id}/acknowledge")
async def acknowledge_incident(incident_id: str, reviewer: str = ""):
    """Acknowledge an incident. Requires reviewer identity."""
    if not _incident_mgr:
        raise HTTPException(status_code=503, detail="Incident manager not configured")
    try:
        inc = _incident_mgr.acknowledge(incident_id, reviewer=reviewer)
        return inc.to_dict()
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/operations/incidents/{incident_id}/mitigate")
async def mitigate_incident(incident_id: str, notes: str = ""):
    """Start mitigation for an incident."""
    if not _incident_mgr:
        raise HTTPException(status_code=503, detail="Incident manager not configured")
    try:
        inc = _incident_mgr.start_mitigation(incident_id, notes=notes)
        return inc.to_dict()
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/operations/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str, reviewer: str = "",
                           reason: str = "", notes: str = ""):
    """Resolve an incident. Requires reviewer + reason."""
    if not _incident_mgr:
        raise HTTPException(status_code=503, detail="Incident manager not configured")
    try:
        inc = _incident_mgr.resolve(
            incident_id, reviewer=reviewer, reason=reason, notes=notes,
        )
        return inc.to_dict()
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/operations/incidents/{incident_id}/close")
async def close_incident(incident_id: str, reviewer: str = "", notes: str = ""):
    """Close an incident. Requires reviewer identity."""
    if not _incident_mgr:
        raise HTTPException(status_code=503, detail="Incident manager not configured")
    try:
        inc = _incident_mgr.close(incident_id, reviewer=reviewer, notes=notes)
        return inc.to_dict()
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Events ──


@router.get("/api/operations/events")
async def get_events(limit: int = 50):
    """Get recent operational events."""
    if _event_bus:
        return {"events": _event_bus.get_recent(limit=limit)}
    return {"events": []}


@router.get("/api/operations/events/{event_id}")
async def get_event(event_id: str):
    """Get a specific event."""
    if not _event_bus:
        raise HTTPException(status_code=503, detail="Event bus not configured")
    event = _event_bus.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.to_dict()


# ── Runbooks ──


@router.get("/api/operations/runbooks")
async def get_runbooks():
    """Get all runbook types."""
    if _runbook_engine:
        return {"runbooks": _runbook_engine.get_all()}
    return {"runbooks": {}}


@router.get("/api/operations/runbooks/{incident_type}")
async def get_runbook(incident_type: str):
    """Get a specific runbook."""
    if not _runbook_engine:
        raise HTTPException(status_code=503, detail="Runbook engine not configured")
    runbook = _runbook_engine.get_runbook(incident_type)
    if isinstance(runbook, dict) and "error" in runbook:
        raise HTTPException(status_code=404, detail=runbook["error"])
    return runbook.to_dict() if hasattr(runbook, 'to_dict') else runbook


# ── Summary ──


@router.get("/api/operations/summary")
async def operations_summary():
    """Get unified operational summary."""
    inc_mgr = _incident_mgr
    bus = _event_bus
    metrics = _metrics

    active_incidents = len(inc_mgr.get_open()) if inc_mgr else 0
    critical_incidents = len(inc_mgr.get_critical()) if inc_mgr else 0
    events = bus.get_recent(limit=1) if bus else []
    last_event = events[0] if events else None
    health_score = metrics.get_health_score() if metrics else 100.0

    return {
        "system_state": "operational",
        "trading_allowed": False,
        "live_execution_locked": True,
        "active_incidents": active_incidents,
        "critical_incidents": critical_incidents,
        "health_score": health_score,
        "broker": "monitored",
        "market_data": "monitored",
        "execution": "monitored",
        "reconciliation": "monitored",
        "risk": "monitored",
        "recovery": "available",
        "last_event": last_event["event_type"] if last_event else None,
        "last_event_timestamp": last_event["timestamp"] if last_event else None,
        "requires_human_review": critical_incidents > 0,
    }
