"""
MarketMind AI — Option Data Provider Protocol

Abstract interface for fetching option chain data.
Every provider (Zerodha, mock, future brokers) implements this protocol.
Services MUST only interact with providers through this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from options.models import (
    OptionChainSnapshot,
    OptionChainSlice,
    OptionInstrument,
    OptionQuote,
    OptionChainSource,
)


@dataclass(frozen=True)
class ProviderCapabilities:
    """Declares what a provider supports."""

    provider_name: str
    source: OptionChainSource
    supports_live_chain: bool = True
    supports_historical: bool = False
    supports_greeks: bool = False
    supports_multi_expiry: bool = True
    underlyings: tuple[str, ...] = ("NIFTY 50", "BANKNIFTY")
    max_poll_interval_seconds: float = 5.0


class OptionDataProvider(ABC):
    """Abstract base class for all option chain data providers."""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection. Return True if successful."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection and release resources."""
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Return current health/status of this provider."""
        ...

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return capabilities of this provider."""
        ...

    @abstractmethod
    async def fetch_chain_snapshot(
        self,
        underlying: str,
        expiries: list[date] | None = None,
    ) -> OptionChainSnapshot:
        """
        Fetch the full option chain snapshot for an underlying.

        Args:
            underlying: Canonical symbol (e.g. "NIFTY 50")
            expiries: Optional list of expiry dates to include.
                      If None, returns nearest expiry only.

        Returns:
            OptionChainSnapshot with all strikes for the requested expiries.

        Raises:
            ValueError: Unknown underlying.
            ProviderError: Provider unavailable or request failed.
        """
        ...

    @abstractmethod
    async def fetch_chain_slice(
        self,
        underlying: str,
        expiry: date,
    ) -> OptionChainSlice:
        """
        Fetch a single expiry slice of the option chain.

        Args:
            underlying: Canonical symbol
            expiry: Specific expiry date

        Returns:
            OptionChainSlice with all strikes for that expiry.

        Raises:
            ValueError: Unknown underlying or expiry.
            ProviderError: Provider unavailable.
        """
        ...

    @abstractmethod
    async def fetch_option_quote(
        self,
        underlying: str,
        expiry: date,
        strike: float,
        option_type: str,
    ) -> OptionQuote | None:
        """
        Fetch quote for a single option instrument.

        Args:
            underlying: Canonical symbol
            expiry: Expiry date
            strike: Strike price
            option_type: "CE" or "PE"

        Returns:
            OptionQuote or None if instrument not found.
        """
        ...

    @abstractmethod
    async def fetch_instruments(
        self,
        underlying: str,
        expiry: date | None = None,
    ) -> list[OptionInstrument]:
        """
        Fetch available option instruments for an underlying.

        Args:
            underlying: Canonical symbol
            expiry: Optional expiry filter

        Returns:
            List of OptionInstrument objects.
        """
        ...

    @abstractmethod
    async def get_available_expiries(
        self,
        underlying: str,
    ) -> list[date]:
        """
        Get available expiry dates for an underlying.

        Returns:
            Sorted list of expiry dates (nearest first).
        """
        ...
