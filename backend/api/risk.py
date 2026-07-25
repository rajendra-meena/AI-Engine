"""
MarketMind AI — Risk Firewall API Routes

Endpoints for the Institutional Risk Firewall:
- Status and dashboard
- Trade validation (pre-execution)
- Exposure and drawdown
- Emergency controls
- Risk settings
- Audit logs
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from risk.risk_engine import RiskEngine, TradeIntent
from risk.risk_logger import RiskLogger
from risk.position_sizing import PositionSizer

router = APIRouter(tags=["risk"])

_engine: RiskEngine | None = None
_position_sizer = PositionSizer()


def set_risk_engine(engine: RiskEngine):
    global _engine
    _engine = engine


def _get() -> RiskEngine:
    assert _engine is not None, "RiskEngine not initialized"
    return _engine


@router.get("/api/risk/status")
async def risk_status():
    """Get comprehensive risk firewall status."""
    return _get().get_status()


@router.get("/api/risk/dashboard")
async def risk_dashboard():
    """Get risk dashboard data with all metrics."""
    engine = _get()
    return {
        "status": engine.get_status(),
        "exposure": engine.exposure,
        "drawdown": engine.drawdown,
        "validation_stats": RiskLogger.get_validation_stats(),
    }


@router.post("/api/risk/validate")
async def risk_validate(intent: dict[str, Any]):
    """
    Validate a trade intent against all risk rules.

    This MUST be called before any broker order placement.
    Returns validation summary with execution_permitted flag.
    """
    try:
        trade = TradeIntent(
            symbol=intent.get("symbol", ""),
            side=intent.get("side", "BUY"),
            quantity=intent.get("quantity", 0),
            price=intent.get("price"),
            order_type=intent.get("order_type", "MARKET"),
            product=intent.get("product", "MIS"),
            exchange=intent.get("exchange", "NSE"),
            strategy=intent.get("strategy", "manual"),
            ai_score=intent.get("ai_score"),
            ai_confidence=intent.get("ai_confidence"),
            ai_decision=intent.get("ai_decision"),
            stop_loss=intent.get("stop_loss"),
            take_profit=intent.get("take_profit"),
            user_id=intent.get("user_id", ""),
            tag=intent.get("tag", ""),
        )
        result = _get().validate(trade)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/risk/exposure")
async def risk_exposure():
    """Get current portfolio exposure metrics."""
    return _get().exposure


@router.get("/api/risk/settings")
async def risk_settings():
    """Get current risk configuration."""
    engine = _get()
    cfg = engine.config
    return {
        "max_daily_loss": cfg.max_daily_loss,
        "max_weekly_loss": cfg.max_weekly_loss,
        "max_monthly_loss": cfg.max_monthly_loss,
        "max_drawdown_percent": cfg.max_drawdown_percent,
        "max_daily_trades": cfg.max_daily_trades,
        "max_concurrent_positions": cfg.max_concurrent_positions,
        "max_open_orders": cfg.max_open_orders,
        "max_exposure_percent": cfg.max_exposure_percent,
        "max_risk_percent": cfg.max_risk_percent,
        "min_ai_score": cfg.min_ai_score,
        "min_ai_confidence": cfg.min_ai_confidence,
        "min_reward_risk": cfg.min_reward_risk,
        "trade_cooldown_seconds": cfg.trade_cooldown_seconds,
        "trading_halt": cfg.trading_halt,
        "broker_disabled": cfg.broker_disabled,
        "ai_disabled": cfg.ai_disabled,
    }


@router.post("/api/risk/settings")
async def risk_update_settings(settings: dict[str, Any]):
    """Update risk configuration."""
    engine = _get()
    engine.update_config(settings)
    return {"success": True}


@router.get("/api/risk/logs")
async def risk_logs(limit: int = 100):
    """Get recent risk validation logs."""
    return {"logs": RiskLogger.get_recent_logs(limit)}


@router.get("/api/risk/events")
async def risk_events(limit: int = 50):
    """Get recent risk events."""
    return {"events": RiskLogger.get_recent_events(limit)}


@router.post("/api/risk/emergency")
async def risk_emergency(action: str = "pause_trading", reason: str = ""):
    """
    Execute an emergency control action.

    Supported actions:
    - pause_trading
    - disable_ai
    - disable_broker
    - emergency_exit
    - close_all
    - cancel_orders
    - reset
    """
    engine = _get()
    action_map = {
        "pause_trading": engine.pause_trading,
        "disable_ai": engine.disable_ai,
        "disable_broker": engine.disable_broker,
        "emergency_exit": engine.emergency_exit,
        "reset": engine.reset_emergency,
    }
    handler = action_map.get(action)
    if handler is None:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
    handler()
    RiskLogger.log_emergency(action, "user", reason)
    return {"success": True, "action": action}


@router.post("/api/risk/position-size")
async def risk_position_size(params: dict[str, Any]):
    """
    Calculate position size using various methods.

    Methods: fixed_quantity, fixed_amount, fixed_risk, atr_based, kelly, volatility_adjusted
    """
    method = params.get("method", "fixed_risk")
    capital = params.get("capital", 100000.0)
    price = params.get("price", 0.0)
    stop_loss = params.get("stop_loss")
    lot_size = params.get("lot_size", 1)
    risk_percent = params.get("risk_percent", 2.0)

    try:
        if method == "fixed_quantity":
            result = _position_sizer.fixed_quantity(
                params.get("quantity", 1), price, capital
            )
        elif method == "fixed_amount":
            result = _position_sizer.fixed_amount(
                params.get("amount", 10000), price, capital, lot_size
            )
        elif method == "fixed_risk":
            if not stop_loss:
                raise HTTPException(status_code=400, detail="stop_loss required for fixed_risk")
            result = _position_sizer.fixed_risk(
                capital, risk_percent, price, stop_loss, lot_size
            )
        elif method == "atr_based":
            atr = params.get("atr", 0)
            result = _position_sizer.atr_based(
                capital, price, atr, risk_percent,
                params.get("atr_multiplier", 2.0), lot_size,
            )
        elif method == "kelly":
            result = _position_sizer.kelly_criterion(
                params.get("win_rate", 0.5),
                params.get("avg_win", 0),
                params.get("avg_loss", 0),
                capital, price, lot_size,
                params.get("kelly_fraction", 0.25),
            )
        elif method == "volatility_adjusted":
            result = _position_sizer.volatility_adjusted(
                capital, price,
                params.get("volatility_pct", 20),
                risk_percent, lot_size,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown method: {method}")
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
