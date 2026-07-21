"""
MarketMind AI — Provider Registry

Static catalog of all known provider types and their metadata.
Used for discovery and documentation. The runtime creation is handled
by ProviderFactory.

To add a new provider (future):
  1. Create the provider class in data/providers/ (e.g. zerodha_provider.py)
  2. Register it here with its metadata
  3. Add it to ProviderFactory._create_provider()
"""

from dataclasses import dataclass
from data.provider_types import ProviderType


@dataclass
class ProviderRegistration:
    """Metadata for a registered provider type."""
    name: str
    display_name: str
    provider_type: ProviderType
    description: str
    requires_api_key: bool = False
    requires_websocket: bool = False
    is_active: bool = False


# ── Registry — the single source of truth for available providers ──

REGISTRY: list[ProviderRegistration] = [
    ProviderRegistration(
        name="yahoo",
        display_name="Yahoo Finance",
        provider_type=ProviderType.YAHOO,
        description="Free market data via yfinance library. No API key required.",
        requires_api_key=False,
        requires_websocket=False,
        is_active=True,
    ),
    # ── Future providers (placeholders) ──
    ProviderRegistration(
        name="kite",
        display_name="Zerodha Kite",
        provider_type=ProviderType.BROKER,
        description="Zerodha Kite Connect API. Requires API key and access token.",
        requires_api_key=True,
        requires_websocket=True,
        is_active=False,
    ),
    ProviderRegistration(
        name="angel",
        display_name="Angel One",
        provider_type=ProviderType.BROKER,
        description="Angel One Smart API. Requires API key and access token.",
        requires_api_key=True,
        requires_websocket=True,
        is_active=False,
    ),
    ProviderRegistration(
        name="csv_replay",
        display_name="CSV Replay",
        provider_type=ProviderType.REPLAY,
        description="Replay historical data from CSV files for backtesting.",
        requires_api_key=False,
        requires_websocket=False,
        is_active=False,
    ),
]


def get_registration(name: str) -> ProviderRegistration | None:
    """Look up a provider registration by name."""
    for r in REGISTRY:
        if r.name == name:
            return r
    return None


def list_active_providers() -> list[ProviderRegistration]:
    """Return all currently active provider registrations."""
    return [r for r in REGISTRY if r.is_active]


def list_all_providers() -> list[ProviderRegistration]:
    """Return all known provider registrations (active and inactive)."""
    return list(REGISTRY)
