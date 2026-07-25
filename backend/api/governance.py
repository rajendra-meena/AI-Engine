"""Champion/Challenger Governance API — strategy versioning and final OOS verification."""

from __future__ import annotations

import random
from typing import Any

from fastapi import APIRouter, HTTPException

from backtest.strategy_version import ChampionManager
from backtest.challenger_validation import ChallengerValidationEngine

router = APIRouter(tags=["governance"])

_champion_manager = ChampionManager()
_validation_engine = ChallengerValidationEngine(_champion_manager)

# Register a default champion
_default = _champion_manager.create_version(
    name="Default Champion",
    confidence=65.0, strategy_score=60.0, min_rr=1.5, risk_pct=1.0,
    source="manual",
)
_champion_manager.register_champion(_default.version_id)
_validation_engine.set_champion_manager(_champion_manager)


@router.get("/api/backtest/governance/champion")
async def get_champion():
    """Get current champion strategy version."""
    champ = _champion_manager.get_champion()
    if not champ:
        return {"champion": None}
    return {"champion": champ.to_dict()}


@router.get("/api/backtest/governance/versions")
async def get_versions():
    """List all strategy versions."""
    return {"versions": [v.to_dict() for v in _champion_manager.get_all_versions()]}


@router.post("/api/backtest/governance/challenger")
async def create_challenger(params: dict[str, Any]):
    """Create a challenger strategy version from optimization or manual config."""
    confidence = params.get("confidence", 65.0)
    strategy_score = params.get("strategy_score", 60.0)
    min_rr = params.get("min_rr", 1.5)
    risk_pct = params.get("risk_pct", 1.0)
    source = params.get("source", "optimization")
    optimization_id = params.get("optimization_id", "")
    validation_id = params.get("validation_id", "")
    tags = params.get("tags", ["challenger"])

    version = _champion_manager.create_version(
        name=f"Challenger {source.upper()}",
        confidence=confidence,
        strategy_score=strategy_score,
        min_rr=min_rr,
        risk_pct=risk_pct,
        source=source,
        optimization_id=optimization_id,
        validation_id=validation_id,
        tags=tags,
    )
    _champion_manager.register_challenger(version.version_id)
    return {"success": True, "version": version.to_dict()}


@router.post("/api/backtest/governance/validate")
async def run_governance_validation(params: dict[str, Any]):
    """Run Champion vs Challenger final OOS validation."""
    champion_id = _champion_manager.get_champion_id()
    challenger_id = params.get("challenger_version_id", "")

    champion = _champion_manager.get_version(champion_id) if champion_id else None
    challenger = _champion_manager.get_version(challenger_id)

    if not champion or not challenger:
        raise HTTPException(status_code=400, detail="Champion or challenger not found")

    # Mock OOS metrics — in production these come from running both on final test data
    def _mock_metrics(base_pf=1.3):
        return {
            "total_trades": random.randint(30, 80),
            "net_pnl": random.uniform(500, 5000),
            "return_pct": random.uniform(2, 15),
            "win_rate": random.uniform(45, 65),
            "profit_factor": random.uniform(base_pf - 0.2, base_pf + 0.3),
            "expectancy": random.uniform(10, 50),
            "sharpe": random.uniform(0.3, 1.5),
            "sortino": random.uniform(0.4, 1.8),
            "max_drawdown_pct": random.uniform(8, 25),
            "avg_r": random.uniform(0.5, 2.0),
            "probability_of_ruin": random.uniform(2, 15),
            "mae": random.uniform(50, 200),
            "mfe": random.uniform(100, 400),
            "avg_holding_hours": random.uniform(1, 8),
        }

    champ_metrics = _mock_metrics(1.3)
    chall_metrics = _mock_metrics(1.35)

    report = _validation_engine.validate(
        champion=champion,
        challenger=challenger,
        champion_oos_metrics=champ_metrics,
        challenger_oos_metrics=chall_metrics,
        dataset_id=params.get("dataset_id", ""),
    )
    return report.to_dict()


@router.get("/api/backtest/governance/{report_id}")
async def get_governance_report(report_id: str):
    """Get a governance validation report."""
    report = _validation_engine.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report.to_dict()


@router.get("/api/backtest/governance/history")
async def governance_history():
    """List governance decisions."""
    return {
        "reports": [r.to_dict() for r in _validation_engine.get_all_reports()],
        "total": len(_validation_engine.get_all_reports()),
    }


@router.post("/api/backtest/governance/{report_id}/promote")
async def promote_challenger(report_id: str):
    """Promote challenger — only if governance decision is PROMOTE."""
    report = _validation_engine.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.decision != "promote":
        raise HTTPException(status_code=400, detail=f"Cannot promote: decision is {report.decision}")
    success = _champion_manager.promote_challenger(report.challenger_version)
    if not success:
        raise HTTPException(status_code=400, detail="Promotion failed")
    champ = _champion_manager.get_champion()
    return {"success": True, "decision": "promote", "champion": champ.to_dict() if champ else None}


@router.post("/api/backtest/governance/{report_id}/reject")
async def reject_challenger(report_id: str):
    """Reject a challenger."""
    report = _validation_engine.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    _champion_manager.reject_challenger(report.challenger_version)
    return {"success": True, "decision": "reject", "challenger_version": report.challenger_version}
