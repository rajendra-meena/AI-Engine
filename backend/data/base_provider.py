"""
MarketMind AI — Abstract Base Provider

The interface that every market data provider must implement.
Services should ONLY interact with providers through this interface.

All methods are async. All return normalized types from provider_types.py.
All exceptions come from exceptions.py — never raw provider-specific errors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from data.provider_types import (
    ProviderType,
    ProviderHealth,
    DailyOHLC,
    IntradayCandle,
    DailyReferenceLevels,
)


@dataclass
class ProviderCapabilities:
    """Declares what a provider supports."""

    provider_name: str
    provider_type: ProviderType
    supports_daily: bool = True
    supports_intraday: bool = True
    supports_reference_levels: bool = True
    supports_symbol_discovery: bool = False
    symbols: list[str] = field(default_factory=list)
    intervals: list[str] = field(default_factory=list)


class BaseProvider(ABC):
    """Abstract base class for all market data providers."""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the data source. Return True if successful."""
        ...

    @abstractmethod
    async def disconnect(self):
        """Close the connection and clean up resources."""
        ...

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """Return current health status of this provider."""
        ...

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return the capabilities and supported symbols/intervals of this provider."""
        ...

    @abstractmethod
    async def fetch_daily(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[DailyOHLC]:
        """
        Fetch daily OHLC data for a symbol and date range.

        Args:
            symbol: Internal normalized symbol (e.g. 'NIFTY 50')
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of DailyOHLC records, oldest first.

        Raises:
            InvalidSymbol: Symbol not supported by this provider.
            DataUnavailable: No data returned for the given range.
            ProviderUnavailable: Provider is offline.
            Timeout: Request timed out.
        """
        ...

    @abstractmethod
    async def fetch_intraday(
        self,
        symbol: str,
        interval: str,
        days: int,
    ) -> list[IntradayCandle]:
        """
        Fetch intraday candle data for a symbol.

        Args:
            symbol: Internal normalized symbol (e.g. 'NIFTY 50')
            interval: Interval key (e.g. '15m')
            days: Number of days of history to fetch

        Returns:
            List of IntradayCandle records, oldest first.

        Raises:
            InvalidSymbol: Symbol not supported by this provider.
            InvalidInterval: Interval not supported by this provider.
            DataUnavailable: No data returned.
            ProviderUnavailable: Provider is offline.
        """
        ...

    @abstractmethod
    async def fetch_daily_reference_levels(
        self,
        symbol: str,
    ) -> DailyReferenceLevels | None:
        """
        Fetch daily data specifically for reference level computation.

        Args:
            symbol: Internal normalized symbol

        Returns:
            DailyReferenceLevels or None if insufficient data.
        """
        ...

    @abstractmethod
    async def validate_symbol(self, symbol: str) -> bool:
        """Check if a symbol is supported by this provider."""
        ...

    @abstractmethod
    async def get_provider_symbol(self, internal_symbol: str) -> str:
        """
        Convert an internal normalized symbol to the provider-specific symbol string.

        E.g. 'NIFTY 50' → '^NSEI' (Yahoo), 'NIFTY' (Zerodha)
        """
        ...
