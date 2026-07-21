"""
MarketMind AI — Market Data Service

Orchestrates fetching, caching, and returning daily & intraday market data.
Communicates ONLY with the provider interface — never with yfinance directly.

Data flow:
    API Route → MarketService → Provider Interface → YahooProvider → yfinance
"""

import asyncio
from datetime import date, datetime, timezone, timedelta

from data.provider_factory import ProviderFactory
from data.base_provider import BaseProvider
from data.provider_types import DailyOHLC, IntradayCandle
from data.exceptions import ProviderError
from cache.csv_cache import (
    load_daily_csv,
    write_full_daily_csv,
    load_intraday_csv,
    write_full_intraday_csv,
)
from core.constants import (
    DAILY_LOOKBACK_DEFAULT_DAYS,
    DAILY_OVERLAP_DAYS,
    CACHE_FLUSH_BUFFER_SEC,
)
from core.intervals import interval_to_minutes
from utils.logger import log_info, log_warn


# ── Provider instance (lazily initialised) ──

_provider: BaseProvider | None = None


def _get_provider() -> BaseProvider:
    """Get or create the market data provider singleton."""
    global _provider
    if _provider is None:
        factory = ProviderFactory()
        _provider = factory.get_default_provider()
    return _provider


# ── Daily data ──


async def fetch_daily_data(symbol: str, start_date: date, end_date: date):
    """
    Fetch daily OHLC data for the given symbol and date range.

    Uses a CSV cache: if the cache covers the requested range, returns instantly.
    Only calls the provider for missing days.

    Returns:
        dict with {"symbol": str, "data": list}
    """
    provider = _get_provider()
    ticker = await provider.get_provider_symbol(symbol)
    today = date.today()

    # 1. Try disk cache
    cached_records, cached_last_date_str, _ = load_daily_csv(ticker)
    cached_last_date = date.fromisoformat(cached_last_date_str) if cached_last_date_str else None

    need_fetch = _check_daily_cache_needs_refresh(
        cached_records, cached_last_date, start_date, end_date, today
    )

    if need_fetch:
        cached_records = await _refresh_daily_cache(provider, symbol, ticker, cached_records, cached_last_date, start_date, end_date)

    # Filter to requested range
    filtered = [
        d for d in cached_records
        if start_date <= date.fromisoformat(d["Date"]) <= end_date
    ]

    return {"symbol": symbol, "data": filtered}


def _check_daily_cache_needs_refresh(cached_records, cached_last_date, start_date, end_date, today):
    """Determine if the daily CSV cache needs updating."""
    if cached_last_date is None or cached_last_date < end_date:
        return True

    fetch_start_needed = start_date - timedelta(days=DAILY_LOOKBACK_DEFAULT_DAYS)
    earliest_cached = (
        date.fromisoformat(cached_records[0]["Date"]) if cached_records else today
    )
    if earliest_cached > fetch_start_needed:
        return True

    return False


async def _refresh_daily_cache(provider, symbol, ticker, cached_records, cached_last_date, start_date, end_date):
    """Fetch missing daily data via provider and merge with cache."""
    if cached_last_date and cached_last_date < end_date:
        fetch_start = cached_last_date - timedelta(days=DAILY_OVERLAP_DAYS)
    else:
        fetch_start = start_date - timedelta(days=DAILY_LOOKBACK_DEFAULT_DAYS)

    log_info("Fetching daily data", symbol=symbol, start=str(fetch_start), end=str(end_date))

    try:
        ohlc_list = await provider.fetch_daily(symbol, fetch_start, end_date)
    except ProviderError as e:
        log_warn("Provider fetch_daily failed", symbol=symbol, error=str(e))
        return cached_records or []

    new_records = [o.to_dict() for o in ohlc_list]

    if cached_records:
        existing_dates = {r["Date"] for r in cached_records}
        fresh = [r for r in new_records if r["Date"] not in existing_dates]
        merged = cached_records + fresh
        merged.sort(key=lambda r: r["Date"])
        write_full_daily_csv(ticker, merged)
        return merged
    else:
        write_full_daily_csv(ticker, new_records)
        return new_records


# ── Intraday data ──


async def fetch_intraday_data(symbol: str, interval: str, days: int):
    """
    Fetch intraday candle data for the given symbol, interval, and lookback days.

    Returns:
        dict with {"symbol", "candles", "dailyRefs", "cached", "cache_size"}
    """
    provider = _get_provider()
    ticker = await provider.get_provider_symbol(symbol)

    # 1. Load intraday cache
    cached_candles, latest_cached_time = load_intraday_csv(ticker, interval)

    # 2. Determine if we need to fetch from provider
    now_utc = datetime.now(timezone.utc)
    need_fetch = _check_intraday_cache_needs_refresh(latest_cached_time, interval, now_utc)

    if need_fetch:
        cached_candles = await _refresh_intraday_cache(provider, symbol, ticker, interval, cached_candles, days)

    # Trim to requested days
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = [c for c in cached_candles if datetime.fromisoformat(c["time"]) >= cutoff]

    # Deduplicate by time (safety)
    deduped = _deduplicate_candles(result)

    # Fetch daily reference levels
    daily_refs = await _fetch_daily_reference_levels(provider, symbol)

    daily_refs_dict = daily_refs.to_dict() if daily_refs else None

    return {
        "symbol": symbol,
        "candles": deduped,
        "dailyRefs": daily_refs_dict,
        "cached": not need_fetch,
        "cache_size": len(deduped),
    }


def _check_intraday_cache_needs_refresh(latest_cached_time, interval, now_utc):
    """Check if a new intraday candle should have closed since the last cache timestamp."""
    if not latest_cached_time:
        return True

    try:
        interval_mins = interval_to_minutes(interval)
        if interval_mins <= 0:
            return True

        latest_dt = datetime.fromisoformat(latest_cached_time)
        delta = timedelta(minutes=interval_mins)
        next_candle_time = latest_dt + delta

        if next_candle_time > now_utc - timedelta(seconds=CACHE_FLUSH_BUFFER_SEC):
            return False
    except Exception:
        return True

    return True


async def _refresh_intraday_cache(provider, symbol, ticker, interval, cached_candles, days):
    """Fetch missing intraday data via provider and merge with cache."""
    log_info("Fetching intraday data", symbol=symbol, interval=interval, days=days)

    try:
        candles = await provider.fetch_intraday(symbol, interval, days)
    except ProviderError as e:
        log_warn("Provider fetch_intraday failed", symbol=symbol, interval=interval, error=str(e))
        return cached_candles

    new_records = [c.to_dict() for c in candles]
    existing_times = {c["time"] for c in cached_candles}
    fresh = [r for r in new_records if r["time"] not in existing_times]

    if fresh:
        cached_candles.extend(fresh)
        cached_candles.sort(key=lambda c: c["time"])
        write_full_intraday_csv(ticker, interval, cached_candles)

    return cached_candles


async def _fetch_daily_reference_levels(provider, symbol):
    """Fetch daily reference levels via the provider."""
    try:
        return await provider.fetch_daily_reference_levels(symbol)
    except Exception:
        return None


async def get_cache_status(symbol: str):
    """Return cache metadata (last_updated, total_days) for a symbol."""
    provider = _get_provider()
    ticker = await provider.get_provider_symbol(symbol)
    records, last_date, total = load_daily_csv(ticker)
    return {
        "symbol": symbol,
        "last_updated": last_date or "never",
        "total_days": total,
    }


# ── Helpers ──


def _deduplicate_candles(candles: list) -> list:
    """Remove candles with duplicate timestamps, preserving order."""
    seen = set()
    deduped = []
    for c in candles:
        if c["time"] not in seen:
            seen.add(c["time"])
            deduped.append(c)
    return deduped
