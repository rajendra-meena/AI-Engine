"""
MarketMind AI — Yahoo Finance Provider

Wraps all yfinance interactions behind the BaseProvider interface.
No code outside this file should import yfinance directly.

This is a wrapper, not a rewrite — it preserves the exact same behavior
as the original market_service.py implementation.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone, timedelta

import yfinance as yf

from data.base_provider import BaseProvider, ProviderCapabilities
from data.provider_types import (
    ProviderType,
    ProviderStatus,
    ProviderHealth,
    DailyOHLC,
    IntradayCandle,
    DailyReferenceLevels,
)
from data.exceptions import (
    InvalidSymbol,
    InvalidInterval,
    DataUnavailable,
    ProviderUnavailable,
    Timeout,
)
from core.symbols import get_ticker, is_valid_symbol
from core.intervals import is_valid_interval
from core.constants import (
    DAILY_REFS_LOOKBACK_DAYS,
    DAILY_REFS_WEEKLY_WINDOW,
    DAILY_REFS_MIN_CANDLES,
    BACKTEST_DAILY_INTERVAL,
    FAST_INTERVALS,
    INTRADAY_MAX_DAYS_FAST,
    INTRADAY_MAX_DAYS_DEFAULT,
)
from core.symbols import list_display_names
from core.intervals import INTERVAL_KEYS
from utils.helpers import parse_date_str
from utils.logger import log_info, log_warn


class YahooProvider(BaseProvider):
    """
    Provider implementation for Yahoo Finance (via yfinance).

    Converts all yfinance-specific data structures into normalized types.
    Every public method is async and raises Provider exceptions on failure.
    """

    def __init__(self):
        self._connected = False
        self._last_success: datetime | None = None
        self._name = "yahoo"

    # ── Lifecycle ──

    async def connect(self) -> bool:
        """Yahoo Finance doesn't need a persistent connection."""
        self._connected = True
        log_info("YahooProvider connected")
        return True

    async def disconnect(self):
        """Yahoo Finance has nothing to disconnect."""
        self._connected = False
        log_info("YahooProvider disconnected")

    # ── Capabilities ──

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name=self._name,
            provider_type=ProviderType.YAHOO,
            supports_daily=True,
            supports_intraday=True,
            supports_reference_levels=True,
            symbols=list_display_names(),
            intervals=list(INTERVAL_KEYS),
        )

    # ── Health ──

    async def health(self) -> ProviderHealth:
        """Check provider health by fetching a small data sample."""
        try:
            df = await asyncio.to_thread(
                yf.Ticker("^NSEI").history, period="1d", interval="1d"
            )
            if df.empty:
                return ProviderHealth(
                    status=ProviderStatus.DEGRADED,
                    provider_name=self._name,
                    provider_type=ProviderType.YAHOO,
                    error_message="Returned empty response",
                )
            self._last_success = datetime.now(timezone.utc)
            symbols = len(list_display_names())
            return ProviderHealth(
                status=ProviderStatus.HEALTHY,
                provider_name=self._name,
                provider_type=ProviderType.YAHOO,
                last_success=self._last_success,
                supported_symbols=symbols,
                supported_intervals=len(INTERVAL_KEYS),
            )
        except Exception as e:
            return ProviderHealth(
                status=ProviderStatus.UNAVAILABLE,
                provider_name=self._name,
                provider_type=ProviderType.YAHOO,
                error_message=str(e),
            )

    # ── Symbol mapping ──

    async def validate_symbol(self, symbol: str) -> bool:
        return is_valid_symbol(symbol)

    async def get_provider_symbol(self, internal_symbol: str) -> str:
        return get_ticker(internal_symbol)

    # ── Daily data ──

    async def fetch_daily(
        self, symbol: str, start_date: date, end_date: date
    ) -> list[DailyOHLC]:
        ticker = await self.get_provider_symbol(symbol)
        log_info(
            "YahooProvider.fetch_daily",
            symbol=symbol,
            ticker=ticker,
            start=str(start_date),
            end=str(end_date),
        )

        df = await asyncio.to_thread(
            yf.Ticker(ticker).history,
            start=start_date,
            end=end_date + timedelta(days=1),
        )

        if df.empty:
            raise DataUnavailable(symbol, "yfinance returned no daily data")

        df = df.reset_index()
        records = []
        for _, row in df.iterrows():
            date_val = row["Date"]
            records.append(
                DailyOHLC(
                    date=parse_date_str(date_val),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row.get("Volume", 0)),
                )
            )

        self._last_success = datetime.now(timezone.utc)
        return records

    # ── Intraday data ──

    async def fetch_intraday(
        self, symbol: str, interval: str, days: int
    ) -> list[IntradayCandle]:
        if not await self.validate_symbol(symbol):
            raise InvalidSymbol(symbol, self._name)
        if not is_valid_interval(interval):
            raise InvalidInterval(interval, self._name)

        ticker = await self.get_provider_symbol(symbol)
        max_days = (
            INTRADAY_MAX_DAYS_FAST
            if interval in FAST_INTERVALS
            else INTRADAY_MAX_DAYS_DEFAULT
        )
        period = f"{min(days, max_days)}d"

        log_info(
            "YahooProvider.fetch_intraday",
            symbol=symbol,
            ticker=ticker,
            interval=interval,
            period=period,
        )

        df = await asyncio.to_thread(
            yf.Ticker(ticker).history, period=period, interval=interval
        )

        if df.empty:
            raise DataUnavailable(
                symbol, f"yfinance returned no intraday data for {interval}"
            )

        df = df.reset_index()
        candles = []
        for _, row in df.iterrows():
            dt = row["Datetime"]
            candles.append(
                IntradayCandle(
                    time=dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row.get("Volume", 0)),
                )
            )

        self._last_success = datetime.now(timezone.utc)
        return candles

    # ── Backtest-specific: raw data for date range ──

    async def fetch_intraday_range(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "15m",
    ) -> list[dict]:
        """
        Fetch raw intraday candles for backtesting (date range, not period-based).

        Returns a list of dicts with keys: Datetime, Open, High, Low, Close, Volume.
        The caller (database.py) handles date filtering and processing.
        This avoids breaking existing backtesting logic while removing direct yfinance imports.
        """
        ticker = await self.get_provider_symbol(symbol)
        df = await asyncio.to_thread(
            yf.Ticker(ticker).history, start=start_date, end=end_date, interval=interval
        )
        if df.empty:
            return []
        df = df.reset_index()
        rows = []
        for _, row in df.iterrows():
            dt = row["Datetime"] if "Datetime" in df.columns else row.get("Date")
            rows.append(
                {
                    "Datetime": dt,
                    "Date": dt,
                    "Open": float(row["Open"]),
                    "High": float(row["High"]),
                    "Low": float(row["Low"]),
                    "Close": float(row["Close"]),
                    "Volume": float(row.get("Volume", 0)),
                }
            )
        return rows

    async def fetch_daily_range(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        """
        Fetch raw daily OHLC data for backtesting (date range).

        Returns a list of dicts with keys: Date, Open, High, Low, Close, Volume.
        """
        ticker = await self.get_provider_symbol(symbol)
        df = await asyncio.to_thread(
            yf.Ticker(ticker).history, start=start_date, end=end_date, interval="1d"
        )
        if df.empty:
            return []
        df = df.reset_index()
        rows = []
        for _, row in df.iterrows():
            date_val = row["Date"] if "Date" in df.columns else row.get("Datetime")
            rows.append(
                {
                    "Date": date_val,
                    "Open": float(row["Open"]),
                    "High": float(row["High"]),
                    "Low": float(row["Low"]),
                    "Close": float(row["Close"]),
                    "Volume": float(row.get("Volume", 0)),
                }
            )
        return rows

    # ── Daily reference levels ──

    async def fetch_daily_reference_levels(
        self, symbol: str
    ) -> DailyReferenceLevels | None:
        ticker = await self.get_provider_symbol(symbol)
        try:
            df = await asyncio.to_thread(
                yf.Ticker(ticker).history,
                period=f"{DAILY_REFS_LOOKBACK_DAYS}d",
                interval=BACKTEST_DAILY_INTERVAL,
            )
            if df.empty:
                return None

            df = df.reset_index()
            dailies = []
            for _, row in df.iterrows():
                date_val = row["Date"] if "Date" in df.columns else row.get("Datetime")
                dailies.append(
                    DailyOHLC(
                        date=parse_date_str(date_val),
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=float(row.get("Volume", 0)),
                    )
                )

            if len(dailies) >= DAILY_REFS_MIN_CANDLES:
                prev = dailies[-2]
                weekly_high = max(d.high for d in dailies[-DAILY_REFS_WEEKLY_WINDOW:])
                weekly_low = min(d.low for d in dailies[-DAILY_REFS_WEEKLY_WINDOW:])
                return DailyReferenceLevels(
                    prev_day_high=prev.high,
                    prev_day_low=prev.low,
                    prev_day_close=prev.close,
                    prev_day_open=prev.open,
                    weekly_high=weekly_high,
                    weekly_low=weekly_low,
                    prev_day_range=round(prev.high - prev.low, 2),
                    prev_day_midpoint=round((prev.high + prev.low) / 2, 2),
                    prev_day_vwap=round((prev.high + prev.low + prev.close) / 3, 2),
                )
            return None
        except Exception:
            return None
