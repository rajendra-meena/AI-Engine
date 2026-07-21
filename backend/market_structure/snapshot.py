"""
MarketMind AI — Market Structure Snapshot

Immutable snapshot of all market structure values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MarketStructureSnapshot:
    symbol: str = ""
    interval: str = ""
    timestamp: str = ""

    # Trend
    trend: str = "RANGING"
    trend_strength: str = "WEAK"
    trend_age: int = 0
    last_hh: float | None = None
    last_hl: float | None = None
    last_lh: float | None = None
    last_ll: float | None = None

    # Swings
    current_swing_high: float | None = None
    current_swing_low: float | None = None
    total_swings: int = 0

    # Structure
    market_phase: str = "undefined"
    last_bos: dict | None = None
    last_choch: dict | None = None
    bos_count: int = 0
    choch_count: int = 0
    impulse_active: bool = False
    pullback_active: bool = False
    consolidation_bars: int = 0

    # Liquidity
    equal_highs: list[float] | None = None
    equal_lows: list[float] | None = None
    liquidity_sweeps: int = 0

    # Validity
    valid_structure: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "timestamp": self.timestamp,
            "trend": self.trend,
            "trend_strength": self.trend_strength,
            "trend_age": self.trend_age,
            "last_hh": self.last_hh,
            "last_hl": self.last_hl,
            "last_lh": self.last_lh,
            "last_ll": self.last_ll,
            "current_swing_high": self.current_swing_high,
            "current_swing_low": self.current_swing_low,
            "market_phase": self.market_phase,
            "bos_count": self.bos_count,
            "choch_count": self.choch_count,
            "impulse_active": self.impulse_active,
            "pullback_active": self.pullback_active,
            "consolidation_bars": self.consolidation_bars,
            "liquidity_sweeps": self.liquidity_sweeps,
            "valid_structure": self.valid_structure,
        }
