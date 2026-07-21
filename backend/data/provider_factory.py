"""
MarketMind AI — Provider Factory

Creates and caches provider instances. The application should never
instantiate providers directly — always use the factory.

Usage:
    factory = ProviderFactory()
    yahoo = factory.get_provider("yahoo")
    # or get the default:
    provider = factory.get_default_provider()
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

    def get_provider(self, name: str = "yahoo") -> BaseProvider:
        """
        Get or create a provider by name.

        Args:
            name: Provider name ('yahoo' for now, 'zerodha'/'angel' in future)

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
        """Get the default provider (Yahoo Finance)."""
        return self.get_provider("yahoo")

    def list_available_providers(self) -> list[str]:
        """Return a list of provider names that can be created."""
        return ["yahoo"]

    def _create_provider(self, name: str) -> BaseProvider | None:
        """Create a new provider instance by name. Returns None if unknown."""
        registry = {
            "yahoo": YahooProvider,
        }
        cls = registry.get(name)
        if cls is None:
            return None
        return cls()
