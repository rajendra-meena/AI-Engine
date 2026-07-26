"""
Confidence Calibration Engine — compares predicted confidence with actual outcomes.

Computes calibration error, reliability curve, confidence bias.
"""

from __future__ import annotations

import math
from typing import Any


class ConfidenceCalibrationEngine:
    """Analyzes how well AI confidence matches actual success rates."""

    @staticmethod
    def compute_reliability_curve(
        predictions: list[dict[str, Any]],
        outcomes: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Build reliability curve across 10 confidence deciles."""
        deciles = [{"min": i * 10, "max": (i + 1) * 10, "avg_confidence": 0.0,
                     "actual_accuracy": 0.0, "calibration_error": 0.0, "count": 0}
                    for i in range(10)]

        for p in predictions:
            conf = p.get("confidence")
            if conf is None or not isinstance(conf, (int, float)):
                continue
            idx = min(9, max(0, int(conf // 10)))
            deciles[idx]["count"] += 1
            deciles[idx]["avg_confidence"] += conf

            outcome = (outcomes or {}).get(p.get("id") or p.get("prediction_id", ""))
            if outcome:
                actual_return = outcome.get("actual_return", 0)
                if actual_return and isinstance(actual_return, (int, float)):
                    if actual_return > 0:
                        deciles[idx]["actual_accuracy"] += 1

        for d in deciles:
            if d["count"] > 0:
                d["avg_confidence"] = round(d["avg_confidence"] / d["count"], 1)
                accuracy = (d["actual_accuracy"] / d["count"]) * 100
                d["actual_accuracy"] = round(accuracy, 1)
                d["calibration_error"] = round(abs(d["avg_confidence"] - accuracy), 1)
            else:
                d["avg_confidence"] = 0
                d["actual_accuracy"] = 0
                d["calibration_error"] = 0

            d["bucket_label"] = f"{d['min']}-{d['max']}%"

        return deciles

    @staticmethod
    def compute_calibration_error(
        predictions: list[dict[str, Any]],
        outcomes: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Compute aggregate calibration metrics."""
        curve = ConfidenceCalibrationEngine.compute_reliability_curve(predictions, outcomes)
        total = sum(d["count"] for d in curve)

        if total == 0:
            return {"ece": 0.0, "mce": 0.0, "bias": "calibrated", "bias_magnitude": 0.0, "sample_count": 0}

        ece = 0.0
        mce = 0.0
        weighted_conf = 0.0
        weighted_acc = 0.0

        for d in curve:
            if d["count"] > 0:
                weight = d["count"] / total
                ece += weight * d["calibration_error"]
                mce = max(mce, d["calibration_error"])
                weighted_conf += weight * d["avg_confidence"]
                weighted_acc += weight * d["actual_accuracy"]

        bias_magnitude = round(weighted_conf - weighted_acc, 1)
        abs_bias = abs(bias_magnitude)

        if abs_bias < 5:
            bias = "calibrated"
        elif bias_magnitude > 0:
            bias = "overconfident"
        else:
            bias = "underconfident"

        return {
            "ece": round(ece, 2),
            "mce": round(mce, 2),
            "bias": bias,
            "bias_magnitude": bias_magnitude,
            "sample_count": total,
            "reliability_curve": curve,
        }

    @staticmethod
    def compute_confidence_accuracy(
        predictions: list[dict[str, Any]],
        outcomes: dict[str, dict[str, Any]] | None = None,
    ) -> float:
        """Compute % of high-confidence predictions that were correct."""
        correct = 0
        total = 0
        for p in predictions:
            conf = p.get("confidence")
            if conf is None or not isinstance(conf, (int, float)) or conf < 60:
                continue
            total += 1
            outcome = (outcomes or {}).get(p.get("id") or p.get("prediction_id", ""))
            if outcome:
                actual_return = outcome.get("actual_return", 0)
                if isinstance(actual_return, (int, float)) and actual_return > 0:
                    correct += 1
        return round((correct / total) * 100, 1) if total > 0 else 0.0

    @staticmethod
    def detect_bias(
        predictions: list[dict[str, Any]],
        outcomes: dict[str, dict[str, Any]] | None = None,
    ) -> str:
        """Determine if system is overconfident, underconfident, or calibrated."""
        result = ConfidenceCalibrationEngine.compute_calibration_error(predictions, outcomes)
        return result["bias"]
