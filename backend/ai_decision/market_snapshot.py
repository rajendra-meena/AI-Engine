"""
Unified AI Market Snapshot — single normalized object representing
the complete current market state for AI decision-making.

Aggregates data from: CandleEngine, IndicatorEngine, MarketStructureEngine,
PatternEngine, TradingContextEngine, MTFEngine, SREngine, and stream health.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class AIMarketSnapshot:
    """Canonical market intelligence snapshot for AI decision-making."""
    # Identity
    symbol: str = ""
    timestamp: str = ""
    last_price: float | None = None
    volume: float | None = None

    # Market state
    trend: str | None = None
    momentum: str | None = None
    volatility: str | None = None
    market_regime: str | None = None
    session: str | None = None

    # Multi-timeframe
    mtf_alignment: str | None = None
    mtf_score: int | None = None
    mtf_bias: str | None = None

    # Indicators
    ema_9: float | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    atr_14: float | None = None
    vwap: float | None = None
    adx_14: float | None = None
    supertrend_trend: str | None = None
    bb_upper: float | None = None
    bb_lower: float | None = None

    # Market structure
    market_phase: str | None = None
    trend_strength: str | None = None
    bos_count: int | None = None
    choch_count: int | None = None
    valid_structure: bool | None = None
    swing_high: float | None = None
    swing_low: float | None = None

    # Patterns
    strongest_pattern: str | None = None
    pattern_direction: str | None = None
    pattern_count: int | None = None
    pattern_bias: str | None = None

    # Support/Resistance
    nearest_support: float | None = None
    nearest_resistance: float | None = None
    support_distance_pct: float | None = None
    resistance_distance_pct: float | None = None
    breakout_state: str | None = None

    # Institutional context
    institutional_bias: str | None = None
    trading_permission: str | None = None
    overall_bias: str | None = None

    # Context confidence
    context_confidence: int | None = None

    # Data health
    data_freshness: str = "unknown"  # live, degraded, stale
    stream_state: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp or datetime.now(timezone.utc).isoformat(),
            "last_price": self.last_price,
            "volume": self.volume,
            "trend": self.trend,
            "momentum": self.momentum,
            "volatility": self.volatility,
            "market_regime": self.market_regime,
            "mtf_alignment": self.mtf_alignment,
            "mtf_score": self.mtf_score,
            "mtf_bias": self.mtf_bias,
            "indicators": {
                "ema_9": self.ema_9,
                "ema_20": self.ema_20,
                "ema_50": self.ema_50,
                "ema_200": self.ema_200,
                "sma_20": self.sma_20,
                "sma_50": self.sma_50,
                "rsi_14": self.rsi_14,
                "macd": self.macd,
                "macd_signal": self.macd_signal,
                "macd_histogram": self.macd_histogram,
                "atr_14": self.atr_14,
                "vwap": self.vwap,
                "adx_14": self.adx_14,
                "supertrend_trend": self.supertrend_trend,
                "bb_upper": self.bb_upper,
                "bb_lower": self.bb_lower,
            },
            "market_structure": {
                "market_phase": self.market_phase,
                "trend_strength": self.trend_strength,
                "bos_count": self.bos_count,
                "choch_count": self.choch_count,
                "valid_structure": self.valid_structure,
                "swing_high": self.swing_high,
                "swing_low": self.swing_low,
            },
            "patterns": {
                "strongest": self.strongest_pattern,
                "direction": self.pattern_direction,
                "count": self.pattern_count,
                "bias": self.pattern_bias,
            },
            "support_resistance": {
                "nearest_support": self.nearest_support,
                "nearest_resistance": self.nearest_resistance,
                "support_distance_pct": self.support_distance_pct,
                "resistance_distance_pct": self.resistance_distance_pct,
                "breakout_state": self.breakout_state,
            },
            "institutional_context": {
                "institutional_bias": self.institutional_bias,
                "trading_permission": self.trading_permission,
                "overall_bias": self.overall_bias,
                "context_confidence": self.context_confidence,
            },
            "data_freshness": self.data_freshness,
            "stream_state": self.stream_state,
        }
