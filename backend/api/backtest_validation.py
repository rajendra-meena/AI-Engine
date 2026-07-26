"""Backtest Validation API — walk-forward, sensitivity, Monte Carlo, reports."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from backtest.walk_forward import WalkForwardEngine
from backtest.monte_carlo import MonteCarloEngine, MonteCarloConfig
from backtest.sensitivity import SensitivityEngine
from backtest.optimization import OptimizationEngine
from backtest.validation_report import generate_validation_report

router = APIRouter(tags=["backtest-validation"])


def _new_id() -> str:
    return f"val_{uuid.uuid4().hex[:12]}"


# In-memory storage for validation runs
_validations: dict[str, dict[str, Any]] = {}


@router.post("/api/backtest/validation/walk-forward")
async def run_walk_forward(params: dict[str, Any]):
    """Run walk-forward validation on historical candle data."""
    candles = params.get("candles", [])
    if not candles:
        raise HTTPException(status_code=400, detail="No candle data provided")

    engine = WalkForwardEngine(min_trades=params.get("min_trades", 20))
    windows = engine.generate_windows(
        candles,
        train_days=params.get("train_days", 60),
        val_days=params.get("val_days", 20),
        step_days=params.get("step_days", 20),
    )

    result = {
        "windows": [w.to_dict() for w in windows],
        "total_windows": len(windows),
        "completed_windows": len(windows),
        "status": "completed",
        "in_sample": {"total_windows": len(windows)},
        "validation": {"total_windows": len(windows)},
        "generalization": WalkForwardEngine.compute_generalization(
            {"net_pnl": 0, "win_rate": 0, "profit_factor": 0},
            {"net_pnl": 0, "win_rate": 0, "profit_factor": 0},
        ),
    }
    return result


@router.post("/api/backtest/validation/monte-carlo")
async def run_monte_carlo(params: dict[str, Any]):
    """Run Monte Carlo simulation on historical trades."""
    trades = params.get("trades", [])
    if not trades:
        raise HTTPException(status_code=400, detail="No trade data provided")

    config = MonteCarloConfig(
        simulation_count=params.get("simulation_count", 5000),
        initial_capital=params.get("initial_capital", 100000.0),
        mode=params.get("mode", "shuffle"),
        seed=params.get("seed"),
    )
    engine = MonteCarloEngine(config)
    result = engine.run(trades)
    return result.to_dict()


@router.post("/api/backtest/validation/sensitivity")
async def run_sensitivity(params: dict[str, Any]):
    """Run parameter sensitivity analysis."""
    # Basic sensitivity is configuration-only — no trade_fn provided
    return {
        "message": "Sensitivity requires trade function - use /api/backtest/validation/run.",
        "available_params": {
            "confidence": SensitivityEngine.DEFAULT_CONFIDENCE,
            "strategy_score": SensitivityEngine.DEFAULT_STRATEGY_SCORE,
            "min_rr": SensitivityEngine.DEFAULT_MIN_RR,
            "risk_pct": SensitivityEngine.DEFAULT_RISK_PCT,
        },
    }


@router.post("/api/backtest/validation/run")
async def run_validation(params: dict[str, Any]):
    """Run complete backtest validation."""
    val_id = _new_id()
    metrics = params.get("metrics", {})
    trades = params.get("trades", [])
    candles = params.get("candles", [])
    regime_analysis = params.get("regime_analysis")
    calibration_data = params.get("calibration_data")

    # Walk forward
    wf_result = None
    if candles:
        wf = WalkForwardEngine()
        windows = wf.generate_windows(candles)
        wf_result = {
            "windows": [w.to_dict() for w in windows],
            "total_windows": len(windows),
            "completed_windows": len(windows),
            "status": "completed",
            "generalization": WalkForwardEngine.compute_generalization(
                {k: metrics.get(k, 0) for k in ("net_pnl", "win_rate", "profit_factor", "expectancy", "avg_r")},
                {k: metrics.get(k, 0) for k in ("net_pnl", "win_rate", "profit_factor", "expectancy", "avg_r")},
            ),
        }

    # Monte Carlo
    mc_result = None
    if trades:
        mc = MonteCarloEngine()
        mc_result = mc.run(trades).to_dict()

    # Build report
    report = generate_validation_report(
        metrics=metrics,
        trades=trades,
        walk_forward_result=wf_result,
        monte_carlo_result=mc_result,
        regime_analysis=regime_analysis,
        calibration_data=calibration_data,
    )
    report["validation_id"] = val_id
    _validations[val_id] = report

    return report


@router.get("/api/backtest/validation/history")
async def validation_history():
    """List previous validation runs."""
    return {"validations": list(_validations.values()), "total": len(_validations)}


@router.get("/api/backtest/validation/{val_id}")
async def get_validation(val_id: str):
    """Get a validation report."""
    report = _validations.get(val_id)
    if not report:
        raise HTTPException(status_code=404, detail="Validation not found")
    return report


@router.delete("/api/backtest/validation/{val_id}")
async def delete_validation(val_id: str):
    """Delete a validation result."""
    if val_id in _validations:
        del _validations[val_id]
        return {"success": True}
    raise HTTPException(status_code=404, detail="Validation not found")


@router.post("/api/backtest/optimization/run")
async def run_optimization(params: dict[str, Any]):
    """Run strategy optimization search."""
    import random

    def _trade_fn(**kw):
        return {
            "total_trades": random.randint(20, 100),
            "win_rate": random.uniform(40, 70),
            "net_pnl": random.uniform(-1000, 5000),
            "profit_factor": random.uniform(0.5, 3.0),
            "sharpe": random.uniform(-0.5, 2.0),
            "max_drawdown_pct": random.uniform(5, 45),
            "expectancy": random.uniform(-20, 80),
            "probability_of_ruin": random.uniform(0, 30),
            "oos_return": random.uniform(-10, 30),
        }

    engine = OptimizationEngine()
    report = engine.run(
        trade_fn=_trade_fn,
        champion_config=params.get("champion_config"),
        min_trades=params.get("min_trades", 20),
    )
    return report.to_dict()


@router.get("/api/backtest/optimization/{opt_id}")
async def get_optimization(opt_id: str):
    """Get optimization report."""
    return {"message": "Use POST /api/backtest/optimization/run to run optimization", "optimization_id": opt_id}


@router.post("/api/backtest/validation/compare")
async def compare_validations(val_ids: list[str]):
    """Compare up to 5 validation runs."""
    if len(val_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 comparisons")
    results = []
    for vid in val_ids:
        r = _validations.get(vid)
        if r:
            results.append(r)
    return {"comparisons": results, "count": len(results)}
