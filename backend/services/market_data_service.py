"""
MarketMind AI — Market Data Service

THE single entry point for all market data in the application.

Architecture:
    API Route
        ↓
    MarketDataService  ← ONLY entry point. All market data requests go through this.
        ↓
    ProviderFactory
        ↓
    YahooProvider (or future broker provider)

Responsibilities:
    - Validate inputs (symbol, interval, dates)
    - Select and retrieve the correct provider
    - Retry on transient failures
    - Convert provider exceptions to service-level exceptions
    - Normalize all responses to a standard format
    - Report provider health and status
    - Log all requests with timing

No module outside this service should call ProviderFactory or any provider directly.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone, timedelta
from typing import Any

from data.provider_factory import ProviderFactory
from data.base_provider import BaseProvider
from data.provider_types import (
    ProviderHealth,
    DailyOHLC,
    IntradayCandle,
    DailyReferenceLevels,
)
from data.exceptions import (
    ProviderError,
    InvalidSymbol,
    InvalidInterval,
    ProviderUnavailable,
)
from cache.csv_cache import (
    load_daily_csv,
    write_full_daily_csv,
    load_intraday_csv,
    write_full_intraday_csv,
)
from cache.memory_cache import MemoryCache
from cache.cache_keys import (
    intraday_key,
    daily_key,
    reference_key,
    provider_status_key,
)
from core.constants import (
    DAILY_LOOKBACK_DEFAULT_DAYS,
    DAILY_OVERLAP_DAYS,
    CACHE_FLUSH_BUFFER_SEC,
    FAST_INTERVALS,
    INTRADAY_MAX_DAYS_FAST,
    INTRADAY_MAX_DAYS_DEFAULT,
    MEMORY_CACHE_TTL_INTRADAY,
    MEMORY_CACHE_TTL_DAILY,
    MEMORY_CACHE_TTL_REFERENCE,
    MEMORY_CACHE_TTL_PROVIDER_STATUS,
)
from core.intervals import interval_to_minutes, is_valid_interval
from core.symbols import is_valid_symbol
from utils.logger import log_info, log_warn, log_error


class MarketDataService:
    """
    Centralized service for all market data operations.

    Instantiate once at application startup and inject into routes.
    The service manages provider selection, caching, retries, and normalization.

    Usage:
        service = MarketDataService()
        result = await service.get_intraday("NIFTY 50", "15m", 3)
    """

    def __init__(self, max_retries: int = 2):
        self._factory = ProviderFactory()
        self._provider: BaseProvider | None = None
        self._max_retries = max_retries
        self._cache = MemoryCache()

    # ── Provider management ──

    async def _get_provider(self) -> BaseProvider:
        """Get or create the active provider instance."""
        if self._provider is None:
            self._provider = self._factory.get_default_provider()
            await self._provider.connect()
            log_info(
                "MarketDataService: provider initialized",
                name=self._provider.capabilities().provider_name,
            )
        return self._provider

    def set_provider(self, name: str):
        """
        Override the active provider by name.
        Useful for switching the data source per-context (e.g. Auto Trade
        must use Zerodha Kite exclusively).
        """
        provider = self._factory.get_provider(name)
        self._provider = provider
        log_info("MarketDataService: provider set", name=name)

    def get_auto_trade_provider(self) -> BaseProvider:
        """
        Get the Zerodha Kite provider for Auto Trade.
        This is the ONLY provider used by the Auto Trade pipeline.
        Yahoo Finance is never used as an Auto Trade fallback.
        """
        return self._factory.get_auto_trade_provider()

    async def provider_status(self) -> dict[str, Any]:
        """Return the current provider's health and capabilities (memory cached)."""
        cache_key = provider_status_key()
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        provider = await self._get_provider()
        health = await provider.health()
        caps = provider.capabilities()
        result = {
            "provider": caps.provider_name,
            "type": caps.provider_type.value,
            "status": health.status.value,
            "last_success": (
                health.last_success.isoformat() if health.last_success else None
            ),
            "error_message": health.error_message,
            "supported_symbols": caps.symbols,
            "supported_intervals": caps.intervals,
        }
        await self._cache.set(
            cache_key, result, ttl_seconds=MEMORY_CACHE_TTL_PROVIDER_STATUS
        )
        return result

    async def health(self) -> ProviderHealth:
        """Quick health check. Returns the provider's health status."""
        provider = await self._get_provider()
        return await provider.health()

    # ── Validation ──

    async def validate_symbol(self, symbol: str) -> tuple[bool, str]:
        """Validate a symbol. Returns (is_valid, error_message)."""
        if not symbol or not isinstance(symbol, str):
            return False, "Symbol must be a non-empty string"
        if not is_valid_symbol(symbol):
            return False, f"Unknown symbol '{symbol}'"
        return True, ""

    async def validate_interval(self, interval: str) -> tuple[bool, str]:
        """Validate a chart interval. Returns (is_valid, error_message)."""
        if not interval or not isinstance(interval, str):
            return False, "Interval must be a non-empty string"
        if not is_valid_interval(interval):
            return False, f"Unsupported interval '{interval}'"
        return True, ""

    # ── Daily data ──

    async def get_daily(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """
        Fetch daily OHLC data for a symbol and optional date range.

        Returns:
            dict with {"symbol": str, "data": list} (same format as original API)
        """
        valid, err = await self.validate_symbol(symbol)
        if not valid:
            return {"symbol": symbol, "data": [], "error": err}

        end_date = end_date or date.today()
        start_date = start_date or (
            end_date - timedelta(days=DAILY_LOOKBACK_DEFAULT_DAYS)
        )

        # 1. Try memory cache first
        cache_key = daily_key(symbol)
        cached_result = await self._cache.get(cache_key)
        if cached_result is not None:
            # Filter cached full dataset to requested range
            filtered = [
                d
                for d in cached_result
                if start_date <= date.fromisoformat(d["Date"]) <= end_date
            ]
            return {"symbol": symbol, "data": filtered}

        provider = await self._get_provider()
        ticker = await provider.get_provider_symbol(symbol)
        today = date.today()

        # 2. Try CSV cache
        cached_records, cached_last_date_str, _ = load_daily_csv(ticker)
        cached_last_date = (
            date.fromisoformat(cached_last_date_str) if cached_last_date_str else None
        )

        # 3. Check if CSV cache is fresh
        need_fetch = self._daily_cache_needs_refresh(
            cached_records, cached_last_date, start_date, end_date, today
        )

        if need_fetch:
            cached_records = await self._refresh_daily_cache(
                provider,
                symbol,
                ticker,
                cached_records,
                cached_last_date,
                start_date,
                end_date,
            )

        # 4. Store full dataset in memory cache
        await self._cache.set(
            cache_key, cached_records, ttl_seconds=MEMORY_CACHE_TTL_DAILY
        )

        # 5. Filter to requested range
        filtered = [
            d
            for d in cached_records
            if start_date <= date.fromisoformat(d["Date"]) <= end_date
        ]

        return {"symbol": symbol, "data": filtered}

    # ── Intraday data ──

    async def get_intraday(
        self,
        symbol: str,
        interval: str = "15m",
        days: int = 3,
    ) -> dict[str, Any]:
        """
        Fetch intraday candle data.

        Returns:
            dict with {"symbol", "candles", "dailyRefs", "cached", "cache_size"}
        """
        valid, err = await self.validate_symbol(symbol)
        if not valid:
            return {"symbol": symbol, "candles": [], "error": err}

        valid_i, err_i = await self.validate_interval(interval)
        if not valid_i:
            return {"symbol": symbol, "candles": [], "error": err_i}

        # 1. Try memory cache first
        cache_key = intraday_key(symbol, interval)
        cached_result = await self._cache.get(cache_key)
        if cached_result is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            result = [
                c for c in cached_result if datetime.fromisoformat(c["time"]) >= cutoff
            ]
            deduped = self._deduplicate_candles(result)

            # Reference levels are cached separately
            refs = await self._get_reference_levels_cached(symbol)

            return {
                "symbol": symbol,
                "candles": deduped,
                "dailyRefs": refs,
                "cached": True,
                "cache_size": len(deduped),
            }

        provider = await self._get_provider()
        ticker = await provider.get_provider_symbol(symbol)

        # 2. Load CSV cache
        cached_candles, latest_cached_time = load_intraday_csv(ticker, interval)

        # 3. Check if CSV cache needs refresh
        now_utc = datetime.now(timezone.utc)
        need_fetch = self._intraday_cache_needs_refresh(
            latest_cached_time, interval, now_utc
        )

        if need_fetch:
            cached_candles = await self._refresh_intraday_cache(
                provider, symbol, ticker, interval, cached_candles, days
            )

        # 4. Store full dataset in memory cache
        await self._cache.set(
            cache_key, cached_candles, ttl_seconds=MEMORY_CACHE_TTL_INTRADAY
        )

        # 5. Trim to requested days
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = [
            c for c in cached_candles if datetime.fromisoformat(c["time"]) >= cutoff
        ]
        deduped = self._deduplicate_candles(result)

        # 6. Fetch daily reference levels (cached)
        refs = await self._get_reference_levels_cached(symbol)

        return {
            "symbol": symbol,
            "candles": deduped,
            "dailyRefs": refs,
            "cached": not need_fetch,
            "cache_size": len(deduped),
        }

    # ── Reference levels ──

    async def get_reference_levels(self, symbol: str) -> dict[str, Any] | None:
        """Fetch daily reference levels for a symbol (memory cached)."""
        return await self._get_reference_levels_cached(symbol)

    # ── Cache status ──

    async def get_cache_status(self, symbol: str) -> dict[str, Any]:
        """Return CSV cache metadata (last_updated, total_days)."""
        provider = await self._get_provider()
        ticker = await provider.get_provider_symbol(symbol)
        records, last_date, total = load_daily_csv(ticker)
        return {
            "symbol": symbol,
            "last_updated": last_date or "never",
            "total_days": total,
        }

    async def get_memory_cache_stats(self) -> dict[str, Any]:
        """Return in-memory cache performance statistics."""
        return self._cache.get_stats()

    # ── Cache helpers ──

    def _daily_cache_needs_refresh(
        self, cached_records, cached_last_date, start_date, end_date, today
    ):
        if cached_last_date is None or cached_last_date < end_date:
            return True
        fetch_start_needed = start_date - timedelta(days=DAILY_LOOKBACK_DEFAULT_DAYS)
        earliest_cached = (
            date.fromisoformat(cached_records[0]["Date"]) if cached_records else today
        )
        if earliest_cached > fetch_start_needed:
            return True
        return False

    def _intraday_cache_needs_refresh(self, latest_cached_time, interval, now_utc):
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

    async def _refresh_daily_cache(
        self,
        provider,
        symbol,
        ticker,
        cached_records,
        cached_last_date,
        start_date,
        end_date,
    ):
        """Fetch missing daily data via provider and merge with CSV cache."""
        if cached_last_date and cached_last_date < end_date:
            fetch_start = cached_last_date - timedelta(days=DAILY_OVERLAP_DAYS)
        else:
            fetch_start = start_date - timedelta(days=DAILY_LOOKBACK_DEFAULT_DAYS)

        log_info(
            "Fetching daily data",
            symbol=symbol,
            start=str(fetch_start),
            end=str(end_date),
        )

        try:
            ohlc_list = await self._call_with_retry(
                provider.fetch_daily, symbol, fetch_start, end_date
            )
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

    async def _refresh_intraday_cache(
        self, provider, symbol, ticker, interval, cached_candles, days
    ):
        """Fetch missing intraday data via provider and merge with CSV cache."""
        log_info("Fetching intraday data", symbol=symbol, interval=interval, days=days)

        try:
            candles = await self._call_with_retry(
                provider.fetch_intraday, symbol, interval, days
            )
        except ProviderError as e:
            log_warn(
                "Provider fetch_intraday failed",
                symbol=symbol,
                interval=interval,
                error=str(e),
            )
            return cached_candles

        new_records = [c.to_dict() for c in candles]
        existing_times = {c["time"] for c in cached_candles}
        fresh = [r for r in new_records if r["time"] not in existing_times]

        if fresh:
            cached_candles.extend(fresh)
            cached_candles.sort(key=lambda c: c["time"])
            write_full_intraday_csv(ticker, interval, cached_candles)

        return cached_candles

    async def _fetch_daily_reference_levels(self, provider, symbol):
        try:
            return await provider.fetch_daily_reference_levels(symbol)
        except Exception:
            return None

    async def _get_reference_levels_cached(self, symbol: str) -> dict | None:
        """Fetch reference levels with memory caching."""
        ref_key = reference_key(symbol)
        cached = await self._cache.get(ref_key)
        if cached is not None:
            return cached

        provider = await self._get_provider()
        refs = await self._fetch_daily_reference_levels(provider, symbol)
        ref_dict = refs.to_dict() if refs else None
        if ref_dict:
            await self._cache.set(
                ref_key, ref_dict, ttl_seconds=MEMORY_CACHE_TTL_REFERENCE
            )
        return ref_dict

    # ── Retry logic ──

    async def _call_with_retry(self, fn, *args, **kwargs):
        """
        Call a provider method with exponential backoff retry.

        Retries on transient failures (timeout, unavailable).
        Does NOT retry on InvalidSymbol or InvalidInterval.
        """
        last_exc = None
        for attempt in range(1, self._max_retries + 2):
            try:
                return await fn(*args, **kwargs)
            except (InvalidSymbol, InvalidInterval):
                raise  # Don't retry these — they're permanent
            except ProviderError as e:
                last_exc = e
                if attempt <= self._max_retries:
                    wait = 0.5 * (2 ** (attempt - 1))  # 0.5s, 1s, 2s...
                    log_warn(
                        "Provider call failed, retrying",
                        attempt=attempt,
                        max_retries=self._max_retries,
                        wait_sec=wait,
                        error=str(e),
                    )
                    await asyncio.sleep(wait)
                else:
                    log_error("Provider call failed, exhausted retries", error=str(e))
        raise last_exc  # type: ignore[misc]

    # ── Backtest data methods (raw date-range queries, no caching) ──

    async def get_intraday_range(
        self,
        symbol: str,
        start_dt: datetime,
        end_dt: datetime,
        interval: str = "15m",
    ) -> list[dict]:
        """
        Fetch raw intraday candles for a date range (backtesting use).
        Returns list of dicts with Datetime/Open/High/Low/Close/Volume keys.
        """
        provider = await self._get_provider()
        return await provider.fetch_intraday_range(symbol, start_dt, end_dt, interval)

    async def get_daily_range(
        self,
        symbol: str,
        start_dt: datetime,
        end_dt: datetime,
    ) -> list[dict]:
        """
        Fetch raw daily OHLC data for a date range (backtesting use).
        Returns list of dicts with Date/Open/High/Low/Close/Volume keys.
        """
        provider = await self._get_provider()
        return await provider.fetch_daily_range(symbol, start_dt, end_dt)

    # ── Helpers ──

    def _deduplicate_candles(self, candles: list) -> list:
        """Remove candles with duplicate timestamps, preserving order."""
        seen = set()
        deduped = []
        for c in candles:
            if c["time"] not in seen:
                seen.add(c["time"])
                deduped.append(c)
        return deduped
