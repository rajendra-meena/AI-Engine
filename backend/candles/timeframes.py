"""
MarketMind AI — Supported Timeframes

Central registry of all supported candle timeframes.
"""

from datetime import datetime
from dataclasses import dataclass


@dataclass
class TimeframeDef:
    label: str  # e.g. "1 min"
    key: str  # e.g. "1m"
    minutes: int  # duration in minutes


SUPPORTED_TIMEFRAMES: list[TimeframeDef] = [
    TimeframeDef(label="1 min", key="1m", minutes=1),
    TimeframeDef(label="2 min", key="2m", minutes=2),
    TimeframeDef(label="3 min", key="3m", minutes=3),
    TimeframeDef(label="5 min", key="5m", minutes=5),
    TimeframeDef(label="10 min", key="10m", minutes=10),
    TimeframeDef(label="15 min", key="15m", minutes=15),
    TimeframeDef(label="30 min", key="30m", minutes=30),
    TimeframeDef(label="60 min", key="60m", minutes=60),
]

TIMEFRAME_KEYS = [tf.key for tf in SUPPORTED_TIMEFRAMES]


def round_to_timeframe(timestamp: datetime, minutes: int) -> datetime:
    """
    Round a datetime DOWN to the start of its timeframe bucket.

    Example: 10:37 with 5m → 10:35
             10:37 with 15m → 10:30
    """
    overflow = timestamp.minute % minutes
    return timestamp.replace(
        minute=timestamp.minute - overflow, second=0, microsecond=0
    )
