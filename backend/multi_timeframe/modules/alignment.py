"""Alignment — computes alignment level and score across timeframes."""

from __future__ import annotations

from typing import Any

from multi_timeframe.config import HIERARCHY, WEIGHTS, BIAS_SCORE_MAP


class AlignmentAnalyzer:
    """Evaluates alignment between timeframes."""

    @staticmethod
    def evaluate(contexts: dict[str, dict[str, Any]]) -> dict[str, Any]:
        available = {tf: c for tf, c in contexts.items() if c is not None}
        if not available:
            return {"level": "MIXED", "score": 0.0, "description": "No timeframe data"}

        # Weighted score
        total_weight = 0.0
        weighted_score = 0.0
        biases = {}
        for tf in HIERARCHY:
            ctx = available.get(tf)
            if ctx:
                w = WEIGHTS.get(tf, 0)
                bias = ctx.get("overall_bias", "NEUTRAL")
                biases[tf] = bias
                weighted_score += BIAS_SCORE_MAP.get(bias, 0) * w
                total_weight += w

        aligned_score = round(weighted_score / total_weight, 3) if total_weight > 0 else 0.0

        # Level classification
        abs_score = abs(aligned_score)
        if abs_score > 0.8:
            level = "FULL_ALIGNMENT"
        elif abs_score > 0.5:
            level = "STRONG_ALIGNMENT"
        elif abs_score > 0.2:
            level = "PARTIAL_ALIGNMENT"
        elif abs_score > 0.05:
            level = "MIXED"
        else:
            level = "CONFLICT"

        # Check HTF vs LTF conflict
        high_tf_biases = [biases[tf] for tf in HIERARCHY[:3] if tf in biases]
        low_tf_biases = [biases[tf] for tf in HIERARCHY[-3:] if tf in biases]
        htf_main = max(set(high_tf_biases), key=high_tf_biases.count) if high_tf_biases else "NEUTRAL"
        ltf_main = max(set(low_tf_biases), key=low_tf_biases.count) if low_tf_biases else "NEUTRAL"

        if htf_main != ltf_main and htf_main != "NEUTRAL" and ltf_main != "NEUTRAL":
            if htf_main != aligned_score > 0:
                level = "REVERSAL_SETUP"

        return {
            "level": level,
            "score": int(aligned_score * 100),
            "htf_bias": htf_main,
            "ltf_bias": ltf_main,
            "available_tfs": list(available.keys()),
            "biases": biases,
        }
