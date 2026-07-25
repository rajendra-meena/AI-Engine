"""Paper Trading API — controlled paper execution pipeline."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from execution.paper_broker import get_paper_broker

router = APIRouter(tags=["paper"])


@router.get("/api/paper/status")
async def paper_status():
    """Get paper trading engine status."""
    broker = get_paper_broker()
    return {
        "running": broker.is_running,
        "paused": broker.is_paused,
        "account": broker.get_account().to_dict(),
        "open_positions": len(broker.get_positions()),
    }


@router.get("/api/paper/account")
async def paper_account():
    """Get paper account summary."""
    return get_paper_broker().get_account().to_dict()


@router.get("/api/paper/positions")
async def paper_positions():
    """Get active paper positions."""
    positions = get_paper_broker().get_positions()
    return {"positions": [p.to_dict() for p in positions], "total": len(positions)}


@router.get("/api/paper/orders")
async def paper_orders():
    """Get paper orders."""
    return {"orders": get_paper_broker().get_orders()}


@router.get("/api/paper/trades")
async def paper_trades():
    """Get paper trade history."""
    return {"trades": get_paper_broker().get_trades()}


@router.get("/api/paper/pnl")
async def paper_pnl():
    """Get paper P&L summary."""
    account = get_paper_broker().get_account()
    return {
        "total_pnl": account.total_pnl,
        "realized_pnl": account.total_realized_pnl,
        "unrealized_pnl": account.total_unrealized_pnl,
        "return_pct": account.to_dict()["return_pct"],
    }


@router.get("/api/paper/events")
async def paper_events():
    """Get recent paper trading events."""
    return {"events": get_paper_broker().get_events()}


@router.post("/api/paper/start")
async def paper_start():
    """Start paper trading engine."""
    get_paper_broker().start()
    return {"success": True, "status": "running"}


@router.post("/api/paper/pause")
async def paper_pause():
    """Pause paper trading (stops new entries, freezes monitoring)."""
    get_paper_broker().pause()
    return {"success": True, "status": "paused"}


@router.post("/api/paper/resume")
async def paper_resume():
    """Resume paper trading."""
    get_paper_broker().resume()
    return {"success": True, "status": "running"}


@router.post("/api/paper/stop")
async def paper_stop():
    """Stop paper trading engine."""
    get_paper_broker().stop()
    return {"success": True, "status": "stopped"}


@router.post("/api/paper/reset")
async def paper_reset():
    """Reset paper account. Does NOT affect production data."""
    get_paper_broker().reset()
    return {"success": True, "message": "Paper account reset"}


@router.post("/api/paper/close-position/{trade_id}")
async def paper_close_position(trade_id: str):
    """Manually close a paper position."""
    broker = get_paper_broker()
    success = broker.close_position(trade_id)
    if not success:
        raise HTTPException(status_code=404, detail="Position not found")
    return {"success": True, "message": "Position closed"}
