"""
MarketMind AI — Live Trading Control Center API

Provides consolidated snapshots of all live trading state:
- Account summary (equity, margin, P&L)
- Open positions with real-time P&L
- Open orders with lifecycle status
- Active trades
- Broker reconciliation status
- Emergency control state
- P&L history
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from trading.trade_lifecycle import get_lifecycle
from trading.pnl_engine import get_pnl_engine, PnLEngine

router = APIRouter(tags=["live"])

_pnl_engine: PnLEngine | None = None


def set_pnl_engine(engine: PnLEngine):
    global _pnl_engine
    _pnl_engine = engine


def _get_pnl():
    if _pnl_engine is not None:
        return _pnl_engine
    return get_pnl_engine()


# In-memory P&L cache
_pnl_cache: dict[str, Any] = {
    "day_pnl": 0.0,
    "realized_pnl": 0.0,
    "unrealized_pnl": 0.0,
    "total_pnl": 0.0,
    "last_updated": None,
}


def update_pnl(realized: float = 0, unrealized: float = 0):
    """Update the P&L cache from trade lifecycle events."""
    _pnl_cache["realized_pnl"] += realized
    _pnl_cache["unrealized_pnl"] = unrealized
    _pnl_cache["total_pnl"] = _pnl_cache["realized_pnl"] + _pnl_cache["unrealized_pnl"]
    _pnl_cache["day_pnl"] = _pnl_cache["total_pnl"]
    _pnl_cache["last_updated"] = datetime.now(timezone.utc).isoformat()


# ── Account ──


@router.get("/api/live/account")
async def live_account():
    """Get account summary (equity, margin, P&L) from P&L engine."""
    pnl = _get_pnl().get_portfolio_pnl()
    lifecycle = get_lifecycle()
    positions = lifecycle.get_open_positions()
    return {
        "total_equity": round(pnl.total_equity, 2),
        "available_margin": round(pnl.available_margin, 2),
        "used_margin": round(pnl.used_margin, 2),
        "exposure": round(pnl.total_exposure, 2),
        "day_pnl": round(pnl.day_pnl, 2),
        "unrealized_pnl": round(pnl.total_unrealized, 2),
        "realized_pnl": round(pnl.total_realized, 2),
        "total_pnl": round(pnl.total_pnl, 2),
        "margin_utilization_pct": round(pnl.margin_utilization_pct, 2),
        "open_positions": len(positions),
        "last_updated": pnl.last_updated,
    }


# ── Positions ──


@router.get("/api/live/positions")
async def live_positions():
    """Get all open positions with real-time P&L."""
    lifecycle = get_lifecycle()
    positions = lifecycle.get_open_positions()
    return {
        "positions": [
            {
                "symbol": p.symbol,
                "direction": p.direction,
                "quantity": p.quantity,
                "entry_price": p.entry_price,
                "current_price": p.entry_price,
                "unrealized_pnl": p.pnl,
                "pnl_percent": p.pnl_percent,
                "stop_loss": p.stop_loss,
                "target": p.target,
                "risk_reward": p.risk_reward,
                "trade_id": p.id,
                "status": p.status,
                "opened_at": p.opened_at,
            }
            for p in positions
        ],
        "total": len(positions),
    }


# ── Orders ──


@router.get("/api/live/orders")
async def live_orders():
    """Get all open orders with lifecycle status."""
    lifecycle = get_lifecycle()
    orders = lifecycle.get_all_orders()
    return {
        "orders": [o.to_dict() for o in orders if o.status not in ("filled", "closed", "cancelled", "rejected")],
        "total_history": len(orders),
    }


# ── Trades ──


@router.get("/api/live/trades")
async def live_trades():
    """Get all active trades."""
    lifecycle = get_lifecycle()
    trades = lifecycle.get_all_trades()
    return {
        "trades": [t.to_dict() for t in trades],
        "open_count": len([t for t in trades if t.status == "open"]),
        "total": len(trades),
    }


@router.get("/api/live/trades/{trade_id}")
async def live_trade_detail(trade_id: str):
    """Get detailed information for a specific trade."""
    lifecycle = get_lifecycle()
    trade = lifecycle.get_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    result = trade.to_dict()
    result["events"] = lifecycle.get_trade_events(trade_id)
    return result


# ── P&L ──


@router.get("/api/live/pnl")
async def live_pnl():
    """Get current P&L snapshot from P&L engine."""
    return _get_pnl().get_portfolio_pnl().to_dict()


# ── Status ──


@router.get("/api/live/status")
async def live_status():
    """Get comprehensive live trading status."""
    lifecycle = get_lifecycle()
    trades = lifecycle.get_all_trades()
    orders = lifecycle.get_all_orders()
    positions = lifecycle.get_open_positions()

    stuck_orders = [
        o.to_dict() for o in orders
        if o.status in ("submitting", "acknowledged") and o.created_at
    ]
    stale_trades = [
        t.to_dict() for t in trades
        if t.status == "open" and t.opened_at
    ]

    return {
        "broker": "zerodha",
        "open_orders": len([o for o in orders if o.status not in ("filled", "closed", "cancelled", "rejected")]),
        "open_positions": len(positions),
        "active_trades": len([t for t in trades if t.status == "open"]),
        "stuck_orders": stuck_orders,
        "stale_trades": stale_trades,
        "reconciliation_status": "unknown",
        "pnl": dict(_pnl_cache),
        "account": await live_account(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Reconciliation ──


@router.get("/api/live/reconciliation")
async def live_reconciliation():
    """Get broker reconciliation status."""
    lifecycle = get_lifecycle()
    return lifecycle.reconcile_with_broker([], [])


# ── Events ──


@router.get("/api/live/events")
async def live_events(limit: int = 100):
    """Get recent live trading events."""
    lifecycle = get_lifecycle()
    trades = lifecycle.get_all_trades()
    events = []
    for t in trades[:20]:
        events.append({
            "type": "trade.created",
            "trade_id": t.id,
            "symbol": t.symbol,
            "timestamp": t.created_at,
        })
        if t.opened_at:
            events.append({
                "type": "trade.opened",
                "trade_id": t.id,
                "symbol": t.symbol,
                "timestamp": t.opened_at,
            })
        if t.closed_at:
            events.append({
                "type": "trade.closed",
                "trade_id": t.id,
                "symbol": t.symbol,
                "pnl": t.pnl,
                "timestamp": t.closed_at,
            })
    return {"events": sorted(events, key=lambda e: e.get("timestamp", ""), reverse=True)[:limit]}


# ── Health ──


@router.get("/api/live/health")
async def live_health():
    """Get live trading health check."""
    lifecycle = get_lifecycle()
    trades = lifecycle.get_all_trades()
    stuck = [o for o in lifecycle.get_all_orders() if o.status in ("submitting", "acknowledged")]
    return {
        "status": "degraded" if stuck else "healthy",
        "open_positions": len([t for t in trades if t.status == "open"]),
        "pending_trades": len([t for t in trades if t.status not in ("open", "closed")]),
        "stuck_orders": len(stuck),
        "issues": ["Stuck orders detected"] if stuck else [],
    }
