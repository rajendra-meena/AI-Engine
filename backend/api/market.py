"""
MarketMind AI — Market Data API Routes

Endpoints for fetching daily OHLC, intraday candles, and cache status.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Query

from services.market_service import fetch_daily_data, fetch_intraday_data, get_cache_status

router = APIRouter(tags=["market"])


@router.get("/api/data")
async def get_data(
    symbol: str = Query("NIFTY 50", description="Index display name"),
    start: str = Query(None, description="Start date YYYY-MM-DD"),
    end: str = Query(None, description="End date YYYY-MM-DD"),
):
    """Fetch historical index data with dual-layer caching."""
    today = date.today()
    end_date = date.fromisoformat(end) if end else today
    start_date = date.fromisoformat(start) if start else end_date - timedelta(days=365)

    try:
        result = await fetch_daily_data(symbol, start_date, end_date)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"symbol": symbol, "data": [], "error": str(e)}


@router.get("/api/intraday")
async def get_intraday(
    symbol: str = Query("NIFTY 50", description="Index display name"),
    interval: str = Query("15m", description="Intraday interval: 1m, 2m, 5m, 15m, 30m, 60m"),
    days: int = Query(3, description="Number of days of intraday data"),
):
    """Fetch intraday candles with disk caching."""
    try:
        result = await fetch_intraday_data(symbol, interval, days)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"symbol": symbol, "candles": [], "error": str(e)}


@router.get("/api/cache/status")
async def cache_status(
    symbol: str = Query("NIFTY 50", description="Index display name"),
):
    """Return cache metadata for a given symbol."""
    return await get_cache_status(symbol)
