"""Market Condition — determines overall market state from MTF data."""

from __future__ import annotations

from typing import Any


class ConditionAnalyzer:
    """Determines market condition from MTF alignment."""

    @staticmethod
    def evaluate(alignment: dict[str, Any], contexts: dict[str, dict[str, Any]]) -> str:
        level = alignment.get("level", "MIXED")
        score = alignment.get("score", 0)
        htf = alignment.get("htf_bias", "NEUTRAL")

        contexts_list = [c for c in contexts.values() if c]
        volatility_states = [c.get("volatility_state", "") for c in contexts_list]
        modes = [c.get("recommended_mode", "") for c in contexts_list]

        has_expansion = "EXPANDING" in volatility_states
        has_contraction = "CONTRACTING" in volatility_states

        # Trending
        if level in ("FULL_ALIGNMENT", "STRONG_ALIGNMENT") and abs(score) > 30:
            if has_expansion:
                return "BREAKOUT"
            return "TRENDING"

        # Pullback
        if level == "PARTIAL_ALIGNMENT":
            if score == 0:
                return "RANGE"
            return "PULLBACK"

        # Reversal
        if level == "REVERSAL_SETUP":
            return "REVERSAL"

        # Compression
        if has_contraction:
            return "COMPRESSION"

        # Range
        if "RANGE" in modes:
            return "RANGE"

        return "MIXED"
