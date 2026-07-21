"""
Orchestrator — combines score, confidence, risk, and trade plan into a final decision.
Applies thresholds, resolves conflicts, generates decision + reasoning.
"""

from __future__ import annotations

from typing import Any


class Orchestrator:
    """Produces the final DecisionSnapshot from sub-engine outputs."""

    @staticmethod
    def orchestrate(score_result: dict[str, Any],
                    confidence_result: dict[str, Any],
                    risk_result: dict[str, Any],
                    trade_plan: dict[str, Any],
                    context_snap: dict[str, Any] | None,
                    mtf_snap: dict[str, Any] | None) -> dict[str, Any]:
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

        if score >= 60 and confidence >= 60 and risk_level in ("LOW", "MEDIUM") and plan_valid:
            decision = "HIGH_CONVICTION"
            all_reasoning.append(f"High conviction: score={score}, confidence={confidence}")
        elif score >= 50 and confidence >= 50 and risk_level in ("LOW", "MEDIUM", "HIGH") and plan_valid:
            decision = "MODERATE"
            all_reasoning.append(f"Moderate: score={score}, confidence={confidence}, risk={risk_level}")
        elif score >= 40 and confidence >= 40 and risk_level != "EXTREME" and plan_valid:
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
