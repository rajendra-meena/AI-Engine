"""
Adaptive Confidence Modifier — adjusts AI confidence based on detected market regime.
Only affects AI confidence, never bypasses approval rules.
"""

from __future__ import annotations

from typing import Any


REGIME_CONFIDENCE_ADJUSTMENTS: dict[str, int] = {
    "STRONG_BULL_TREND": 8,
    "STRONG_BEAR_TREND": 8,
    "WEAK_BULL_TREND": 3,
    "WEAK_BEAR_TREND": 3,
    "SIDEWAYS_RANGE": -5,
    "HIGH_VOLATILITY": -10,
    "LOW_VOLATILITY": -15,
    "BREAKOUT": 5,
    "FAKE_BREAKOUT": -20,
    "MEAN_REVERSION": -5,
    "NEWS_DRIVEN": -50,
    "OPENING_AUCTION": 0,
    "CLOSING_SESSION": 0,
    "ILLIQUID_MARKET": -35,
}


class RegimeConfidenceModifier:
    """Adjusts confidence based on detected market regime."""

    @staticmethod
    def adjust(
        base_confidence: int,
        regime: str | None,
        regime_confidence: int = 50,
    ) -> dict[str, Any]:
        """
        Apply regime-based confidence adjustment.

        The adjustment is scaled by regime_confidence/100 so that
        a low-confidence regime detection has a proportional impact.
        """
        if not regime:
            return {
                "adjusted_confidence": base_confidence,
                "original_confidence": base_confidence,
                "adjustments": [],
                "total_adjustment": 0,
            }

        raw = REGIME_CONFIDENCE_ADJUSTMENTS.get(regime, 0)
        scale = max(0, min(100, regime_confidence)) / 100.0
        scaled = int(round(raw * scale))

        adjusted = max(0, min(100, base_confidence + scaled))

        return {
            "adjusted_confidence": adjusted,
            "original_confidence": base_confidence,
            "adjustments": [{
                "factor": "regime",
                "regime": regime,
                "impact": scaled,
                "reason": f"Market regime '{regime}' adjusted confidence by {scaled:+d}%",
            }],
            "total_adjustment": scaled,
        }
