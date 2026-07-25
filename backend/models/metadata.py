"""
MarketMind AI — Metadata Models

Small, reusable value objects for describing intervals, sessions, price levels,
and provider status. Used across other domain models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class SessionType(str, Enum):
    """Market session phase."""

    PRE_MARKET = "PreMarket"
    OPENING = "Opening"
    MID = "Mid"
    CLOSING = "Closing"
    CLOSED = "Closed"


@dataclass(frozen=True)
class MarketSession:
    """Current market session information."""

    session: SessionType = SessionType.CLOSED
    is_open: bool = False
    minutes_from_open: int = 0
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.session.value,
            "is_open": self.is_open,
            "minutes_from_open": self.minutes_from_open,
            "label": self.label or self.session.value,
        }


@dataclass(frozen=True)
class TimeframeInfo:
    """Metadata about a chart interval/timeframe."""

    key: str = ""  # e.g. "15m"
    label: str = ""  # e.g. "15 min"
    minutes: int = 0
    seconds: int = 0
    is_intraday: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "minutes": self.minutes,
            "seconds": self.seconds,
            "is_intraday": self.is_intraday,
        }


@dataclass(frozen=True)
class PriceLevel:
    """
    A price level with type classification (support, resistance, pivot, etc.).
    """

    price: float = 0.0
    label: str = ""  # e.g. "R1", "S1", "Prev Day High"
    level_type: str = (
        ""  # "support", "resistance", "pivot", "supply_zone", "demand_zone"
    )
    strength: str = ""  # "WEAK", "MODERATE", "STRONG", "MAJOR"
    zone_high: float | None = None  # For zones: upper boundary
    zone_low: float | None = None  # For zones: lower boundary

    def to_dict(self) -> dict[str, Any]:
        return {
            "price": self.price,
            "label": self.label,
            "type": self.level_type,
            "strength": self.strength,
        }


@dataclass(frozen=True)
class ProviderStatus:
    """Current status and capabilities of a market data provider."""

    provider: str = ""
    type: str = ""
    status: str = "unknown"
    last_success: str | None = None
    error_message: str = ""
    supported_symbols: list[str] = list
    supported_intervals: list[str] = list

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "type": self.type,
            "status": self.status,
            "last_success": self.last_success,
            "error_message": self.error_message,
            "supported_symbols": list(self.supported_symbols),
            "supported_intervals": list(self.supported_intervals),
        }
