"""
MarketMind AI — Market Snapshot Model

A complete point-in-time view of a single symbol's market state.
Useful for AI engines, UI updates, and WebSocket broadcasts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from models.candle import Candle, DailyCandle
from models.reference_levels import ReferenceLevels
from models.volume import VolumeData
from models.metadata import MarketSession, ProviderStatus


@dataclass(frozen=True)
class MarketSnapshot:
    """
    Complete market state for a single symbol at a point in time.

    This is the primary model for broadcasting to WebSocket clients
    and for AI engine evaluation.
    """

    symbol: str
    timestamp: str  # ISO-8601
    latest_price: float = 0.0
    latest_candle: Candle | None = None
    daily_candle: DailyCandle | None = None
    reference_levels: ReferenceLevels | None = None
    volume_data: VolumeData | None = None
    session: str = ""  # "PreMarket" / "Opening" / "Mid" / "Closing" / "Closed"
    provider_status: ProviderStatus | None = None
    change_percent: float = 0.0
    day_high: float = 0.0
    day_low: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "latest_price": self.latest_price,
            "session": self.session,
            "change_percent": self.change_percent,
            "day_high": self.day_high,
            "day_low": self.day_low,
        }
        if self.latest_candle:
            d["latest_candle"] = self.latest_candle.to_dict()
        if self.reference_levels:
            d["reference_levels"] = self.reference_levels.to_dict()
        if self.volume_data:
            d["volume_data"] = self.volume_data.to_dict()
        if self.provider_status:
            d["provider_status"] = self.provider_status.to_dict()
        return d
