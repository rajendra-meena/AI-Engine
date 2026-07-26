"""
Orchestrator — combines score, confidence, risk, and trade plan into a final decision.
Applies thresholds, resolves conflicts, generates decision + reasoning.

EnhancedOrchestrator — wraps the original Orchestrator + all Phase 56 modules.
"""

from __future__ import annotations

from typing import Any

from ai_decision.modules.signal_validator import SignalValidator
from ai_decision.modules.trade_quality import TradeQualityScorer
from ai_decision.modules.mtf_agreement import MultiTFAgreement
from ai_decision.modules.false_signal import FalseSignalDetector
from ai_decision.modules.detailed_confidence import DetailedConfidenceEngine
from ai_decision.modules.confidence_adjuster import DynamicConfidenceAdjuster
from ai_decision.modules.ai_explainer import AIExplainer
from ai_decision.modules.trade_approval import TradeApprovalEngine


class Orchestrator:
    """Produces the final DecisionSnapshot from sub-engine outputs."""

    @staticmethod
    def orchestrate(
        score_result: dict[str, Any],
        confidence_result: dict[str, Any],
        risk_result: dict[str, Any],
        trade_plan: dict[str, Any],
        context_snap: dict[str, Any] | None,
        mtf_snap: dict[str, Any] | None,
    ) -> dict[str, Any]:
        score = score_result.get("score", 0)
        confidence = confidence_result.get("confidence", 0)
        risk_level = risk_result.get("risk_level", "EXTREME")
        plan_valid = trade_plan.get("plan_valid", False)

        all_warnings = []
        all_reasoning = []
        decision = "NO_TRADE"

        if score < 40:
            all_warnings.append(f"Score too low: {score}")
        if confidence < 40:
            all_warnings.append(f"Confidence too low: {confidence}")
        if risk_level in ("HIGH", "EXTREME"):
            all_warnings.append(f"Risk too high: {risk_level}")
        if not plan_valid:
            all_warnings.append("No valid trade plan")

        if (
            score >= 60
            and confidence >= 60
            and risk_level in ("LOW", "MEDIUM")
            and plan_valid
        ):
            decision = "HIGH_CONVICTION"
            all_reasoning.append(
                f"High conviction: score={score}, confidence={confidence}"
            )
        elif (
            score >= 50
            and confidence >= 50
            and risk_level in ("LOW", "MEDIUM", "HIGH")
            and plan_valid
        ):
            decision = "MODERATE"
            all_reasoning.append(
                f"Moderate: score={score}, confidence={confidence}, risk={risk_level}"
            )
        elif (
            score >= 40 and confidence >= 40 and risk_level != "EXTREME" and plan_valid
        ):
            decision = "LOW_CONVICTION"
            all_reasoning.append(f"Low: score={score}, confidence={confidence}")
        else:
            decision = "NO_TRADE"
            all_reasoning = all_warnings[:3] if all_warnings else ["Thresholds not met"]
            all_warnings = all_reasoning

        all_reasoning.extend(score_result.get("reasoning", [])[:2])
        all_reasoning.extend(confidence_result.get("reasoning", [])[:2])
        all_reasoning.extend(risk_result.get("reasoning", [])[:2])

        return {
            "decision": decision,
            "score": score,
            "score_grade": score_result.get("grade", "VERY_LOW"),
            "confidence": confidence,
            "confidence_grade": confidence_result.get("grade", "VERY_LOW"),
            "risk_level": risk_level,
            "risk_score": risk_result.get("risk_score", 0),
            "max_risk_percent": risk_result.get("max_risk_percent", 0.0),
            "trade_plan": {
                "direction": trade_plan.get("direction", "NONE"),
                "valid": trade_plan.get("plan_valid", False),
                "entry_zone": trade_plan.get("entry_zone"),
                "sl_zone": trade_plan.get("sl_zone"),
                "target_zones": trade_plan.get("target_zones", []),
                "risk_reward_context": trade_plan.get("risk_reward_context", "unknown"),
                "max_risk_percent": trade_plan.get("max_risk_percent", 0.0),
            },
            "reasoning": all_reasoning[:8],
            "warnings": all_warnings[:5],
        }


class EnhancedOrchestrator:
    """Composes the original Orchestrator + all Phase 56 validation modules."""

    @staticmethod
    def orchestrate(
        score_result: dict[str, Any],
        confidence_result: dict[str, Any],
        risk_result: dict[str, Any],
        trade_plan: dict[str, Any],
        context_snap: dict[str, Any] | None = None,
        indicator_snap: dict[str, Any] | None = None,
        structure_snap: dict[str, Any] | None = None,
        pattern_snap: dict[str, Any] | None = None,
        mtf_snap: dict[str, Any] | None = None,
        sr_snap: dict[str, Any] | None = None,
        decision_snap: dict[str, Any] | None = None,
        market_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run original orchestrator then all Phase 56 modules."""
        # Step 1: Original orchestration
        base = Orchestrator.orchestrate(
            score_result, confidence_result, risk_result, trade_plan,
            context_snap, mtf_snap,
        )

        # Step 2: Signal Validator
        signal_validations = SignalValidator.validate(
            decision_snap, context_snap, indicator_snap, structure_snap,
            pattern_snap, mtf_snap, sr_snap,
        )

        # Step 3: Trade Quality Scorer
        trade_quality = TradeQualityScorer.evaluate(
            decision_snap, context_snap, indicator_snap, pattern_snap, sr_snap, mtf_snap,
        )

        # Step 4: MTF Agreement
        mtf_agreement = MultiTFAgreement.evaluate(mtf_snap)

        # Step 5: False Signal Detection
        false_signal_check = FalseSignalDetector.detect(
            context_snap, indicator_snap, structure_snap, sr_snap,
        )

        # Step 6: Detailed Confidence
        detailed_confidence = DetailedConfidenceEngine.evaluate(
            context_snap, indicator_snap, structure_snap, pattern_snap, mtf_snap, sr_snap, decision_snap,
        )

        # Step 7: Dynamic Confidence Adjustment
        base_confidence = detailed_confidence.get("overall_confidence", 0)
        confidence_adjustment = DynamicConfidenceAdjuster.adjust(
            context_snap, indicator_snap, market_snapshot, base_confidence,
        )
        adjusted_confidence = confidence_adjustment.get("adjusted_confidence", base_confidence)

        # Step 8: AI Explainer
        ai_explanation = AIExplainer.explain(
            decision_snap, context_snap, indicator_snap, structure_snap,
            pattern_snap, mtf_snap, sr_snap,
            signal_validations, trade_quality, false_signal_check,
        )

        # Step 9: Trade Approval
        approval = TradeApprovalEngine.approve(
            detailed_confidence, trade_quality, mtf_agreement, risk_result,
            signal_validations, false_signal_check, decision_snap,
        )

        # Merge into enriched output
        enriched = dict(base)
        enriched.update({
            "signal_validations": signal_validations,
            "trade_quality": trade_quality,
            "mtf_agreement": mtf_agreement,
            "false_signal_check": false_signal_check,
            "detailed_confidence": detailed_confidence,
            "confidence_adjustment": confidence_adjustment,
            "adjusted_confidence": adjusted_confidence,
            "ai_explanation": ai_explanation,
            "approval": approval,
            "is_trade_eligible": approval.get("approved", False),
        })

        return enriched
