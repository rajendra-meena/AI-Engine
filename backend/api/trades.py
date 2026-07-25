"""
MarketMind AI — Trade Lifecycle API Routes

Endpoints for the production trade lifecycle:
- Trades (list, detail, events, exit)
- Orders (list, detail)
- Positions (list)
- Reconciliation
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from trading.trade_lifecycle import TradeLifecycleManager

router = APIRouter(tags=["trades"])

_lifecycle: TradeLifecycleManager | None = None


def set_trade_lifecycle(lc: TradeLifecycleManager):
    global _lifecycle
    _lifecycle = lc


def _get() -> TradeLifecycleManager:
    if _lifecycle is not None:
        return _lifecycle
    return _get()


@router.get("/api/trades")
async def list_trades(status: str | None = Query(None)):
    """Get all trades, optionally filtered by status."""
    lifecycle = _get()
    trades = lifecycle.get_all_trades(status)
    return {"trades": [t.to_dict() for t in trades]}


@router.get("/api/trades/{trade_id}")
async def get_trade(trade_id: str):
    """Get a specific trade by ID."""
    lifecycle = _get()
    trade = lifecycle.get_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade.to_dict()


@router.get("/api/trades/{trade_id}/events")
async def get_trade_events(trade_id: str):
    """Get events for a specific trade."""
    lifecycle = _get()
    trade = lifecycle.get_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    events = lifecycle.get_trade_events(trade_id)
    return {"events": events}


@router.post("/api/trades/{trade_id}/exit")
async def exit_trade(trade_id: str, reason: str = Query("manual")):
    """Submit an exit order for an open trade."""
    lifecycle = _get()
    trade = lifecycle.get_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status != "open":
        raise HTTPException(status_code=400, detail=f"Trade is not open (status: {trade.status})")
    exit_order = lifecycle.submit_exit_order(trade_id, reason)
    if not exit_order:
        raise HTTPException(status_code=500, detail="Failed to submit exit order")
    return {"success": True, "order": exit_order.to_dict()}


@router.post("/api/trades/{trade_id}/close")
async def close_trade(trade_id: str, exit_price: float | None = Query(None)):
    """Close a trade (after exit fills)."""
    lifecycle = _get()
    lifecycle.close_trade(trade_id, exit_price)
    trade = lifecycle.get_trade(trade_id)
    return {"success": True, "trade": trade.to_dict() if trade else None}


@router.get("/api/orders")
async def list_orders(status: str | None = Query(None)):
    """Get all orders, optionally filtered by status."""
    lifecycle = _get()
    return {"orders": [o.to_dict() for o in lifecycle.get_all_orders(status)]}


@router.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    """Get a specific order by internal ID or broker order ID."""
    lifecycle = _get()
    order = lifecycle.get_order(order_id) or lifecycle.get_order_by_broker_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.to_dict()


@router.get("/api/positions")
async def list_positions():
    """Get all open positions."""
    lifecycle = _get()
    positions = lifecycle.get_open_positions()
    return {"positions": [p.to_dict() for p in positions]}


@router.post("/api/reconciliation/run")
async def run_reconciliation(orders: list[dict[str, Any]] | None = None, positions: list[dict[str, Any]] | None = None):
    """Run broker reconciliation with provided broker data."""
    lifecycle = _get()
    result = lifecycle.reconcile_with_broker(orders or [], positions or [])
    return result


@router.get("/api/reconciliation/status")
async def reconciliation_status():
    """Get current reconciliation status."""
    lifecycle = _get()
    return {
        "trades": len(lifecycle._trades),
        "orders": len(lifecycle._orders),
        "open_positions": len(lifecycle._open_positions),
        "warnings": [],
    }
