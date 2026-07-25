"""Backtest API — production historical backtesting and replay validation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backtest.backtest_runner import BacktestRunner
from backtest.backtest_models import SUPPORTED_TIMEFRAMES, BacktestStatus
from backtest.data_loader import HistoricalDataLoader

router = APIRouter(tags=["backtest"])

_runner: BacktestRunner | None = None


def set_backtest_runner(runner: BacktestRunner):
    global _runner
    _runner = runner


def _get() -> BacktestRunner:
    assert _runner is not None, "BacktestRunner not initialized"
    return _runner


@router.post("/api/backtest/create")
async def create_backtest(params: dict[str, Any]):
    """Create a new backtest configuration."""
    runner = _get()
    timeframe = params.get("timeframe", "15m")
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe: {timeframe}")
    run_id = runner.create_run(
        symbol=params.get("symbol", "NIFTY 50"),
        timeframe=timeframe,
        start_date=params.get("start_date", ""),
        end_date=params.get("end_date", ""),
        initial_capital=params.get("initial_capital", 100000.0),
        name=params.get("name", ""),
        risk_per_trade_pct=params.get("risk_per_trade_pct", 2.0),
        max_positions=params.get("max_positions", 1),
        slippage_model=params.get("slippage_model", "none"),
        slippage_value=params.get("slippage_value", 0.0),
        brokerage_model=params.get("brokerage_model", "none"),
        brokerage_value=params.get("brokerage_value", 0.0),
        execution_model=params.get("execution_model", "next_open"),
        intrabar_rule=params.get("intrabar_rule", "conservative"),
        end_of_test_rule=params.get("end_of_test_rule", "force_close"),
    )
    return {"success": True, "backtest_id": run_id}


@router.post("/api/backtest/{backtest_id}/start")
async def start_backtest(backtest_id: str):
    """Start a backtest run."""
    runner = _get()
    run = runner.get_run(backtest_id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest not found")
    run.status = BacktestStatus.RUNNING
    return {"success": True, "status": "running"}


@router.get("/api/backtest/{backtest_id}/status")
async def backtest_status(backtest_id: str):
    """Get backtest status and progress."""
    runner = _get()
    run = runner.get_run(backtest_id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return run.to_dict()


@router.get("/api/backtest/{backtest_id}/result")
async def backtest_result(backtest_id: str):
    """Get backtest results."""
    runner = _get()
    run = runner.get_run(backtest_id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return {
        "metrics": run.metrics.to_dict() if run.metrics else None,
        "trades": [t.to_dict() if hasattr(t, 'to_dict') else t for t in run.trades],
    }


@router.get("/api/backtest/{backtest_id}/trades")
async def backtest_trades(backtest_id: str):
    """Get trades from a backtest."""
    runner = _get()
    run = runner.get_run(backtest_id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest not found")
    trades = [t.to_dict() if hasattr(t, 'to_dict') else t for t in run.trades]
    return {"trades": trades, "total": len(trades)}


@router.get("/api/backtest/history")
async def backtest_history():
    """Get backtest history."""
    runner = _get()
    runs = runner.get_all_runs()
    return {"backtests": [r.to_dict() for r in runs], "total": len(runs)}


@router.delete("/api/backtest/{backtest_id}")
async def delete_backtest(backtest_id: str):
    """Delete a backtest."""
    runner = _get()
    if not runner.delete_run(backtest_id):
        raise HTTPException(status_code=404, detail="Backtest not found")
    return {"success": True}


@router.post("/api/backtest/validate-data")
async def validate_backtest_data(data: list[dict[str, Any]], timeframe: str = Query("15m")):
    """Validate historical market data for backtesting."""
    tf_minutes = {"1m": 1, "2m": 2, "3m": 3, "5m": 5, "10m": 10, "15m": 15, "30m": 30, "60m": 60}
    minutes = tf_minutes.get(timeframe, 15)
    _, report = HistoricalDataLoader.validate_and_prepare(data, minutes)
    return report.to_dict()
