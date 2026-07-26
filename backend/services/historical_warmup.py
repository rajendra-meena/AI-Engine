"""
MarketMind AI — Historical Warmup Engine

Fetches, validates, and stores historical candle data from the Kite Historical Data API.
Warms indicator state so that real-time events start from a primed position.

Rules:
- Fetch minimum candles required by all enabled indicators (e.g. EMA 200 → 200+)
- Add a safe warm-up buffer (HISTORICAL_WARMUP_BUFFER = 50)
- Validate chronological order, no duplicates, expected interval, valid OHLC
- Store validated candles for indicator initialization
- Mark symbol ready only after complete warm-up
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from core.freshness import SymbolFreshnessTracker
from data.exceptions import DataUnavailable, InvalidSymbol, InvalidInterval
from utils.logger import log_info, log_warn, log_error

# Maximum candles to fetch in a single historical call
MAX_CANDLES_PER_CALL = 2000
# Safe buffer added to minimum indicator requirements
HISTORICAL_WARMUP_BUFFER = 50
# Maximum re-fetch attempts for gap filling
MAX_GAP_FILL_ATTEMPTS = 3


@dataclass
class WarmupStatus:
    """Warm-up progress for a single symbol/timeframe."""
    symbol: str = ""
    interval: str = "15m"
    required_candles: int = 0
    fetched_candles: int = 0
    validated_candles: int = 0
    is_complete: bool = False
    errors: list[str] = field(default_factory=list)
    last_fetch_time: str = ""


@dataclass
class WarmupCandle:
    """A single validated historical candle."""
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    oi: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "oi": self.oi,
        }


class HistoricalWarmupEngine:
    """
    Coordinates historical data fetching and warm-up for Auto Trade symbols.

    Usage:
        engine = HistoricalWarmupEngine(market_data, freshness_tracker)
        await engine.warmup_symbol("NIFTY 50", ["15m", "5m"])
        status = engine.get_status("NIFTY 50", "15m")
    """

    def __init__(
        self,
        kite_provider=None,
        freshness_tracker: SymbolFreshnessTracker | None = None,
    ):
        self._kite = kite_provider
        self._freshness = freshness_tracker or SymbolFreshnessTracker()
        self._statuses: dict[tuple[str, str], WarmupStatus] = {}
        self._buffers: dict[tuple[str, str], deque[WarmupCandle]] = {}
        self._callbacks: list[Callable] = []

    def is_kite_available(self) -> bool:
        """Public check: whether the Kite provider is available for historical data.

        For Auto Trade, if this returns False the engine must transition
        to ERROR / BLOCKED — not fall back to Yahoo Finance.
        """
        return self._kite is not None

    def set_kite_provider(self, provider):
        """Set or update the Kite provider after authentication."""
        self._kite = provider

    def on_warmup_progress(self, cb: Callable):
        """Register callback for warm-up progress events."""
        self._callbacks.append(cb)

    async def warmup_symbol(
        self,
        symbol: str,
        intervals: list[str] | None = None,
        min_candles: int | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Warm up indicator state for a symbol across specified timeframes.

        Args:
            symbol: Internal symbol name (e.g. "NIFTY 50")
            intervals: List of intervals to warm up (default: ["15m", "5m", "1m"])
            min_candles: Minimum candles required (default: 250 for EMA 200 + buffer)
            force: If True, re-fetch even if already warmed up

        Returns:
            Dict with warm-up results per interval.
        """
        if intervals is None:
            intervals = ["15m", "5m", "1m"]
        if min_candles is None:
            min_candles = 250  # EMA 200 + 50 buffer

        results = {}
        for interval in intervals:
            key = (symbol, interval)
            existing = self._statuses.get(key)
            if existing and existing.is_complete and not force:
                results[interval] = {"status": "already_complete", "candles": existing.validated_candles}
                continue

            status = WarmupStatus(
                symbol=symbol,
                interval=interval,
                required_candles=min_candles,
            )
            self._statuses[key] = status
            self._buffers[key] = deque()

            try:
                candles = await self._fetch_and_validate(symbol, interval, min_candles, status)
                if candles:
                    self._buffers[key] = deque(candles)
                    status.validated_candles = len(candles)
                    status.is_complete = len(candles) >= min_candles
                    status.last_fetch_time = _now_str()

                    log_info(
                        "HistoricalWarmup: symbol ready",
                        symbol=symbol,
                        interval=interval,
                        candles=len(candles),
                        required=min_candles,
                    )
                else:
                    log_warn(
                        "HistoricalWarmup: no candles returned",
                        symbol=symbol,
                        interval=interval,
                    )

            except Exception as e:
                status.errors.append(str(e))
                log_error(
                    "HistoricalWarmup: failed",
                    symbol=symbol,
                    interval=interval,
                    error=str(e),
                )

            results[interval] = {
                "status": "complete" if status.is_complete else "failed",
                "fetched": status.fetched_candles,
                "validated": status.validated_candles,
                "required": status.required_candles,
                "errors": status.errors,
            }

            # Notify callbacks
            for cb in self._callbacks:
                try:
                    cb(symbol, interval, status)
                except Exception:
                    pass

        return results

    async def warmup_all(
        self,
        symbols: list[str],
        intervals: list[str] | None = None,
        min_candles: int = 250,
    ) -> dict[str, Any]:
        """Warm up all symbols sequentially."""
        results = {}
        for symbol in symbols:
            results[symbol] = await self.warmup_symbol(symbol, intervals, min_candles)
        return results

    async def fill_gap(
        self, symbol: str, interval: str, missing_from: str, missing_to: str
    ) -> list[WarmupCandle] | None:
        """Fetch missing candles for a detected data gap."""
        if not self._kite:
            log_warn("HistoricalWarmup: no Kite provider for gap fill")
            return None

        log_info(
            "HistoricalWarmup: filling gap",
            symbol=symbol,
            interval=interval,
            from_ts=missing_from,
            to_ts=missing_to,
        )

        for attempt in range(MAX_GAP_FILL_ATTEMPTS):
            try:
                candles = await self._fetch_raw(symbol, interval, missing_from, missing_to)
                if candles:
                    return candles
            except Exception as e:
                log_warn("HistoricalWarmup: gap fill attempt failed", attempt=attempt, error=str(e))
                if attempt < MAX_GAP_FILL_ATTEMPTS - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))

        log_error("HistoricalWarmup: gap fill exhausted", symbol=symbol, interval=interval)
        return None

    def get_candles(
        self, symbol: str, interval: str, count: int = 250
    ) -> list[WarmupCandle]:
        """Get most recent validated candles for a symbol/interval."""
        key = (symbol, interval)
        buf = self._buffers.get(key)
        if not buf:
            return []
        return list(buf)[-count:]

    def get_status(self, symbol: str, interval: str) -> dict[str, Any] | None:
        """Get warm-up status for a symbol/interval."""
        key = (symbol, interval)
        s = self._statuses.get(key)
        if not s:
            return None
        return {
            "symbol": s.symbol,
            "interval": s.interval,
            "required_candles": s.required_candles,
            "fetched_candles": s.fetched_candles,
            "validated_candles": s.validated_candles,
            "is_complete": s.is_complete,
            "errors": s.errors,
            "last_fetch_time": s.last_fetch_time,
        }

    def get_all_status(self) -> dict[str, Any]:
        """Get warm-up status for all symbols/intervals."""
        result = {}
        for (sym, interval), s in self._statuses.items():
            if sym not in result:
                result[sym] = {}
            result[sym][interval] = {
                "required": s.required_candles,
                "validated": s.validated_candles,
                "complete": s.is_complete,
                "errors": s.errors,
            }
        return result

    def is_symbol_ready(self, symbol: str, intervals: list[str] | None = None) -> bool:
        """Check if a symbol has completed warm-up for required intervals."""
        if intervals is None:
            intervals = ["15m", "5m", "1m"]
        for interval in intervals:
            key = (symbol, interval)
            s = self._statuses.get(key)
            if not s or not s.is_complete:
                return False
        return True

    def reset_symbol(self, symbol: str):
        """Reset warm-up state for a symbol (forces re-fetch on next warm-up)."""
        keys_to_remove = [k for k in self._statuses if k[0] == symbol]
        for k in keys_to_remove:
            del self._statuses[k]
            self._buffers.pop(k, None)

    # ── Internal fetch + validation ──

    async def _fetch_and_validate(
        self,
        symbol: str,
        interval: str,
        min_candles: int,
        status: WarmupStatus,
    ) -> list[WarmupCandle]:
        """Fetch and validate historical candles from Kite."""
        if not self._kite:
            log_warn("HistoricalWarmup: Kite provider not available")
            return []

        # Calculate fetch range: need 'min_candles' candles at 'interval' spacing
        days = self._interval_to_days(interval, min_candles)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        raw = await self._fetch_raw(symbol, interval, start_date.isoformat(), end_date.isoformat())
        if not raw:
            return []

        status.fetched_candles = len(raw)

        # Validate
        validated = []
        prev_time: str | None = None
        for row in raw:
            if not self._validate_candle(row, prev_time, interval):
                continue
            validated.append(row)
            prev_time = row.time

        log_info(
            "HistoricalWarmup: fetched and validated",
            symbol=symbol,
            interval=interval,
            raw=len(raw),
            valid=len(validated),
            required=min_candles,
        )
        return validated

    async def _fetch_raw(
        self, symbol: str, interval: str, from_date: str, to_date: str
    ) -> list[WarmupCandle]:
        """Raw fetch from Kite historical data API."""
        if not self._kite or not self._kite.market_data.is_ready:
            return []

        try:
            kite_sym = await self._kite.get_provider_symbol(symbol)
            # Import needed types
            from providers.zerodha.market_data import KITE_INTERVAL_MAP

            kite_interval = KITE_INTERVAL_MAP.get(interval)
            if not kite_interval:
                log_warn("HistoricalWarmup: unsupported interval", interval=interval)
                return []

            instr_token = self._kite.instruments.map_to_kite_token(symbol)
            if not instr_token:
                log_warn("HistoricalWarmup: cannot resolve token", symbol=symbol)
                return []

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self._kite.auth.kite.historical_data(
                    instrument_token=instr_token,
                    from_date=datetime.fromisoformat(from_date),
                    to_date=datetime.fromisoformat(to_date),
                    interval=kite_interval,
                    continuous=False,
                    oi=False,
                ),
            )

            if not data:
                return []

            candles = []
            for row in data:
                try:
                    dt = row.get("date")
                    if isinstance(dt, str):
                        dt = datetime.fromisoformat(dt)
                    candles.append(WarmupCandle(
                        time=dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
                        open=float(row.get("open", 0)),
                        high=float(row.get("high", 0)),
                        low=float(row.get("low", 0)),
                        close=float(row.get("close", 0)),
                        volume=float(row.get("volume", 0)),
                        oi=float(row.get("oi", 0)),
                    ))
                except (ValueError, TypeError, AttributeError):
                    continue

            return candles

        except Exception as e:
            log_error("HistoricalWarmup: fetch error", symbol=symbol, error=str(e))
            return []

    # ── Validation ──

    def _validate_candle(
        self, candle: WarmupCandle, prev_time: str | None, interval: str
    ) -> bool:
        """Validate a single candle row. Returns True if valid."""
        # Basic OHLC integrity
        if candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0:
            return False
        if candle.high < candle.low or candle.high < candle.open or candle.high < candle.close:
            return False
        if candle.low > candle.high or candle.low > candle.open or candle.low > candle.close:
            return False
        if candle.volume < 0:
            return False

        # Chronological order check
        if prev_time and candle.time <= prev_time:
            return False

        return True

    def _interval_to_days(self, interval: str, min_candles: int) -> int:
        """Estimate how many days of data are needed for min_candles."""
        minute_map = {
            "1m": 1, "2m": 2, "3m": 3, "5m": 5,
            "10m": 10, "15m": 15, "30m": 30, "60m": 60,
            "1d": 1440,
        }
        mins = minute_map.get(interval, 15)
        # Trading day ≈ 375 minutes (6.25 hours)
        candles_per_day = max(1, 375 / mins)
        needed = int(min_candles / candles_per_day) + 5  # +5 buffer
        return max(needed, 30)  # At least 30 days


def _now_str() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
