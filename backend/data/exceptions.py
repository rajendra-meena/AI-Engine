"""
MarketMind AI — Market Data Provider Exceptions

Consistent exception hierarchy for all data provider operations.
No caller should need to catch yfinance-specific errors.
"""


class ProviderError(Exception):
    """Base exception for all data provider errors."""

    pass


class ProviderUnavailable(ProviderError):
    """The provider is not available (offline, not configured, etc.)."""

    def __init__(self, provider_name: str, reason: str = ""):
        msg = f"Provider '{provider_name}' is unavailable"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
        self.provider_name = provider_name
        self.reason = reason


class InvalidSymbol(ProviderError):
    """The requested symbol is not supported by this provider."""

    def __init__(self, symbol: str, provider_name: str = ""):
        msg = f"Invalid symbol '{symbol}'"
        if provider_name:
            msg += f" for provider '{provider_name}'"
        super().__init__(msg)
        self.symbol = symbol


class InvalidInterval(ProviderError):
    """The requested interval is not supported by this provider."""

    def __init__(self, interval: str, provider_name: str = ""):
        msg = f"Invalid interval '{interval}'"
        if provider_name:
            msg += f" for provider '{provider_name}'"
        super().__init__(msg)
        self.interval = interval


class DataUnavailable(ProviderError):
    """The requested market data is not available from this provider."""

    def __init__(self, symbol: str, reason: str = ""):
        msg = f"No data available for '{symbol}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
        self.symbol = symbol


class Timeout(ProviderError):
    """The provider request timed out."""

    def __init__(self, provider_name: str, timeout_sec: int = 0):
        msg = f"Provider '{provider_name}' request timed out"
        if timeout_sec:
            msg += f" after {timeout_sec}s"
        super().__init__(msg)
