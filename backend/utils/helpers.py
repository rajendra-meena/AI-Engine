"""
MarketMind AI — Shared Helper Functions

Small reusable utilities used across the backend.
New helpers should be added here rather than in individual modules.
"""

from core.symbols import get_ticker


def get_ticker_from_display(display_name: str) -> str:
    """Convert a display name (e.g. 'NIFTY 50') to a Yahoo ticker (e.g. '^NSEI').

    Delegates to the central symbol registry so there's one source of truth.
    """
    return get_ticker(display_name)


def parse_date_str(date_val) -> str:
    """Safely parse a candle date/datetime column into a date string YYYY-MM-DD."""
    if hasattr(date_val, "strftime"):
        return date_val.strftime("%Y-%m-%d")
    return str(date_val)[:10]


def is_intraday_interval(interval: str) -> bool:
    """Check if the interval is intraday (minute/hour based) vs daily+."""
    if not interval:
        return False
    interval = interval.strip().lower()
    return interval.endswith("m") or interval.endswith("h")
