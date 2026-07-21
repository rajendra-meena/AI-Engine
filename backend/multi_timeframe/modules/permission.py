"""Trading Permission — determines allowable trading actions from MTF data."""

from __future__ import annotations

from typing import Any


class PermissionAnalyzer:
    """Evaluates trading permission from alignment, condition, and HTF bias."""

    @staticmethod
    def evaluate(alignment: dict[str, Any], condition: str, contexts: dict[str, dict[str, Any]]) -> dict[str, Any]:
        score = alignment.get("score", 0)
        level = alignment.get("level", "MIXED")
        htf_bias = alignment.get("htf_bias", "NEUTRAL")
        ltf_bias = alignment.get("ltf_bias", "NEUTRAL")

        warnings = []
        permission = "WAIT"

        if level in ("FULL_ALIGNMENT", "STRONG_ALIGNMENT") and abs(score) > 30:
            if htf_bias == "BULLISH":
                permission = "ALLOW_LONG"
            elif htf_bias == "BEARISH":
                permission = "ALLOW_SHORT"
            else:
                permission = "WAIT"
        elif level == "PARTIAL_ALIGNMENT" and abs(score) > 15:
            if score > 0:
                permission = "ALLOW_LONG"
            elif score < 0:
                permission = "ALLOW_SHORT"
            else:
                permission = "WAIT"
        elif level == "REVERSAL_SETUP":
            permission = "WAIT"
            warnings.append("Possible reversal setup — wait for confirmation")
        elif level == "CONFLICT":
            permission = "NO_TRADE"
            warnings.append("Timeframe conflict — no clear direction")
        else:
            permission = "WAIT"

        # Additional warnings
        if htf_bias != ltf_bias and ltf_bias != "NEUTRAL":
            warnings.append(f"LTF ({ltf_bias}) against HTF ({htf_bias})")

        # Check confidence
        confidences = [c.get("confidence", 0) or 0 for c in contexts.values() if c]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        if avg_conf < 40:
            warnings.append("Low confidence across timeframes")

        return {
            "permission": permission,
            "htf_bias": htf_bias,
            "avg_confidence": int(avg_conf),
            "warnings": warnings,
        }
