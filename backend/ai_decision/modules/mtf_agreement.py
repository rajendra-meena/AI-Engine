"""
Multi-Timeframe Agreement Engine — computes % agreement across timeframes.

Analyzes 1m/3m/5m/15m/1H to determine what fraction agree on direction.
"""

from __future__ import annotations

from typing import Any


# Hierarchy from highest to lowest
TF_HIERARCHY = ["60m", "30m", "15m", "10m", "5m", "3m", "2m", "1m"]
TF_WEIGHTS = {"60m": 0.30, "30m": 0.20, "15m": 0.20, "10m": 0.10, "5m": 0.10, "3m": 0.05, "2m": 0.03, "1m": 0.02}

TARGET_TFS = ["1m", "3m", "5m", "15m", "1H"]
TARGET_WEIGHTS = {"1m": 0.10, "3m": 0.15, "5m": 0.20, "15m": 0.25, "1H": 0.30}


class MultiTFAgreement:
    """Computes agreement percentage across timeframes."""

    @staticmethod
    def evaluate(mtf_snap: dict[str, Any] | None) -> dict[str, Any]:
        """Compute MTF agreement percentage and breakdown."""
        if not mtf_snap:
            return {
                "agreement_percent": 0,
                "weighted_agreement": 0,
                "breakdown": [],
                "conflicts_found": [],
                "status": "NO_DATA",
            }

        timeframes = mtf_snap.get("timeframes", {})
        if not timeframes or not isinstance(timeframes, dict):
            return {
                "agreement_percent": 0,
                "weighted_agreement": 0,
                "breakdown": [],
                "conflicts_found": [],
                "status": "NO_DATA",
            }

        # Determine primary direction bias
        overall_bias = mtf_snap.get("institutional_bias", mtf_snap.get("bias", "NEUTRAL"))
        if not isinstance(overall_bias, str):
            overall_bias = "NEUTRAL"
        overall_bias = overall_bias.upper()

        # If no clear bias, compute from strongest TF
        if overall_bias in ("NEUTRAL", "NONE", ""):
            overall_bias = MultiTFAgreement._compute_primary_bias(timeframes)

        breakdown: list[dict[str, Any]] = []
        agreeing_weight = 0.0
        total_weight = 0.0
        conflicts: list[dict[str, Any]] = []

        for tf in TARGET_TFS:
            # Try exact match, then case-insensitive
            tf_data = timeframes.get(tf) or timeframes.get(tf.lower()) or timeframes.get(tf.upper())
            if tf_data is None:
                # Try mapping 1H→60m
                mapped = {"1H": "60m", "1h": "60m", "1h": "60m"}.get(tf)
                if mapped:
                    tf_data = timeframes.get(mapped)
            if tf_data is None:
                continue

            bias = tf_data.get("bias", tf_data.get("direction", "NEUTRAL"))
            if not isinstance(bias, str):
                bias = "NEUTRAL"
            bias = bias.upper()

            weight = TARGET_WEIGHTS.get(tf, 0.10)
            total_weight += weight

            agrees = MultiTFAgreement._bias_agrees(bias, overall_bias)
            if agrees:
                agreeing_weight += weight

            breakdown.append({
                "timeframe": tf,
                "bias": bias,
                "agrees": agrees,
                "weight": weight,
            })

            if not agrees and bias not in ("NEUTRAL", "NONE"):
                conflicts.append({
                    "type": "tf_conflict",
                    "timeframe": tf,
                    "bias": bias,
                    "against": overall_bias,
                    "severity": "medium" if weight >= 0.20 else "low",
                })

        if total_weight == 0:
            return {
                "agreement_percent": 0,
                "weighted_agreement": 0,
                "breakdown": breakdown,
                "conflicts_found": conflicts,
                "status": "NO_DATA",
            }

        agreement_pct = round((agreeing_weight / total_weight) * 100)
        weighted_agreement = round(agreeing_weight * 100)

        if agreement_pct >= 80:
            status = "STRONG"
        elif agreement_pct >= 60:
            status = "MODERATE"
        elif agreement_pct >= 40:
            status = "WEAK"
        else:
            status = "CONFLICT"

        return {
            "agreement_percent": agreement_pct,
            "weighted_agreement": weighted_agreement,
            "breakdown": breakdown,
            "conflicts_found": conflicts,
            "status": status,
        }

    @staticmethod
    def _bias_agrees(bias: str, primary: str) -> bool:
        """Check if a TF bias agrees with the primary direction."""
        if bias == primary:
            return True
        if primary in ("BUY", "BULLISH") and bias in ("BUY", "BULLISH"):
            return True
        if primary in ("SELL", "BEARISH") and bias in ("SELL", "BEARISH"):
            return True
        if bias == "NEUTRAL":
            return False
        return False

    @staticmethod
    def _compute_primary_bias(timeframes: dict[str, Any]) -> str:
        """Vote across timeframes to determine primary bias."""
        bullish_weight = 0.0
        bearish_weight = 0.0
        for tf_name, tf_data in timeframes.items():
            if not isinstance(tf_data, dict):
                continue
            bias = tf_data.get("bias", tf_data.get("direction", "NEUTRAL"))
            if not isinstance(bias, str):
                continue
            bias = bias.upper()
            weight = TF_WEIGHTS.get(tf_name, 0.05)
            if bias in ("BUY", "BULLISH"):
                bullish_weight += weight
            elif bias in ("SELL", "BEARISH"):
                bearish_weight += weight
        if bullish_weight > bearish_weight:
            return "BULLISH"
        elif bearish_weight > bullish_weight:
            return "BEARISH"
        return "NEUTRAL"
