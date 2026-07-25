"""Performance Analytics API — paper trading validation and replay integration."""

from __future__ import annotations

from fastapi import APIRouter, Query

from execution.paper_broker import get_paper_broker
from performance import analytics as pa


router = APIRouter(tags=["performance"])


def _get_trades():
    """Get all paper trade history."""
    return get_paper_broker().get_trades()


def _get_blocked():
    """Get blocked trades — currently returns empty list.
    In production, this would read from the Learning Engine's blocked_trade table.
    """
    return []


@router.get("/api/performance/overview")
async def performance_overview():
    """Get overall performance summary."""
    trades = _get_trades()
    blocked = _get_blocked()
    return pa.compute_overview(trades, blocked)


@router.get("/api/performance/funnel")
async def performance_funnel():
    """Get signal funnel breakdown."""
    trades = _get_trades()
    total = len(trades)
    buy = sum(1 for t in trades if t.get("direction") == "LONG")
    sell = sum(1 for t in trades if t.get("direction") == "SHORT")
    wait = 0
    qualified = total
    risk_approved = total
    executed = total
    closed = sum(1 for t in trades if t.get("exit_reason"))
    return pa.compute_funnel(total, buy, sell, wait, qualified, risk_approved, executed, closed)


@router.get("/api/performance/pnl")
async def performance_pnl():
    """Get P&L summary and equity curve."""
    trades = _get_trades()
    overview = pa.compute_overview(trades, [])
    equity = pa.compute_equity_curve(trades)
    return {"overview": overview, "equity_curve": equity}


@router.get("/api/performance/trades")
async def performance_trades(limit: int = Query(100)):
    """Get recent paper trades for analysis."""
    trades = _get_trades()
    return {"trades": trades[-limit:], "total": len(trades)}


@router.get("/api/performance/r-multiple")
async def performance_r_multiple():
    """Get R-multiple distribution."""
    trades = _get_trades()
    return pa.compute_r_multiple(trades)


@router.get("/api/performance/calibration")
async def performance_calibration():
    """Get AI confidence calibration analysis."""
    trades = _get_trades()
    return {"buckets": pa.compute_calibration(trades)}


@router.get("/api/performance/regimes")
async def performance_regimes():
    """Get performance by market regime."""
    trades = _get_trades()
    return {"regimes": pa.compute_regime_performance(trades)}


@router.get("/api/performance/timeframes")
async def performance_timeframes():
    """Get performance by timeframe."""
    trades = _get_trades()
    return {"timeframes": pa.compute_timeframe_performance(trades)}


@router.get("/api/performance/symbols")
async def performance_symbols():
    """Get performance by symbol."""
    trades = _get_trades()
    return {"symbols": pa.compute_symbol_performance(trades)}


@router.get("/api/performance/directions")
async def performance_directions():
    """Get LONG vs SHORT performance comparison."""
    trades = _get_trades()
    return {"directions": pa.compute_direction_performance(trades)}


@router.get("/api/performance/blocked")
async def performance_blocked():
    """Get blocked trade analysis."""
    blocked = _get_blocked()
    return pa.compute_blocked_analysis(blocked)


@router.get("/api/performance/equity-curve")
async def performance_equity_curve():
    """Get equity curve and drawdown."""
    trades = _get_trades()
    return pa.compute_equity_curve(trades)
