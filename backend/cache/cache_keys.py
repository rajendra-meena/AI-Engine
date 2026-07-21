"""
MarketMind AI — Cache Key Standardization

Every cache key in the application is generated here.
No module should construct cache keys by string concatenation.

Key namespacing:
    intraday:{symbol}:{interval}
    daily:{symbol}:{date_range}
    reference:{symbol}
    provider:status
    health
"""


def intraday_key(symbol: str, interval: str) -> str:
    """Key for cached intraday candle data."""
    return f"intraday:{symbol}:{interval}"


def daily_key(symbol: str) -> str:
    """Key for cached daily OHLC data."""
    return f"daily:{symbol}"


def reference_key(symbol: str) -> str:
    """Key for cached daily reference levels."""
    return f"reference:{symbol}"


def provider_status_key() -> str:
    """Key for cached provider health status."""
    return "provider:status"


def health_key() -> str:
    """Key for cached health check result."""
    return "health"


def symbol_pattern(symbol: str) -> str:
    """Pattern to match all keys for a given symbol (for invalidation)."""
    return f"*:{symbol}:*"


def interval_pattern(interval: str) -> str:
    """Pattern to match all keys for a given interval."""
    return f"intraday:*:{interval}"
