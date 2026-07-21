"""
MarketMind AI — Candle Models

Standardized OHLCV candle models for intraday and daily data.
These are the primary data units exchanged between modules.

Backward compatibility:
    Candle.to_dict()     → matches existing intraday API format
    DailyCandle.to_dict() → matches existing daily API format
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Candle:
    """
    An intraday OHLCV candle.

    Immutable. Use the helper methods to derive values.

    Fields match the existing {time, open, high, low, close, volume} format.
    """
    symbol: str = ""
    interval: str = ""
    time: str = ""                  # ISO-8601 datetime string
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    provider: str = "yahoo"
    is_closed: bool = True          # False if the candle is still forming

    @property
    def range(self) -> float:
        """Candle range (high - low)."""
        return self.high - self.low

    @property
    def body(self) -> float:
        """Candle body (abs(close - open))."""
        return abs(self.close - self.open)

    @property
    def is_bullish(self) -> bool:
        """True if close >= open."""
        return self.close >= self.open

    @property
    def upper_wick(self) -> float:
        """Length of the upper wick."""
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        """Length of the lower wick."""
        return min(self.open, self.close) - self.low

    @property
    def body_percent(self) -> float:
        """Body as a percentage of the total range. 0 if range is 0."""
        if self.range == 0:
            return 0.0
        return (self.body / self.range) * 100.0

    # ── Serialization (matching existing intraday format) ──

    def to_dict(self) -> dict[str, Any]:
        """Returns dict matching the existing intraday candle format."""
        return {
            "time": self.time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }

    def to_dict_full(self) -> dict[str, Any]:
        """Returns dict with all fields (including symbol/interval)."""
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "time": self.time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "provider": self.provider,
            "is_closed": self.is_closed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Candle:
        return cls(
            symbol=data.get("symbol", ""),
            interval=data.get("interval", ""),
            time=str(data.get("time", "")),
            open=float(data.get("open", 0)),
            high=float(data.get("high", 0)),
            low=float(data.get("low", 0)),
            close=float(data.get("close", 0)),
            volume=float(data.get("volume", 0)),
            provider=data.get("provider", "yahoo"),
            is_closed=bool(data.get("is_closed", True)),
        )


@dataclass(frozen=True)
class DailyCandle:
    """
    A daily OHLC record.

    Fields match the existing {Date, Open, High, Low, Close, Volume} format.
    """
    symbol: str = ""
    date: str = ""                  # YYYY-MM-DD
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    provider: str = "yahoo"

    @property
    def range(self) -> float:
        return self.high - self.low

    # ── Serialization (matching existing daily format) ──

    def to_dict(self) -> dict[str, Any]:
        """Returns dict matching the existing daily API format."""
        return {
            "Date": self.date,
            "Open": self.open,
            "High": self.high,
            "Low": self.low,
            "Close": self.close,
            "Volume": self.volume,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DailyCandle:
        return cls(
            symbol=data.get("symbol", ""),
            date=str(data.get("Date", data.get("date", ""))),
            open=float(data.get("Open", data.get("open", 0))),
            high=float(data.get("High", data.get("high", 0))),
            low=float(data.get("Low", data.get("low", 0))),
            close=float(data.get("Close", data.get("close", 0))),
            volume=float(data.get("Volume", data.get("volume", 0))),
            provider=data.get("provider", "yahoo"),
        )
