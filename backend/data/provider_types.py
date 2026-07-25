"""
MarketMind AI — Provider Type Definitions

Enums and type aliases for the Market Data Provider layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


class ProviderType(str, Enum):
    """Supported data provider types."""

    YAHOO = "yahoo"
    BROKER = "broker"
    CSV = "csv"
    DATABASE = "database"
    REPLAY = "replay"
    SIMULATION = "simulation"


class ProviderStatus(str, Enum):
    """Health status of a data provider."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"


@dataclass
class ProviderHealth:
    """Response from a provider health check."""

    status: ProviderStatus = ProviderStatus.HEALTHY
    provider_name: str = ""
    provider_type: ProviderType = ProviderType.YAHOO
    last_success: datetime | None = None
    error_message: str = ""
    supported_symbols: int = 0
    supported_intervals: int = 0


@dataclass
class DailyOHLC:
    """Normalized daily OHLC record returned by any provider."""

    date: str  # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "Date": self.date,
            "Open": self.open,
            "High": self.high,
            "Low": self.low,
            "Close": self.close,
            "Volume": self.volume,
        }


@dataclass
class IntradayCandle:
    """Normalized intraday candle returned by any provider."""

    time: str  # ISO-8601 datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass
class DailyReferenceLevels:
    """Daily reference levels (prev day, weekly) computed from provider data."""

    prev_day_high: float
    prev_day_low: float
    prev_day_close: float
    prev_day_open: float
    weekly_high: float
    weekly_low: float
    prev_day_range: float
    prev_day_midpoint: float
    prev_day_vwap: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "prevDayHigh": self.prev_day_high,
            "prevDayLow": self.prev_day_low,
            "prevDayClose": self.prev_day_close,
            "prevDayOpen": self.prev_day_open,
            "weeklyHigh": self.weekly_high,
            "weeklyLow": self.weekly_low,
            "prevDayRange": self.prev_day_range,
            "prevDayMidpoint": self.prev_day_midpoint,
            "prevDayVWAP": self.prev_day_vwap,
        }
