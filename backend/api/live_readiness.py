"""Live Readiness API — production safety gate and audit endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from live.readiness_engine import LiveReadinessEngine

router = APIRouter(tags=["live-readiness"])

_engine: LiveReadinessEngine | None = None


def set_readiness_engine(engine: LiveReadinessEngine):
    global _engine
    _engine = engine


def _get() -> LiveReadinessEngine:
    assert _engine is not None, "Readiness engine not initialized"
    return _engine


@router.get("/api/live-readiness/status")
async def readiness_status():
    """Get latest readiness status."""
    engine = _get()
    reports = engine.get_all_reports()
    if reports:
        return reports[-1].to_dict()
    return {"status": "no_reports", "message": "Run readiness check first"}


@router.post("/api/live-readiness/run")
async def run_readiness():
    """Run full readiness evaluation."""
    report = _get().run()
    return report.to_dict()


@router.get("/api/live-readiness/report/{report_id}")
async def get_readiness_report(report_id: str):
    """Get a specific readiness report."""
    report = _get().get_report(report_id)
    if not report:
        return {"error": "Not found"}
    return report.to_dict()


@router.get("/api/live-readiness/history")
async def readiness_history():
    """Get all readiness reports."""
    return {"reports": [r.to_dict() for r in _get().get_all_reports()]}


@router.get("/api/live-readiness/checks")
async def readiness_checks():
    """Get readiness check categories."""
    return {
        "checks": [
            {"name": "champion", "label": "Champion Strategy", "required": True},
            {"name": "shadow", "label": "Shadow Validation", "required": True},
            {"name": "risk", "label": "RiskEngine", "required": True},
            {"name": "safety", "label": "Runtime Safety", "required": True},
            {"name": "market_data", "label": "Market Data Health", "required": True},
            {"name": "broker", "label": "Broker Connectivity", "required": False},
            {"name": "trading", "label": "SL/Target & Sizing", "required": True},
            {"name": "data", "label": "Data Quality", "required": True},
        ]
    }


@router.get("/api/live-readiness/config")
async def readiness_config():
    """Get read-only configuration snapshot."""
    return {
        "runtime_mode": "observe/shadow",
        "live_execution": False,
        "live_auto_trading": False,
        "phase_39_lock": True,
        "note": "Read-only configuration snapshot. LIVE trading is NOT enabled.",
    }


@router.get("/api/live-readiness/safety")
async def readiness_safety():
    """Get safety status summary."""
    return {
        "observe_enabled": True,
        "shadow_enabled": True,
        "paper_enabled": False,
        "live_enabled": False,
        "live_auto_trading": False,
        "risk_firewall": True,
        "execution_gateway": True,
        "idempotency": True,
        "kill_switch": True,
        "daily_loss_limit": True,
    }
