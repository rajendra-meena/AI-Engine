"""
AI Explainer — produces structured WHY BUY / WHY SELL / WHY NO TRADE explanations.
"""

from __future__ import annotations

from typing import Any


class AIExplainer:
    """Generates human-readable explanations for AI decisions."""

    @staticmethod
    def explain(
        decision_snap: dict[str, Any] | None,
        context_snap: dict[str, Any] | None,
        indicator_snap: dict[str, Any] | None,
        structure_snap: dict[str, Any] | None,
        pattern_snap: dict[str, Any] | None,
        mtf_snap: dict[str, Any] | None,
        sr_snap: dict[str, Any] | None,
        signal_validations: dict[str, Any] | None = None,
        trade_quality: dict[str, Any] | None = None,
        false_signal_check: dict[str, Any] | None = None,
        approval_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Explain why the AI decided BUY, SELL, or NO_TRADE."""
        decision = (decision_snap or {}).get("decision", "NO_TRADE")
        direction = (decision_snap or {}).get("direction", "WAIT")
        score = (decision_snap or {}).get("score", 0)
        confidence = (decision_snap or {}).get("confidence", 0)

        supporting_factors: list[dict[str, Any]] = []
        blocking_factors: list[dict[str, Any]] = []

        # Collect supporting factors
        AIExplainer._add_supporting_factors(supporting_factors, context_snap, structure_snap, indicator_snap, pattern_snap, mtf_snap, signal_validations)

        # Collect blocking factors
        AIExplainer._add_blocking_factors(blocking_factors, decision_snap, signal_validations, false_signal_check, approval_result)

        # Build primary reason
        primary = AIExplainer._primary_reason(decision, direction, score, confidence, blocking_factors)

        # Construct explanations
        why_buy = AIExplainer._why_buy(decision, direction, primary, supporting_factors, blocking_factors)
        why_sell = AIExplainer._why_sell(decision, direction, primary, supporting_factors, blocking_factors)
        why_no_trade = AIExplainer._why_no_trade(decision, primary, blocking_factors)

        return {
            "decision_explanation": {
                "primary_reason": primary,
                "supporting_factors": supporting_factors[:6],
                "blocking_factors": blocking_factors[:6],
            },
            "why_buy": why_buy,
            "why_sell": why_sell,
            "why_no_trade": why_no_trade,
        }

    @staticmethod
    def _add_supporting_factors(
        factors: list[dict[str, Any]],
        context_snap: dict[str, Any] | None,
        structure_snap: dict[str, Any] | None,
        indicator_snap: dict[str, Any] | None,
        pattern_snap: dict[str, Any] | None,
        mtf_snap: dict[str, Any] | None,
        signal_validations: dict[str, Any] | None,
    ) -> None:
        if structure_snap:
            trend = structure_snap.get("trend", "")
            if trend:
                factors.append({"factor": "trend", "impact": "positive", "detail": f"Trend is {trend}"})
            valid = structure_snap.get("valid_structure", False)
            if valid:
                factors.append({"factor": "market_structure", "impact": "positive", "detail": "Valid market structure"})

        if context_snap:
            momo = context_snap.get("momentum", "")
            if momo and str(momo).upper() in ("STRONG", "BULLISH"):
                factors.append({"factor": "momentum", "impact": "positive", "detail": f"Strong momentum ({momo})"})

        if indicator_snap:
            rsi = indicator_snap.get("rsi_14")
            if isinstance(rsi, (int, float)) and 40 <= rsi <= 60:
                factors.append({"factor": "rsi", "impact": "positive", "detail": f"RSI {rsi:.0f} in neutral zone"})
            macd = indicator_snap.get("macd_histogram")
            if isinstance(macd, (int, float)):
                factors.append({"factor": "macd", "impact": "positive" if macd > 0 else "negative", "detail": f"MACD histogram {'positive' if macd > 0 else 'negative'}"})

        if pattern_snap:
            pat = pattern_snap.get("strongest_pattern", "")
            if pat:
                factors.append({"factor": "pattern", "impact": "positive", "detail": f"Pattern detected: {pat}"})
            count = pattern_snap.get("pattern_count") or pattern_snap.get("total_count", 0)
            if isinstance(count, (int, float)) and count > 0:
                factors.append({"factor": "pattern_count", "impact": "positive", "detail": f"{int(count)} patterns detected"})

        if mtf_snap:
            align = mtf_snap.get("alignment_level", "")
            if align in ("FULL_ALIGNMENT", "STRONG_ALIGNMENT"):
                factors.append({"factor": "mtf_alignment", "impact": "positive", "detail": f"MTF {align}"})

        if signal_validations:
            passed = signal_validations.get("pass_count", 0)
            if isinstance(passed, (int, float)) and passed >= 7:
                factors.append({"factor": "signal_validation", "impact": "positive", "detail": f"{int(passed)}/10 signals passed"})

    @staticmethod
    def _add_blocking_factors(
        factors: list[dict[str, Any]],
        decision_snap: dict[str, Any] | None,
        signal_validations: dict[str, Any] | None,
        false_signal_check: dict[str, Any] | None,
        approval_result: dict[str, Any] | None,
    ) -> None:
        warnings_list = (decision_snap or {}).get("warnings", [])
        if isinstance(warnings_list, list) and warnings_list:
            for w in warnings_list[:3]:
                factors.append({"factor": "warning", "impact": "blocking", "detail": str(w)})

        risk_level = (decision_snap or {}).get("risk_level", "")
        if risk_level in ("HIGH", "EXTREME"):
            factors.append({"factor": "risk_level", "impact": "blocking", "detail": f"Risk level: {risk_level}"})

        if signal_validations:
            blocks = signal_validations.get("block_count", 0)
            if isinstance(blocks, (int, float)) and blocks > 0:
                blocked = [v for v in signal_validations.get("validations", []) if v.get("status") == "BLOCK"]
                for b in blocked[:2]:
                    factors.append({"factor": "signal_block", "impact": "blocking", "detail": b.get("reason", "")})

        if false_signal_check and false_signal_check.get("is_false_signal"):
            for r in (false_signal_check.get("reject_reasons") or [])[:2]:
                factors.append({"factor": "false_signal", "impact": "blocking", "detail": str(r)})

        if approval_result and not approval_result.get("approved", False):
            gates = approval_result.get("gates", [])
            for g in gates:
                if not g.get("passed", True):
                    factors.append({"factor": f"gate_{g.get('name', 'unknown')}", "impact": "blocking", "detail": g.get("detail", f"Gate {g.get('name')} failed")})

    @staticmethod
    def _primary_reason(decision: str, direction: str, score: int, confidence: int, blocking: list[dict[str, Any]]) -> str:
        if decision in ("HIGH_CONVICTION", "MODERATE") and direction in ("BUY", "SELL"):
            return f"Confidence at {confidence}% with score {score}/100 — {direction} signal confirmed"
        if decision == "LOW_CONVICTION":
            return f"Low conviction {direction} — score {score}, confidence {confidence}%"
        if blocking:
            return f"No trade — {blocking[0]['detail']}"
        return f"No trade — score {score}, confidence {confidence}%"

    @staticmethod
    def _why_buy(
        decision: str, direction: str, primary: str,
        supporting: list[dict[str, Any]], blocking: list[dict[str, Any]]
    ) -> str:
        if decision in ("HIGH_CONVICTION", "MODERATE") and direction == "BUY":
            top = [s["detail"] for s in supporting[:3]]
            return f"BUY because: {'; '.join(top)}" if top else "BUY signal — all conditions favorable"
        return ""

    @staticmethod
    def _why_sell(
        decision: str, direction: str, primary: str,
        supporting: list[dict[str, Any]], blocking: list[dict[str, Any]]
    ) -> str:
        if decision in ("HIGH_CONVICTION", "MODERATE") and direction == "SELL":
            top = [s["detail"] for s in supporting[:3]]
            return f"SELL because: {'; '.join(top)}" if top else "SELL signal — all conditions favorable"
        return ""

    @staticmethod
    def _why_no_trade(
        decision: str, primary: str,
        blocking: list[dict[str, Any]]
    ) -> str:
        if decision in ("HIGH_CONVICTION", "MODERATE"):
            return ""
        if blocking:
            top = [b["detail"] for b in blocking[:3]]
            return f"No trade because: {'; '.join(top)}"
        return "No trade — insufficient conditions for execution"
