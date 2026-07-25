"""
Score Engine — evaluates setup quality from all lower engines.

Inputs: TradingContext, MTF, SR
Output: score (0-100), score_grade, reasoning
"""

from __future__ import annotations

from typing import Any


class ScoreEngine:
    """Evaluates the overall quality score of the current market setup."""

    WEIGHTS = {
        "trend": 0.25,
        "alignment": 0.20,
        "momentum": 0.15,
        "structure": 0.15,
        "patterns": 0.10,
        "sr_proximity": 0.10,
        "volatility": 0.05,
    }

    @staticmethod
    def evaluate(
        context_snap: dict[str, Any] | None,
        mtf_snap: dict[str, Any] | None,
        sr_snap: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not context_snap:
            return {"score": 0, "grade": "VERY_LOW", "reasoning": ["No context data"]}

        score = 0.0
        max_score = sum(ScoreEngine.WEIGHTS.values())
        reasoning = []

        # Trend contribution
        trend = context_snap.get("trend", "NEUTRAL")
        trend_str = context_snap.get("trend_strength", "WEAK")
        if trend == "BULLISH":
            score += ScoreEngine.WEIGHTS["trend"] * (
                1.0 if trend_str == "STRONG" else 0.6
            )
            reasoning.append(f"Trend: {trend} ({trend_str})")
        elif trend == "BEARISH":
            score += ScoreEngine.WEIGHTS["trend"] * (
                1.0 if trend_str == "STRONG" else 0.6
            )
            reasoning.append(f"Trend: {trend} ({trend_str})")
        else:
            score += ScoreEngine.WEIGHTS["trend"] * 0.2
            reasoning.append("Trend: Neutral")

        # MTF alignment contribution
        if mtf_snap:
            alignment = mtf_snap.get("alignment_level", "MIXED")
            align_score = mtf_snap.get("alignment_score", 0)
            if alignment in ("FULL_ALIGNMENT", "STRONG_ALIGNMENT"):
                score += ScoreEngine.WEIGHTS["alignment"] * (abs(align_score) / 100.0)
                reasoning.append(f"MTF alignment: {alignment} ({align_score})")
            elif alignment == "CONFLICT":
                score += ScoreEngine.WEIGHTS["alignment"] * 0.1
                reasoning.append(f"MTF conflict: {alignment}")
            else:
                score += ScoreEngine.WEIGHTS["alignment"] * 0.4
                reasoning.append(f"MTF: {alignment}")

        # Momentum
        momentum = context_snap.get("momentum", "WEAK")
        if momentum == "STRONG":
            score += ScoreEngine.WEIGHTS["momentum"]
            reasoning.append("Momentum: Strong")
        elif momentum == "MODERATE":
            score += ScoreEngine.WEIGHTS["momentum"] * 0.6
            reasoning.append("Momentum: Moderate")
        else:
            score += ScoreEngine.WEIGHTS["momentum"] * 0.2
            reasoning.append("Momentum: Weak")

        # Structure
        struct = context_snap.get("market_phase", "undefined")
        if struct in ("markup", "markdown"):
            score += ScoreEngine.WEIGHTS["structure"]
            reasoning.append(f"Structure: {struct}")
        elif struct in ("accumulation", "distribution"):
            score += ScoreEngine.WEIGHTS["structure"] * 0.6
            reasoning.append(f"Structure: {struct}")
        else:
            score += ScoreEngine.WEIGHTS["structure"] * 0.3

        # Patterns
        pat_bias = context_snap.get("pattern_bias", "NEUTRAL")
        if pat_bias != "NEUTRAL":
            score += ScoreEngine.WEIGHTS["patterns"]
            reasoning.append(f"Patterns: {pat_bias}")
        else:
            score += ScoreEngine.WEIGHTS["patterns"] * 0.2

        # SR proximity
        if sr_snap:
            nearest_s = sr_snap.get("nearest_support")
            nearest_r = sr_snap.get("nearest_resistance")
            close = context_snap.get("candle_close") or context_snap.get(
                "indicator_snap", {}
            ).get("candle_close")
            if nearest_s and nearest_r and close:
                range_size = nearest_r - nearest_s
                if range_size > 0:
                    pos_in_range = (close - nearest_s) / range_size
                    if 0.3 <= pos_in_range <= 0.7:
                        score += ScoreEngine.WEIGHTS["sr_proximity"]
                        reasoning.append("SR: Mid-range (room to move)")
                    else:
                        score += ScoreEngine.WEIGHTS["sr_proximity"] * 0.4
                        reasoning.append("SR: Near boundary")

        # Volatility
        vol = context_snap.get("volatility_state", "NORMAL")
        if vol == "EXPANDING":
            score += ScoreEngine.WEIGHTS["volatility"] * 0.5
            reasoning.append("Volatility: Expanding (caution)")
        elif vol == "CONTRACTING":
            score += ScoreEngine.WEIGHTS["volatility"] * 0.3
            reasoning.append("Volatility: Contracting (wait)")

        # Normalize
        normalized = (
            min(100, max(0, int((score / max_score) * 100))) if max_score > 0 else 0
        )

        if normalized >= 80:
            grade = "VERY_HIGH"
        elif normalized >= 60:
            grade = "HIGH"
        elif normalized >= 40:
            grade = "MODERATE"
        elif normalized >= 20:
            grade = "LOW"
        else:
            grade = "VERY_LOW"

        return {"score": normalized, "grade": grade, "reasoning": reasoning}
