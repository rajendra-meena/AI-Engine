"""
MarketMind AI — Symbol Registry

Central registry for every tradable symbol/instrument.
Maps display names to Yahoo tickers and contains placeholders for future brokers.

Every module should use this registry instead of hardcoding symbol mappings.
"""

from typing import NamedTuple


class SymbolInfo(NamedTuple):
    """Metadata for a single trading symbol."""
    display_name: str         # User-facing name (e.g. "NIFTY 50")
    yahoo_ticker: str         # yfinance symbol
    exchange: str             # Primary exchange
    # Future fields (placeholders for broker integration):
    # zerodha_symbol: str
    # angel_symbol: str
    # fyers_symbol: str
    # lot_size: int
    # tick_size: float


def _build_symbols():
    """Build the full symbol registry."""
    return {
        "NIFTY 50": SymbolInfo(
            display_name="NIFTY 50",
            yahoo_ticker="^NSEI",
            exchange="NSE",
        ),
        "BANKNIFTY": SymbolInfo(
            display_name="BANKNIFTY",
            yahoo_ticker="^NSEBANK",
            exchange="NSE",
        ),
        "SENSEX": SymbolInfo(
            display_name="SENSEX",
            yahoo_ticker="^BSESN",
            exchange="BSE",
        ),
    }


# Populated once on import
SYMBOLS = _build_symbols()

# Display name → Yahoo ticker map (fast lookup)
SYMBOL_MAP = {name: info.yahoo_ticker for name, info in SYMBOLS.items()}

# Yahoo ticker → Display name map (reverse lookup)
DISPLAY_NAMES = {info.yahoo_ticker: name for name, info in SYMBOLS.items()}

# Default symbol
DEFAULT_SYMBOL = "NIFTY 50"


def get_symbol(display_name: str) -> SymbolInfo | None:
    """Look up symbol metadata by display name."""
    return SYMBOLS.get(display_name)


def get_ticker(display_name: str) -> str:
    """Convert a display name to a Yahoo ticker. Returns input unchanged if unknown."""
    return SYMBOL_MAP.get(display_name, display_name)


def get_display_name(yahoo_ticker: str) -> str:
    """Convert a Yahoo ticker to a display name. Returns input unchanged if unknown."""
    return DISPLAY_NAMES.get(yahoo_ticker, yahoo_ticker)


def is_valid_symbol(display_name: str) -> bool:
    """Check if a display name corresponds to a known symbol."""
    return display_name in SYMBOLS


def list_display_names() -> list[str]:
    """Return all known symbol display names."""
    return list(SYMBOLS.keys())
