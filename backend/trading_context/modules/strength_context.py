"""Strength Context — weighted scoring combining all dimensions."""

from typing import Any


class StrengthContext:
    """
    Computes overall strength, bias, and confidence using weighted scoring.

    Weights:
      Trend:       35%
      Structure:   25%
      Indicators:  20%
      Patterns:    10%
      Momentum:    10%
    """

    WEIGHTS = {"trend": 0.35, "structure": 0.25, "indicators": 0.20, "patterns": 0.10, "momentum": 0.10}
    BIAS_MAP = {"BULLISH": 1.0, "NEUTRAL": 0.0, "BEARISH": -1.0}

    @staticmethod
    def evaluate(trend: dict[str, Any],
                 momentum: dict[str, Any],
                 structure: dict[str, Any] | None,
                 patterns: dict[str, Any] | None) -> dict[str, Any]:
        score = 0.0
        max_score = sum(StrengthContext.WEIGHTS.values())
        warnings = []

        # Trend contribution
        trend_bias = StrengthContext.BIAS_MAP.get(trend.get("bias", "NEUTRAL"), 0)
        trend_weight = StrengthContext.WEIGHTS["trend"]
        score += trend_bias * trend_weight

        if trend.get("strength") == "WEAK":
            warnings.append("Weak trend")

        # Momentum contribution
        mom_bias = StrengthContext.BIAS_MAP.get(momentum.get("bias", "NEUTRAL"), 0)
        score += mom_bias * StrengthContext.WEIGHTS["momentum"]

        if momentum.get("state") == "WEAK":
            warnings.append("Weak momentum")

        # Structure contribution
        if structure:
            struct_trend = structure.get("trend", "RANGING")
            if struct_trend == "UPTREND":
                score += 1.0 * StrengthContext.WEIGHTS["structure"]
            elif struct_trend == "DOWNTREND":
                score -= 1.0 * StrengthContext.WEIGHTS["structure"]

            if not structure.get("valid_structure", False):
                warnings.append("No valid structure")

        # Pattern contribution
        if patterns:
            pat_dir = patterns.get("pattern_direction", "neutral")
            pat_count = patterns.get("total_count", 0)
            if pat_dir == "bullish":
                score += 1.0 * StrengthContext.WEIGHTS["patterns"]
            elif pat_dir == "bearish":
                score -= 1.0 * StrengthContext.WEIGHTS["patterns"]
            if pat_count == 0:
                warnings.append("No patterns detected")

        # Indicators contribution
        score += trend_bias * StrengthContext.WEIGHTS["indicators"]

        # Normalize to -1.0 to 1.0
        if max_score > 0:
            score = max(-1.0, min(1.0, score / max_score))

        # Bias
        if score > 0.2:
            bias = "BULLISH"
        elif score < -0.2:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        # Strength
        abs_score = abs(score)
        if abs_score > 0.7:
            strength = "VERY_STRONG" if abs_score > 0.85 else "STRONG"
        elif abs_score > 0.3:
            strength = "NORMAL"
        else:
            strength = "WEAK"

        # Confidence (0-100) based on agreement
        confidence = int((abs_score * 0.7 + 0.3) * 100)
        confidence = max(0, min(100, confidence))

        # Risk level
        num_warnings = len(warnings)
        if num_warnings >= 3:
            risk = "VERY_HIGH"
        elif num_warnings >= 2:
            risk = "HIGH"
        elif num_warnings >= 1:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        # Recommended mode
        if strength in ("STRONG", "VERY_STRONG") and bias != "NEUTRAL":
            mode = "TREND_FOLLOWING"
        elif any("breakout" in w for w in warnings):
            mode = "BREAKOUT"
        elif strength == "WEAK":
            mode = "WAIT"
        elif volatility := momentum.get("state") == "HIGH":
            mode = "SCALPING"
        else:
            mode = "RANGE"

        return {
            "overall_bias": bias,
            "overall_strength": strength,
            "confidence": confidence,
            "score": round(score, 3),
            "risk_level": risk,
            "recommended_mode": mode,
            "warnings": warnings,
        }
