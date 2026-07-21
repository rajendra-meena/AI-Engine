"""
MarketMind AI — Tick Model

Represents a single price tick from the market.
Primary use: real-time streaming (future Tick Engine).

The bid/ask fields are placeholders for broker integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Tick:
    """
    A single market price tick.

    Immutable to ensure consistency when passed between modules.
    """
    symbol: str
    price: float
    timestamp: datetime
    volume: float = 0.0
    bid: float | None = None      # Future: broker bid
    ask: float | None = None      # Future: broker ask
    provider: str = "yahoo"
    exchange: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(timespec="milliseconds"),
            "volume": self.volume,
            "bid": self.bid,
            "ask": self.ask,
            "provider": self.provider,
            "exchange": self.exchange,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tick:
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            symbol=data["symbol"],
            price=float(data["price"]),
            timestamp=ts or datetime.utcnow(),
            volume=float(data.get("volume", 0)),
            bid=float(data["bid"]) if data.get("bid") is not None else None,
            ask=float(data["ask"]) if data.get("ask") is not None else None,
            provider=data.get("provider", "yahoo"),
            exchange=data.get("exchange", ""),
        )
