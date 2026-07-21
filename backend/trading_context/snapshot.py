"""TradingContextSnapshot — immutable unified institutional market view."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TradingContextSnapshot:
    symbol: str = ""
    interval: str = ""
    timestamp: str = ""

    # Trend
    trend: str = "NEUTRAL"
    trend_strength: str = "WEAK"

    # Momentum
    momentum: str = "WEAK"
    momentum_strength: str = "WEAK"

    # Volatility
    volatility: str = "NORMAL"
    volatility_state: str = "NORMAL"

    # Liquidity
    liquidity_state: str = "BALANCED"

    # Market
    market_phase: str = "undefined"
    session: str = ""

    # Biases
    pattern_bias: str = "NEUTRAL"
    structure_bias: str = "NEUTRAL"
    indicator_bias: str = "NEUTRAL"
    overall_bias: str = "NEUTRAL"

    # Strength
    overall_strength: str = "WEAK"
    confidence: int = 0

    # Risk & Mode
    risk_level: str = "MEDIUM"
    recommended_mode: str = "WAIT"

    # Warnings
    warnings: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "timestamp": self.timestamp,
            "trend": self.trend,
            "trend_strength": self.trend_strength,
            "momentum": self.momentum,
            "momentum_strength": self.momentum_strength,
            "volatility": self.volatility,
            "volatility_state": self.volatility_state,
            "liquidity_state": self.liquidity_state,
            "market_phase": self.market_phase,
            "session": self.session,
            "pattern_bias": self.pattern_bias,
            "structure_bias": self.structure_bias,
            "indicator_bias": self.indicator_bias,
            "overall_bias": self.overall_bias,
            "overall_strength": self.overall_strength,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "recommended_mode": self.recommended_mode,
            "warnings": self.warnings or [],
        }
