"""
Zerodha Kite Connect — Market Data

Provides historical market data fetching via Kite Connect REST APIs:
- Intraday candles (minute, etc.)
- Daily candles
- Quotes (LTP, OHLC, volume, OI)
- Instrument history

All methods normalize Kite data into the system's provider types.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any

from data.provider_types import DailyOHLC, IntradayCandle
from data.exceptions import InvalidSymbol, InvalidInterval, DataUnavailable
from utils.logger import log_info, log_warn, log_error


# Kite interval map: internal interval → Kite interval string
KITE_INTERVAL_MAP: dict[str, str] = {
    "1m": "minute",
    "2m": "2minute",
    "3m": "3minute",
    "5m": "5minute",
    "10m": "10minute",
    "15m": "15minute",
    "30m": "30minute",
    "60m": "60minute",
    "1d": "day",
    "day": "day",
}

# Reverse map: Kite interval → internal interval
INTERNAL_INTERVAL_MAP: dict[str, str] = {v: k for k, v in KITE_INTERVAL_MAP.items()}


class KiteMarketDataError(Exception):
    """Base exception for Kite market data errors."""
    pass


class KiteMarketData:
    """
    Fetches market data from Kite Connect REST API.

    Converts Kite-specific responses into normalized system types.
    Should never be called directly — use via KiteProvider (BaseProvider).
    """

    def __init__(self, kite=None, instrument_manager=None):
        self._kite = kite
        self._instrument_manager = instrument_manager

    def set_kite(self, kite):
        self._kite = kite

    def set_instrument_manager(self, manager):
        self._instrument_manager = manager

    @property
    def is_ready(self) -> bool:
        return self._kite is not None

    # ── Symbol helpers ──

    def _resolve_symbol(self, internal_symbol: str) -> tuple[str, str, int | None]:
        """
        Resolve internal symbol to Kite trading symbol and exchange.

        Returns:
            (trading_symbol, exchange, instrument_token_or_None)
        """
        # Use instrument manager if available
        if self._instrument_manager and self._instrument_manager.is_loaded:
            kite_sym = self._instrument_manager.map_to_kite_symbol(internal_symbol)
            token = self._instrument_manager.map_to_kite_token(internal_symbol)
            if kite_sym:
                return kite_sym, "NSE", token

        # Fallback manual mapping
        mapping = {
            "NIFTY 50": ("NIFTY", "NSE"),
            "BANKNIFTY": ("BANKNIFTY", "NSE"),
            "BANK NIFTY": ("BANKNIFTY", "NSE"),
            "SENSEX": ("SENSEX", "BSE"),
        }
        result = mapping.get(internal_symbol)
        if result:
            return (*result, None)
        # Try direct use
        return (internal_symbol, "NSE", None)

    # ── Historical data ──

    async def fetch_intraday(
        self, symbol: str, interval: str, days: int
    ) -> list[IntradayCandle]:
        """
        Fetch intraday candles from Kite.

        Kite provides intraday data for up to 60 days for minute intervals.
        """
        if not self._kite:
            raise KiteMarketDataError("Kite not connected")

        kite_interval = KITE_INTERVAL_MAP.get(interval)
        if not kite_interval:
            raise InvalidInterval(interval, "zerodha")

        trading_symbol, exchange, token = self._resolve_symbol(symbol)

        if not trading_symbol:
            raise InvalidSymbol(symbol, "zerodha")

        # Kite needs instrument_token for history API
        instr_token = token
        if instr_token is None and self._instrument_manager and self._instrument_manager.is_loaded:
            instr_token = self._instrument_manager.map_to_kite_token(symbol)

        if instr_token is None:
            raise InvalidSymbol(symbol, "zerodha: cannot resolve instrument token")

        from_date = datetime.now(timezone.utc) - timedelta(days=days)
        to_date = datetime.now(timezone.utc)

        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self._kite.historical_data(
                    instrument_token=instr_token,
                    from_date=from_date,
                    to_date=to_date,
                    interval=kite_interval,
                    continuous=False,
                    oi=False,
                ),
            )

            if not data:
                raise DataUnavailable(symbol, "Kite returned no intraday data")

            candles = []
            for row in data:
                try:
                    dt = row.get("date")
                    if isinstance(dt, str):
                        dt = datetime.fromisoformat(dt)
                    candles.append(
                        IntradayCandle(
                            time=dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
                            open=float(row.get("open", 0)),
                            high=float(row.get("high", 0)),
                            low=float(row.get("low", 0)),
                            close=float(row.get("close", 0)),
                            volume=float(row.get("volume", 0)),
                        )
                    )
                except (ValueError, TypeError) as e:
                    log_warn("KiteMarketData: skip bad candle row", error=str(e))
                    continue

            if not candles:
                raise DataUnavailable(symbol, "No valid candles parsed from Kite response")

            log_info(
                "KiteMarketData: fetched intraday",
                symbol=symbol,
                interval=interval,
                candles=len(candles),
            )
            return candles

        except DataUnavailable:
            raise
        except Exception as e:
            log_error("KiteMarketData: intraday fetch failed", symbol=symbol, error=str(e))
            raise KiteMarketDataError(f"Intraday fetch failed: {e}") from e

    async def fetch_daily(
        self, symbol: str, start_date: date, end_date: date
    ) -> list[DailyOHLC]:
        """Fetch daily OHLC data from Kite."""
        if not self._kite:
            raise KiteMarketDataError("Kite not connected")

        trading_symbol, exchange, token = self._resolve_symbol(symbol)
        instr_token = token
        if instr_token is None and self._instrument_manager and self._instrument_manager.is_loaded:
            instr_token = self._instrument_manager.map_to_kite_token(symbol)

        if instr_token is None:
            raise InvalidSymbol(symbol, "zerodha: cannot resolve instrument token")

        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self._kite.historical_data(
                    instrument_token=instr_token,
                    from_date=datetime.combine(start_date, datetime.min.time()),
                    to_date=datetime.combine(end_date, datetime.max.time()),
                    interval="day",
                    continuous=False,
                    oi=False,
                ),
            )

            if not data:
                raise DataUnavailable(symbol, "Kite returned no daily data")

            records = []
            for row in data:
                try:
                    dt = row.get("date")
                    if isinstance(dt, str):
                        dt = datetime.fromisoformat(dt)
                    records.append(
                        DailyOHLC(
                            date=dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt),
                            open=float(row.get("open", 0)),
                            high=float(row.get("high", 0)),
                            low=float(row.get("low", 0)),
                            close=float(row.get("close", 0)),
                            volume=float(row.get("volume", 0)),
                        )
                    )
                except (ValueError, TypeError):
                    continue

            return records

        except DataUnavailable:
            raise
        except Exception as e:
            log_error("KiteMarketData: daily fetch failed", symbol=symbol, error=str(e))
            raise KiteMarketDataError(f"Daily fetch failed: {e}") from e

    async def fetch_quote(self, symbol: str) -> dict[str, Any] | None:
        """Fetch latest quote for a symbol."""
        if not self._kite:
            return None

        trading_symbol, exchange, token = self._resolve_symbol(symbol)
        if not trading_symbol:
            return None

        try:
            loop = asyncio.get_event_loop()
            quotes = await loop.run_in_executor(
                None,
                lambda: self._kite.quote(f"{exchange}:{trading_symbol}"),
            )
            key = f"{exchange}:{trading_symbol}"
            q = quotes.get(key, {})
            if not q:
                return None

            ohlc = q.get("ohlc", {})
            depth = q.get("depth", {})
            timestamp = q.get("timestamp", "")

            return {
                "symbol": symbol,
                "trading_symbol": trading_symbol,
                "exchange": exchange,
                "last_price": q.get("last_price"),
                "change": q.get("change"),
                "volume": q.get("volume"),
                "open": ohlc.get("open"),
                "high": ohlc.get("high"),
                "low": ohlc.get("low"),
                "close": ohlc.get("close"),
                "oi": q.get("oi"),
                "bid": depth.get("buy", [{}])[0].get("price") if depth.get("buy") else None,
                "ask": depth.get("sell", [{}])[0].get("price") if depth.get("sell") else None,
                "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
            }
        except Exception as e:
            log_warn("KiteMarketData: quote fetch failed", symbol=symbol, error=str(e))
            return None

    async def fetch_ltp(self, symbol: str) -> float | None:
        """Fetch last traded price for a symbol."""
        if not self._kite:
            return None

        trading_symbol, exchange, token = self._resolve_symbol(symbol)
        if not trading_symbol:
            return None

        try:
            loop = asyncio.get_event_loop()
            ltp_data = await loop.run_in_executor(
                None,
                lambda: self._kite.ltp(f"{exchange}:{trading_symbol}"),
            )
            key = f"{exchange}:{trading_symbol}"
            return ltp_data.get(key, {}).get("last_price")
        except Exception as e:
            log_warn("KiteMarketData: LTP fetch failed", symbol=symbol, error=str(e))
            return None

    async def fetch_ohlc(self, symbol: str) -> dict[str, float] | None:
        """Fetch OHLC for a symbol."""
        if not self._kite:
            return None

        trading_symbol, exchange, token = self._resolve_symbol(symbol)
        if not trading_symbol:
            return None

        try:
            loop = asyncio.get_event_loop()
            quotes = await loop.run_in_executor(
                None,
                lambda: self._kite.quote(f"{exchange}:{trading_symbol}"),
            )
            key = f"{exchange}:{trading_symbol}"
            q = quotes.get(key, {})
            ohlc = q.get("ohlc", {})
            return {
                "open": ohlc.get("open"),
                "high": ohlc.get("high"),
                "low": ohlc.get("low"),
                "close": ohlc.get("close"),
            }
        except Exception as e:
            log_warn("KiteMarketData: OHLC fetch failed", symbol=symbol, error=str(e))
            return None

    # ── Supported intervals ──

    def supported_intervals(self) -> list[str]:
        return list(KITE_INTERVAL_MAP.keys())

    def kite_interval(self, internal_interval: str) -> str | None:
        return KITE_INTERVAL_MAP.get(internal_interval)

    def internal_interval(self, kite_interval: str) -> str | None:
        return INTERNAL_INTERVAL_MAP.get(kite_interval)
