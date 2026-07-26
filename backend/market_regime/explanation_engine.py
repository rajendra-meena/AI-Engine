"""
Regime Explanation Engine — generates human-readable explanations for regime detections.
"""

from __future__ import annotations

from typing import Any

from market_regime.snapshot import RegimeSnapshot, RegimeExplanation
from market_regime.strategy_router import REGIME_STRATEGY_MAP


FACTOR_DESCRIPTIONS: dict[str, str] = {
    "ema_bullish_alignment": "EMA Bullish Alignment (9>20>50)",
    "ema_bearish_alignment": "EMA Bearish Alignment (9<20<50)",
    "vwap_support": "Price Above VWAP (Support)",
    "vwap_resistance": "Price Below VWAP (Resistance)",
    "strong_trend_strength": "Strong Trend Strength",
    "strong_volume": "Above Average Volume",
    "high_volume": "High Volume",
    "volume_spike": "Volume Spike",
    "low_volume": "Below Average Volume",
    "bos_detected": "Break of Structure Detected",
    "choch_detected": "Change of Character Detected",
    "mtf_breakout_condition": "MTF Breakout Condition",
    "mtf_aligned": "MTF Aligned",
    "weak_mtf_alignment": "Weak MTF Alignment",
    "liquidity_sweep": "Liquidity Sweep",
    "near_vwap": "Price Near VWAP",
    "volatility_expanding": "Volatility Expanding",
    "volatility_contracting": "Volatility Contracting",
    "opening_session": "Opening Session (First 30-60 min)",
    "closing_session": "Closing Session (Last 30-60 min)",
    "no_bos": "No Break of Structure",
    "no_structure": "No Clear Structure",
    "no_structural_moves": "No Structural Price Moves",
    "emas_tight": "EMAs Tight (Low Separation)",
}


class RegimeExplanationEngine:
    """Generates human-readable regime explanations."""

    @staticmethod
    def explain(
        regime_snapshot: RegimeSnapshot | None,
        strategy_rec: dict[str, Any] | None = None,
    ) -> RegimeExplanation:
        """Generate full explanation from regime data."""
        if not regime_snapshot:
            return RegimeExplanation(
                regime="UNKNOWN",
                confidence=0,
                primary_reason="No regime data available. Market conditions cannot be classified.",
                supporting_evidence=(),
                strategy_reasoning="No strategy recommendation available.",
                market_conditions_summary="Unable to assess market conditions.",
            )

        regime_display = regime_snapshot.regime.replace("_", " ").title()
        primary = (
            f"Current Market: {regime_display}. "
            f"Confidence: {regime_snapshot.confidence}%. "
            f"Stability: {regime_snapshot.stability_score:.0%}."
        )

        evidence: list[str] = []
        for factor in regime_snapshot.supporting_factors:
            desc = FACTOR_DESCRIPTIONS.get(factor)
            if desc:
                evidence.append(desc)
            elif factor.startswith("adx_"):
                evidence.append(f"ADX {factor.split('_')[1]}")
            elif factor.startswith("rsi_"):
                parts = factor.split("_")
                if len(parts) >= 3:
                    evidence.append(f"RSI {parts[1]} ({parts[2]})")
            elif factor.startswith("high_atr_"):
                evidence.append(f"ATR {factor.split('_')[2]} — High Volatility")
            elif factor.startswith("far_from_"):
                evidence.append(f"Price Far From {factor.split('_')[2].upper()}")
            elif "_bos" in factor:
                evidence.append(f"{factor.split('_')[0]} BOS Events")
            elif "_choch" in factor:
                evidence.append(f"{factor.split('_')[0]} CHoCH Events")
            else:
                evidence.append(factor.replace("_", " ").title())

        if not evidence:
            evidence.append(f"Market conditions indicate {regime_display.lower()}")

        strategy_text = ""
        rec_strat = ""
        avoid: list[str] = []
        if strategy_rec:
            rec_strat = strategy_rec.get("primary", "none")
            rec_conf = strategy_rec.get("confidence", 0)
            strategy_text = (
                f"Recommended Strategy: {rec_strat.replace('_', ' ').title()}. "
                f"Secondary: {strategy_rec.get('secondary', 'none').replace('_', ' ').title()}. "
                f"Strategy Confidence: {rec_conf}%."
            )
            avoid = strategy_rec.get("avoid", [])

        market_summary = (
            f"Market is in a {regime_display.lower()} phase "
            f"with {regime_snapshot.confidence}% detection confidence. "
            f"The regime has been active for {regime_snapshot.regime_age_bars} bars "
            f"with {regime_snapshot.stability_score:.0%} stability."
        )

        return RegimeExplanation(
            regime=regime_snapshot.regime,
            confidence=regime_snapshot.confidence,
            primary_reason=primary,
            supporting_evidence=tuple(evidence),
            recommended_strategy=rec_strat,
            avoid_strategies=tuple(avoid),
            strategy_reasoning=strategy_text,
            market_conditions_summary=market_summary,
        )
