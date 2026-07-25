"""
Confidence Engine — evaluates data reliability and engine agreement.

Inputs: Indicator readiness, pattern count, structure validity, MTF alignment
Output: confidence (0-100), grade, reasoning
"""

from __future__ import annotations

from typing import Any


class ConfidenceEngine:
    """Evaluates how much we can trust the current data and analysis."""

    @staticmethod
    def evaluate(
        context_snap: dict[str, Any] | None,
        mtf_snap: dict[str, Any] | None,
        structure_snap: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not context_snap:
            return {
                "confidence": 0,
                "grade": "VERY_LOW",
                "reasoning": ["No context data"],
            }

        score = 50.0  # base
        reasoning = []

        # Context confidence
        ctx_conf = context_snap.get("confidence", 0) or 0
        score += (ctx_conf - 50) * 0.3
        if ctx_conf >= 70:
            reasoning.append(f"Context confidence: {ctx_conf}%")
        elif ctx_conf < 40:
            reasoning.append(f"Low context confidence: {ctx_conf}%")

        # MTF alignment boosts confidence
        if mtf_snap:
            align = mtf_snap.get("alignment_level", "MIXED")
            if align in ("FULL_ALIGNMENT", "STRONG_ALIGNMENT"):
                score += 15
                reasoning.append(f"MTF {align} boosts confidence")
            elif align == "CONFLICT":
                score -= 15
                reasoning.append(f"MTF conflict reduces confidence")

        # Structure validity
        if structure_snap:
            valid = structure_snap.get("valid_structure", False)
            if valid:
                score += 10
                reasoning.append("Valid market structure")
            else:
                score -= 10
                reasoning.append("Invalid market structure")

        # Overall bias vs trend alignment
        ob = context_snap.get("overall_bias", "NEUTRAL")
        trend = context_snap.get("trend", "NEUTRAL")
        if ob == trend:
            score += 10
            reasoning.append(f"Bias aligns with trend ({ob})")
        else:
            score -= 5
            reasoning.append(f"Bias ({ob}) vs trend ({trend}) conflict")

        # Normalize
        confidence = max(0, min(100, int(score)))

        if confidence >= 80:
            grade = "VERY_HIGH"
        elif confidence >= 60:
            grade = "HIGH"
        elif confidence >= 40:
            grade = "MODERATE"
        elif confidence >= 20:
            grade = "LOW"
        else:
            grade = "VERY_LOW"

        return {"confidence": confidence, "grade": grade, "reasoning": reasoning}
