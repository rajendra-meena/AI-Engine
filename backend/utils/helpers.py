"""
MarketMind AI — Shared Helper Functions

Small reusable utilities used across the backend.
"""

from core.config import SYMBOL_MAP


def get_ticker_from_display(display_name: str) -> str:
    """Convert a display name (e.g. 'NIFTY 50') to a Yahoo ticker (e.g. '^NSEI')."""
    return SYMBOL_MAP.get(display_name, display_name)


def parse_date_str(date_str: str):
    """Safely parse a candle date/datetime column into a date string YYYY-MM-DD."""
    if hasattr(date_str, "strftime"):
        return date_str.strftime("%Y-%m-%d")
    return str(date_str)[:10]


def is_intraday_interval(interval: str) -> bool:
    """Check if the interval is intraday (minute/hour based) vs daily+."""
    if not interval:
        return False
    interval = interval.strip().lower()
    return interval.endswith("m") or interval.endswith("h")
