"""
MarketMind AI — Validators

Reusable validation functions for symbols, intervals, dates, and configuration.
Every module should call these instead of duplicating validation logic.
"""

from datetime import datetime

from core.symbols import is_valid_symbol, list_canonical_names
from core.intervals import is_valid_interval


def validate_symbol(display_name: str) -> str | None:
    """Validate a symbol display name. Returns error message or None."""
    if not display_name or not isinstance(display_name, str):
        return "Symbol must be a non-empty string"
    if not is_valid_symbol(display_name):
        valid = ", ".join(list_canonical_names())
        return f"Unknown symbol '{display_name}'. Valid: {valid}"
    return None


def validate_interval(interval: str) -> str | None:
    """Validate a chart interval string. Returns error message or None."""
    if not interval or not isinstance(interval, str):
        return "Interval must be a non-empty string"
    if not is_valid_interval(interval):
        return f"Unsupported interval '{interval}'. Valid: 1m, 3m, 5m, 15m, 30m, 60m"
    return None


def validate_date_str(date_str: str) -> str | None:
    """Validate a YYYY-MM-DD date string. Returns error message or None."""
    if not date_str or not isinstance(date_str, str):
        return "Date must be a non-empty string"
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return f"Invalid date format '{date_str}'. Expected YYYY-MM-DD"
    return None


def validate_limit(limit: int) -> str | None:
    """Validate a pagination limit value. Returns error message or None."""
    if not isinstance(limit, int) or limit < 1:
        return "Limit must be a positive integer"
    if limit > 500:
        return "Limit cannot exceed 500"
    return None
