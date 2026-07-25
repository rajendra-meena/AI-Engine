"""
MarketMind AI — Interval Registry

Central registry for every supported chart interval.
Each interval carries metadata so no module needs to parse interval strings.

For broker integration in future phases: add the broker's interval string
to each record so the registry maps intervals across providers.
"""

from typing import NamedTuple


class IntervalInfo(NamedTuple):
    """Metadata for a single chart interval."""

    label: str  # Display name (e.g. "1 min")
    yahoo_key: str  # Key used in yfinance calls (e.g. "1m")
    minutes: int  # Duration in minutes
    seconds: int  # Duration in seconds (computed)
    is_intraday: bool  # True if interval < 1 day


def _build_intervals():
    """Build the full interval registry."""
    raw = [
        # (label, yahoo_key, minutes)
        ("1 min", "1m", 1),
        ("2 min", "2m", 2),
        ("3 min", "3m", 3),
        ("5 min", "5m", 5),
        ("10 min", "10m", 10),
        ("15 min", "15m", 15),
        ("30 min", "30m", 30),
        ("60 min", "60m", 60),
    ]
    return {
        key: IntervalInfo(
            label=label,
            yahoo_key=key,
            minutes=mins,
            seconds=mins * 60,
            is_intraday=True,
        )
        for label, key, mins in raw
    }


# Populated once on import
INTERVALS = _build_intervals()

# Ordered list of interval keys (fastest first)
INTERVAL_KEYS = list(INTERVALS.keys())

# Default
DEFAULT_INTERVAL = "15m"

# Fast intervals (limited history)
FAST_INTERVAL_KEYS = ("1m", "2m")


def get_interval(key: str) -> IntervalInfo | None:
    """Look up interval metadata by key. Returns None for unknown keys."""
    return INTERVALS.get(key)


def is_valid_interval(key: str) -> bool:
    """Check if a key corresponds to a known interval."""
    return key in INTERVALS


def is_intraday_interval(key: str) -> bool:
    """Check if an interval key is intraday (vs daily+). Same as is_valid_interval for now."""
    return key in INTERVALS


def interval_to_minutes(key: str) -> int:
    """Convert an interval key to its duration in minutes."""
    info = INTERVALS.get(key)
    if info:
        return info.minutes
    # Fallback for daily/weekly etc.: parse suffix
    if key.endswith("m"):
        return int(key[:-1])
    if key.endswith("h"):
        return int(key[:-1]) * 60
    return 0
