"""
MarketMind AI — Zerodha Kite Connect API Routes

REST endpoints for all Zerodha integration:
- Authentication (login URL, session creation, status)
- Connection management (connect, disconnect, reconnect)
- Real-time WebSocket tick streaming management
- Instrument master lookup
- Order placement and management
- Positions, holdings, margins, funds
- Provider health and status
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from data.provider_factory import ProviderFactory
from data.base_provider import BaseProvider
from providers.zerodha.kite_provider import KiteProvider
from utils.logger import log_info, log_warn, log_error

router = APIRouter(tags=["zerodha"])

_factory: ProviderFactory | None = None


def set_provider_factory(factory: ProviderFactory):
    global _factory
    _factory = factory


def _get_factory() -> ProviderFactory:
    assert _factory is not None, "ProviderFactory not initialized"
    return _factory


def _get_kite() -> KiteProvider | None:
    """Get KiteProvider instance from factory, or None."""
    try:
        provider = _get_factory().get_provider("zerodha")
        if isinstance(provider, KiteProvider):
            return provider
        return None
    except Exception:
        return None


def _require_kite() -> KiteProvider:
    kite = _get_kite()
    if kite is None:
        raise HTTPException(status_code=503, detail="Kite provider not available")
    return kite


# ── Authentication ──


@router.get("/api/kite/login-url")
async def kite_login_url():
    """Get the Kite Connect login URL for OAuth flow."""
    try:
        kite = _require_kite()
        url = kite.get_login_url()
        return {"success": True, "login_url": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate login URL: {e}")


@router.post("/api/kite/session")
async def kite_create_session(request_token: str = Query(..., description="Request token from OAuth callback")):
    """Create a Kite session using the request token from login redirect."""
    try:
        kite = _require_kite()
        result = kite.create_session(request_token)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Session creation failed: {e}")


@router.post("/api/kite/logout")
async def kite_logout():
    """Logout from Kite and clear all tokens."""
    try:
        kite = _require_kite()
        kite.logout()
        return {"success": True, "message": "Logged out"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {e}")


@router.get("/api/kite/auth-status")
async def kite_auth_status():
    """Return current authentication status."""
    kite = _get_kite()
    if kite is None:
        return {
            "authenticated": False,
            "configured": False,
            "message": "Kite provider not configured",
        }
    auth = kite.auth.get_status()
    return {
        "authenticated": auth.get("authenticated", False),
        "configured": auth.get("has_api_key", False),
        "user_id": auth.get("user_id", ""),
        "user_name": auth.get("user_name", ""),
        "broker": auth.get("broker", "ZERODHA"),
        "exchange": auth.get("exchange", "NSE"),
        "last_auth_time": auth.get("last_auth_time"),
    }


# ── Connection management ──


@router.post("/api/kite/connect")
async def kite_connect():
    """Connect to Kite (authenticate + load instruments)."""
    try:
        kite = _require_kite()
        success = await kite.connect()
        if not success:
            raise HTTPException(status_code=401, detail="Connection failed. Authenticate first.")
        return {"success": True, "status": kite.get_status()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection failed: {e}")


@router.post("/api/kite/disconnect")
async def kite_disconnect():
    """Disconnect from Kite."""
    try:
        kite = _require_kite()
        await kite.disconnect()
        return {"success": True, "message": "Disconnected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Disconnect failed: {e}")


@router.post("/api/kite/reconnect")
async def kite_reconnect():
    """Reconnect to Kite."""
    try:
        kite = _require_kite()
        await kite.disconnect()
        success = await kite.connect()
        return {"success": success, "status": kite.get_status()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reconnect failed: {e}")


# ── WebSocket tick streaming ──


@router.post("/api/kite/ws/start")
async def kite_ws_start():
    """Start the Kite WebSocket tick stream."""
    try:
        kite = _require_kite()
        success = await kite.start_websocket()
        if not success:
            raise HTTPException(status_code=500, detail="WebSocket start failed")
        return {"success": True, "status": kite.ws_client.get_stats() if kite.ws_client else {}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"WebSocket start failed: {e}")


@router.post("/api/kite/ws/stop")
async def kite_ws_stop():
    """Stop the Kite WebSocket tick stream."""
    try:
        kite = _require_kite()
        kite.stop_websocket()
        return {"success": True, "message": "WebSocket stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"WebSocket stop failed: {e}")


@router.get("/api/kite/ws/status")
async def kite_ws_status():
    """Get WebSocket connection status."""
    kite = _get_kite()
    if kite is None or kite.ws_client is None:
        return {"connected": False, "ticks_received": 0}
    return kite.ws_client.get_health()


@router.post("/api/kite/ws/subscribe")
async def kite_ws_subscribe(symbols: list[str] = Query(..., description="List of internal symbol names")):
    """Subscribe to real-time ticks for given symbols."""
    try:
        kite = _require_kite()
        kite.subscribe_ticks(symbols)
        return {"success": True, "symbols": symbols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subscribe failed: {e}")


# ── Instrument master ──


@router.get("/api/kite/instruments/search")
async def kite_instruments_search(
    query: str = Query(..., description="Symbol search text"),
    exchange: str | None = Query(None, description="Exchange filter (NSE, BSE, NFO)"),
):
    """Search instruments by symbol."""
    try:
        kite = _require_kite()
        await kite.instruments.load()
        results = kite.instruments.search(query, exchange)
        return {"count": len(results), "results": results[:30]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.get("/api/kite/instruments/expiries")
async def kite_instruments_expiries(symbol: str = Query(..., description="Symbol name")):
    """Get available expiry dates for a symbol's options/futures."""
    try:
        kite = _require_kite()
        await kite.instruments.load()
        expiries = kite.instruments.get_expiries(symbol)
        return {"symbol": symbol, "expiries": expiries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/kite/instruments/status")
async def kite_instruments_status():
    """Get instrument master loading status."""
    kite = _get_kite()
    if kite is None:
        return {"loaded": False}
    return kite.instruments.get_stats()


# ── Market data ──


@router.get("/api/kite/quote")
async def kite_quote(symbol: str = Query(..., description="Internal symbol name")):
    """Get latest quote for a symbol."""
    try:
        kite = _require_kite()
        # Ensure connected
        if not kite.market_data.is_ready:
            await kite.connect()
        quote = await kite.market_data.fetch_quote(symbol)
        if quote is None:
            raise HTTPException(status_code=404, detail="No quote data")
        return quote
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/kite/ltp")
async def kite_ltp(symbol: str = Query(..., description="Internal symbol name")):
    """Get last traded price for a symbol."""
    try:
        kite = _require_kite()
        ltp = await kite.market_data.fetch_ltp(symbol)
        if ltp is None:
            raise HTTPException(status_code=404, detail="No LTP data")
        return {"symbol": symbol, "ltp": ltp}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Orders ──


@router.post("/api/kite/orders")
async def kite_place_order(order: dict[str, Any]):
    """
    Place an order.

    Required fields: tradingsymbol, exchange, transaction_type, quantity
    Optional: order_type (default MARKET), price, product, validity, variety,
              trigger_price, stoploss, squareoff, trailing_stoploss, tag
    """
    try:
        kite = _require_kite()
        if not kite.orders.is_ready:
            await kite.connect()
        result = kite.orders.place_order(
            tradingsymbol=order.get("tradingsymbol", ""),
            exchange=order.get("exchange", "NSE"),
            transaction_type=order.get("transaction_type", "BUY"),
            quantity=order.get("quantity", 1),
            order_type=order.get("order_type", "MARKET"),
            price=order.get("price", 0.0),
            product=order.get("product", "MIS"),
            validity=order.get("validity", "DAY"),
            variety=order.get("variety", "regular"),
            trigger_price=order.get("trigger_price"),
            stoploss=order.get("stoploss"),
            squareoff=order.get("squareoff"),
            trailing_stoploss=order.get("trailing_stoploss"),
            tag=order.get("tag", ""),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/kite/orders/{order_id}")
async def kite_modify_order(order_id: str, modifications: dict[str, Any]):
    """Modify an existing order."""
    try:
        kite = _require_kite()
        result = kite.orders.modify_order(
            order_id=order_id,
            price=modifications.get("price"),
            quantity=modifications.get("quantity"),
            order_type=modifications.get("order_type"),
            trigger_price=modifications.get("trigger_price"),
            variety=modifications.get("variety", "regular"),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/kite/orders/{order_id}")
async def kite_cancel_order(order_id: str, variety: str = Query("regular")):
    """Cancel an order."""
    try:
        kite = _require_kite()
        result = kite.orders.cancel_order(order_id, variety)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/kite/orders")
async def kite_get_orders():
    """Get all orders."""
    try:
        kite = _require_kite()
        orders = kite.orders.get_orders()
        return {"orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/kite/orders/{order_id}/history")
async def kite_order_history(order_id: str):
    """Get history for a specific order."""
    try:
        kite = _require_kite()
        history = kite.orders.get_order_history(order_id)
        return {"order_id": order_id, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Positions ──


@router.get("/api/kite/positions")
async def kite_get_positions():
    """Get current open positions."""
    try:
        kite = _require_kite()
        positions = kite.orders.get_positions()
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/kite/positions/exit")
async def kite_exit_position(
    tradingsymbol: str = Query(...), exchange: str = Query("NSE")
):
    """Exit an open position."""
    try:
        kite = _require_kite()
        result = kite.orders.exit_position(tradingsymbol, exchange)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Holdings ──


@router.get("/api/kite/holdings")
async def kite_get_holdings():
    """Get equity holdings."""
    try:
        kite = _require_kite()
        holdings = kite.orders.get_holdings()
        return {"holdings": holdings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Margins / Funds ──


@router.get("/api/kite/margins")
async def kite_get_margins():
    """Get available margins and funds."""
    try:
        kite = _require_kite()
        margins = kite.orders.get_margins()
        return margins
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Trades ──


@router.get("/api/kite/trades")
async def kite_get_trades():
    """Get executed trades."""
    try:
        kite = _require_kite()
        trades = kite.orders.get_trades()
        return {"trades": trades}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Provider status ──


@router.get("/api/kite/status")
async def kite_status():
    """Get comprehensive Kite provider status."""
    kite = _get_kite()
    if kite is None:
        return {
            "available": False,
            "configured": False,
            "authenticated": False,
        }
    return {
        "available": True,
        "configured": kite.auth.api_key is not None,
        "connected": kite._connected,
        **kite.get_status(),
    }


@router.get("/api/kite/health")
async def kite_health():
    """Get Kite provider health check."""
    try:
        kite = _require_kite()
        health = await kite.health()
        return health.to_dict() if hasattr(health, "to_dict") else {
            "status": health.status.value if hasattr(health.status, "value") else str(health.status),
            "provider_name": health.provider_name,
            "provider_type": health.provider_type.value if hasattr(health.provider_type, "value") else str(health.provider_type),
            "last_success": health.last_success.isoformat() if health.last_success else None,
            "error_message": health.error_message,
        }
    except Exception as e:
        return {
            "status": "unavailable",
            "error_message": str(e),
        }
