"""
Trade Evaluator — evaluates every completed trade on entry, exit, SL, target quality.

Computes overall trade score (0-100) and outcome classification.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"ev_{uuid.uuid4().hex[:12]}"


class TradeEvaluator:
    """Evaluates trade quality across multiple dimensions."""

    @staticmethod
    def evaluate_single(
        prediction: dict[str, Any] | None,
        outcome: dict[str, Any] | None,
        feedback: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Evaluate a single trade and return scoring breakdown."""
        if not prediction:
            return {"overall_score": 0, "outcome_class": "Failed", "reason": "No prediction data"}

        entry = TradeEvaluator._score_entry_accuracy(prediction, outcome, feedback)
        exit_q = TradeEvaluator._score_exit_quality(outcome)
        sl = TradeEvaluator._score_sl_quality(prediction, outcome)
        target = TradeEvaluator._score_target_quality(prediction, outcome)
        mfe_mae = TradeEvaluator._compute_mfe_mae_ratio(outcome)
        slippage = TradeEvaluator._compute_slippage_impact(feedback)

        # Weighted overall score
        weights = {"entry": 0.20, "exit": 0.25, "sl": 0.15, "target": 0.20, "mfe_mae": 0.10, "slippage": 0.10}
        overall = round(
            entry * weights["entry"]
            + exit_q * weights["exit"]
            + sl * weights["sl"]
            + target * weights["target"]
            + mfe_mae * weights["mfe_mae"]
            + (100 - slippage) * weights["slippage"]
        )
        overall = max(0, min(100, overall))

        outcome_class = TradeEvaluator.classify_outcome(overall)

        return {
            "entry_accuracy": round(entry, 1),
            "exit_quality": round(exit_q, 1),
            "sl_quality": round(sl, 1),
            "target_quality": round(target, 1),
            "mfe_mae_ratio": round(mfe_mae, 1),
            "slippage_impact": round(slippage, 1),
            "overall_score": overall,
            "outcome_class": outcome_class,
        }

    @staticmethod
    def evaluate_batch(
        predictions: list[dict[str, Any]],
        outcomes: dict[str, dict[str, Any]],
        feedbacks: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Evaluate multiple trades."""
        results = []
        for p in predictions:
            pid = p.get("id") or p.get("prediction_id", "")
            o = outcomes.get(pid)
            f = feedbacks.get(pid)
            eval_result = TradeEvaluator.evaluate_single(p, o, f)
            eval_result["prediction_id"] = pid
            results.append(eval_result)
        return results

    @staticmethod
    def store_evaluation(
        db_conn: Any, prediction_id: str, evaluation: dict[str, Any]
    ) -> str:
        """Insert or update evaluation record."""
        eid = _new_id()
        now = _now()
        try:
            db_conn.execute(
                "INSERT OR REPLACE INTO ai_perf_trade_evaluation "
                "(id, prediction_id, entry_accuracy, exit_quality, sl_quality, target_quality, "
                "mfe_mae_ratio, slippage_impact, overall_score, outcome_class, evaluated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    eid, prediction_id,
                    evaluation.get("entry_accuracy"), evaluation.get("exit_quality"),
                    evaluation.get("sl_quality"), evaluation.get("target_quality"),
                    evaluation.get("mfe_mae_ratio"), evaluation.get("slippage_impact"),
                    evaluation.get("overall_score"), evaluation.get("outcome_class"), now,
                ),
            )
            db_conn.commit()
        except Exception:
            db_conn.rollback()
        return eid

    @staticmethod
    def classify_outcome(score: int) -> str:
        if score >= 85:
            return "Excellent"
        elif score >= 65:
            return "Good"
        elif score >= 45:
            return "Average"
        elif score >= 25:
            return "Poor"
        return "Failed"

    # ── Scoring helpers ──

    @staticmethod
    def _score_entry_accuracy(
        prediction: dict[str, Any] | None, outcome: dict[str, Any] | None, feedback: dict[str, Any] | None
    ) -> float:
        if not prediction:
            return 0.0
        entry_price = prediction.get("entry_price")
        direction = prediction.get("direction", "BUY")
        if not entry_price:
            return 50.0

        # Check how far entry was from optimal
        # If outcome has actual_return > 0, entry was good enough
        actual_return = (outcome or {}).get("actual_return", 0)
        if actual_return is not None and actual_return > 0:
            return 85.0
        elif actual_return is not None and actual_return > -0.5:
            return 60.0
        elif actual_return is not None:
            return 30.0
        return 50.0

    @staticmethod
    def _score_exit_quality(outcome: dict[str, Any] | None) -> float:
        if not outcome:
            return 50.0
        mfe = outcome.get("max_favorable_excursion") or outcome.get("max_favorable", 0)
        actual_return = outcome.get("actual_return", 0)
        if mfe and isinstance(mfe, (int, float)) and mfe > 0:
            capture_ratio = abs(actual_return) / abs(mfe) if mfe != 0 else 0
            capture_ratio = min(1.0, max(0, capture_ratio))
            return capture_ratio * 100
        # Without MFE data, use return magnitude
        if isinstance(actual_return, (int, float)):
            if actual_return > 2: return 85
            elif actual_return > 0: return 70
            elif actual_return > -1: return 40
            else: return 20
        return 50.0

    @staticmethod
    def _score_sl_quality(prediction: dict[str, Any] | None, outcome: dict[str, Any] | None) -> float:
        if not prediction:
            return 50.0
        stop_loss = prediction.get("stop_loss")
        entry_price = prediction.get("entry_price")
        mae = (outcome or {}).get("max_adverse_excursion") or (outcome or {}).get("max_adverse", 0)
        if stop_loss and entry_price and isinstance(mae, (int, float)) and mae > 0:
            sl_distance = abs(entry_price - stop_loss)
            if sl_distance > 0:
                ratio = mae / sl_distance
                if ratio <= 0.8: return 90
                elif ratio <= 1.0: return 70
                elif ratio <= 1.5: return 40
                else: return 20
        # Without MAE, check if SL was hit
        if (outcome or {}).get("stop_loss_hit"):
            return 30
        return 70

    @staticmethod
    def _score_target_quality(prediction: dict[str, Any] | None, outcome: dict[str, Any] | None) -> float:
        if not prediction:
            return 50.0
        target_hit = (outcome or {}).get("target_hit", False)
        mfe = (outcome or {}).get("max_favorable_excursion") or (outcome or {}).get("max_favorable", 0)
        target = prediction.get("target")
        entry = prediction.get("entry_price")
        if target_hit:
            return 100
        if target and entry and isinstance(mfe, (int, float)) and mfe > 0:
            target_dist = abs(target - entry)
            if target_dist > 0:
                pct = mfe / target_dist
                if pct >= 0.9: return 85
                elif pct >= 0.7: return 65
                elif pct >= 0.5: return 45
                elif pct >= 0.3: return 30
                else: return 15
        return 50

    @staticmethod
    def _compute_mfe_mae_ratio(outcome: dict[str, Any] | None) -> float:
        if not outcome:
            return 50.0
        mfe = outcome.get("max_favorable_excursion") or outcome.get("max_favorable", 0)
        mae = outcome.get("max_adverse_excursion") or outcome.get("max_adverse", 0)
        if isinstance(mfe, (int, float)) and isinstance(mae, (int, float)) and (mfe + mae) > 0:
            ratio = (mfe / (mfe + mae)) * 100
            return max(0, min(100, ratio))
        return 50.0

    @staticmethod
    def _compute_slippage_impact(feedback: dict[str, Any] | None) -> float:
        if not feedback:
            return 0.0
        entry_slip = feedback.get("entry_slippage", 0) or 0
        exit_slip = feedback.get("exit_slippage", 0) or 0
        planned_risk = feedback.get("planned_risk", 1) or 1
        if isinstance(entry_slip, (int, float)) and isinstance(exit_slip, (int, float)):
            total = abs(entry_slip) + abs(exit_slip)
            if planned_risk and planned_risk > 0:
                impact_pct = (total / abs(planned_risk)) * 100
                return min(100, impact_pct)
        return 0.0
