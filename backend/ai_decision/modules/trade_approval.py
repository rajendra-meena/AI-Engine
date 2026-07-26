"""
Trade Approval Engine — final gatekeeper deciding TRADE_ELIGIBLE vs NO_TRADE.

All 7 gates must pass for a trade to be eligible.
"""

from __future__ import annotations

from typing import Any


class TradeApprovalEngine:
    """Evaluates all gates and decides if a trade is eligible."""

    @staticmethod
    def approve(
        detailed_confidence: dict[str, Any] | None = None,
        trade_quality: dict[str, Any] | None = None,
        mtf_agreement: dict[str, Any] | None = None,
        risk_result: dict[str, Any] | None = None,
        signal_validations: dict[str, Any] | None = None,
        false_signal_check: dict[str, Any] | None = None,
        decision_snap: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate all 7 gates and return approval decision."""
        gates: list[dict[str, Any]] = []

        # Gate 1: Confidence Gate (> 80)
        gate1 = TradeApprovalEngine._gate_confidence(detailed_confidence)
        gates.append(gate1)

        # Gate 2: Quality Gate (>= B)
        gate2 = TradeApprovalEngine._gate_quality(trade_quality)
        gates.append(gate2)

        # Gate 3: RR Gate (>= 2.0)
        gate3 = TradeApprovalEngine._gate_rr(decision_snap)
        gates.append(gate3)

        # Gate 4: MTF Agreement Gate (> 70%)
        gate4 = TradeApprovalEngine._gate_mtf_agreement(mtf_agreement)
        gates.append(gate4)

        # Gate 5: Risk Gate (LOW or MEDIUM)
        gate5 = TradeApprovalEngine._gate_risk(risk_result)
        gates.append(gate5)

        # Gate 6: Signal Validation Gate (no BLOCK)
        gate6 = TradeApprovalEngine._gate_signal_validations(signal_validations)
        gates.append(gate6)

        # Gate 7: False Signal Gate (no false signal)
        gate7 = TradeApprovalEngine._gate_false_signal(false_signal_check)
        gates.append(gate7)

        all_passed = all(g["passed"] for g in gates)
        blocking_reasons = [g["detail"] for g in gates if not g["passed"]]

        return {
            "approved": all_passed,
            "decision": "TRADE_ELIGIBLE" if all_passed else "NO_TRADE",
            "gates": gates,
            "blocking_reasons": blocking_reasons,
        }

    @staticmethod
    def _gate_confidence(detailed_confidence: dict[str, Any] | None) -> dict[str, Any]:
        if not detailed_confidence:
            return {"name": "confidence", "passed": False, "value": 0, "threshold": 80, "detail": "No confidence data"}
        value = detailed_confidence.get("overall_confidence", 0)
        if not isinstance(value, (int, float)):
            value = 0
        return {
            "name": "confidence",
            "passed": value >= 80,
            "value": int(value),
            "threshold": 80,
            "detail": f"Confidence {int(value)}/80" if value >= 80 else f"Confidence {int(value)} < 80",
        }

    @staticmethod
    def _gate_quality(trade_quality: dict[str, Any] | None) -> dict[str, Any]:
        if not trade_quality:
            return {"name": "quality", "passed": False, "value": "NONE", "threshold": "B", "detail": "No quality data"}
        grade = trade_quality.get("grade", "REJECT")
        score = trade_quality.get("total_score", 0)
        acceptable = {"A+", "A", "B"}
        passed = grade in acceptable
        return {
            "name": "quality",
            "passed": passed,
            "value": grade,
            "threshold": "B",
            "detail": f"Grade {grade} (score {score})" if passed else f"Grade {grade} < B",
        }

    @staticmethod
    def _gate_rr(decision_snap: dict[str, Any] | None) -> dict[str, Any]:
        rr = 0.0
        if decision_snap:
            tp = decision_snap.get("trade_plan", {})
            entry = tp.get("entry_zone")
            sl = tp.get("sl_zone")
            targets = tp.get("target_zones", [])
            target = targets[0] if isinstance(targets, list) and targets else tp.get("target_price")
            if isinstance(entry, dict): entry = entry.get("price") or entry.get("value")
            if isinstance(sl, dict): sl = sl.get("price") or sl.get("value")
            if isinstance(target, dict): target = target.get("price") or target.get("value")
            if entry and sl and target:
                try:
                    risk = abs(float(entry) - float(sl))
                    reward = abs(float(target) - float(entry))
                    if risk > 0:
                        rr = round(reward / risk, 1)
                except (TypeError, ValueError, ZeroDivisionError):
                    pass
        return {
            "name": "risk_reward",
            "passed": rr >= 2.0,
            "value": rr,
            "threshold": 2.0,
            "detail": f"R:R {rr}/2.0" if rr >= 2.0 else f"R:R {rr} < 2.0",
        }

    @staticmethod
    def _gate_mtf_agreement(mtf_agreement: dict[str, Any] | None) -> dict[str, Any]:
        if not mtf_agreement:
            return {"name": "mtf_agreement", "passed": False, "value": 0, "threshold": 70, "detail": "No MTF agreement data"}
        pct = mtf_agreement.get("agreement_percent", 0)
        if not isinstance(pct, (int, float)):
            pct = 0
        return {
            "name": "mtf_agreement",
            "passed": pct > 70,
            "value": int(pct),
            "threshold": 70,
            "detail": f"MTF agreement {int(pct)}% > 70%" if pct > 70 else f"MTF agreement {int(pct)}% <= 70%",
        }

    @staticmethod
    def _gate_risk(risk_result: dict[str, Any] | None) -> dict[str, Any]:
        if not risk_result:
            return {"name": "risk", "passed": False, "value": "UNKNOWN", "threshold": "LOW/MEDIUM", "detail": "No risk data"}
        level = risk_result.get("risk_level", "EXTREME")
        if not isinstance(level, str):
            level = "EXTREME"
        level = level.upper()
        passed = level in ("LOW", "MEDIUM")
        return {
            "name": "risk",
            "passed": passed,
            "value": level,
            "threshold": "LOW/MEDIUM",
            "detail": f"Risk {level}" if passed else f"Risk {level} — too high",
        }

    @staticmethod
    def _gate_signal_validations(signal_validations: dict[str, Any] | None) -> dict[str, Any]:
        if not signal_validations:
            return {"name": "signal_validation", "passed": False, "value": "NO_DATA", "threshold": "0 BLOCK", "detail": "No validation data"}
        blocks = signal_validations.get("block_count", 0)
        if not isinstance(blocks, (int, float)):
            blocks = 0
        passed = blocks == 0
        return {
            "name": "signal_validation",
            "passed": passed,
            "value": int(blocks),
            "threshold": "0",
            "detail": f"{int(blocks)} BLOCK signals" if not passed else "No BLOCK signals",
        }

    @staticmethod
    def _gate_false_signal(false_signal_check: dict[str, Any] | None) -> dict[str, Any]:
        if not false_signal_check:
            return {"name": "false_signal", "passed": True, "value": "NOT_CHECKED", "threshold": "none", "detail": "False signal check not performed — assumed clean"}
        detected = false_signal_check.get("is_false_signal", False)
        return {
            "name": "false_signal",
            "passed": not detected,
            "value": "DETECTED" if detected else "CLEAN",
            "threshold": "none",
            "detail": "False signal detected" if detected else "No false signal",
        }
