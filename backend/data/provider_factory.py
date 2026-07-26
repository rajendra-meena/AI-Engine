"""
MarketMind AI — Provider Factory

Creates and caches provider instances. The application should never
instantiate providers directly — always use the factory.

Usage:
    factory = ProviderFactory()
    yahoo = factory.get_provider("yahoo")
    zerodha = factory.get_provider("zerodha")
    # or get the default:
    provider = factory.get_default_provider()

Auto Trade provider selection:
    The Auto Trade pipeline must use Zerodha Kite exclusively.
    Use get_auto_trade_provider() to obtain it.
    Yahoo Finance is blocked as an Auto Trade fallback.
"""

from data.base_provider import BaseProvider
from data.yahoo_provider import YahooProvider
from data.provider_types import ProviderType
from data.exceptions import ProviderUnavailable
from utils.logger import log_info


class ProviderFactory:
    """
    Factory for market data provider instances.

    Providers are cached once created. The factory is a singleton-like
    instance that lives for the application lifetime.
    """

    def __init__(self):
        self._instances: dict[str, BaseProvider] = {}
        self._active_provider: str = "yahoo"

    def get_provider(self, name: str = "yahoo") -> BaseProvider:
        """
        Get or create a provider by name.

        Args:
            name: Provider name ('yahoo', 'zerodha')

        Returns:
            A cached provider instance.

        Raises:
            ProviderUnavailable: Provider name is unknown.
        """
        if name not in self._instances:
            provider = self._create_provider(name)
            if provider is None:
                raise ProviderUnavailable(name, "Unknown provider type")
            self._instances[name] = provider
            log_info("ProviderFactory: created provider", name=name)
        return self._instances[name]

    def get_default_provider(self) -> BaseProvider:
        """Get the configured default provider."""
        return self.get_provider(self._active_provider)

    def set_active_provider(self, name: str):
        """Switch the active provider at runtime."""
        if name not in self._instances:
            self.get_provider(name)
        self._active_provider = name
        log_info("ProviderFactory: active provider changed", name=name)

    def get_active_provider_name(self) -> str:
        return self._active_provider

    def get_auto_trade_provider(self) -> BaseProvider:
        """
        Get the provider for the Auto Trade pipeline.

        Returns the Zerodha Kite provider instance.
        This is the ONLY provider used by Auto Trade.
        Yahoo Finance is never a fallback for Auto Trade.

        Raises:
            ProviderUnavailable: If the Zerodha provider cannot be created.
        """
        return self.get_provider("zerodha")

    def list_available_providers(self) -> list[str]:
        """Return a list of provider names that can be created."""
        return ["yahoo", "zerodha"]

    def list_active_instances(self) -> dict[str, BaseProvider]:
        """Return all cached provider instances."""
        return dict(self._instances)

    def _create_provider(self, name: str) -> BaseProvider | None:
        """Create a new provider instance by name. Returns None if unknown."""
        registry = {
            "yahoo": YahooProvider,
        }
        if name == "zerodha":
            from providers.zerodha.kite_provider import KiteProvider

            registry["zerodha"] = KiteProvider

        cls = registry.get(name)
        if cls is None:
            return None
        return cls()
