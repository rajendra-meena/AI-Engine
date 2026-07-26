"""
Mistake Classification Engine — automatically classifies trade failures.

10 mistake types, each with severity, description, and estimated impact.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"mk_{uuid.uuid4().hex[:12]}"


MISTAKE_TYPES = [
    "late_entry", "early_exit", "weak_confirmation", "false_breakout",
    "wrong_trend", "low_liquidity", "high_slippage", "news_impact",
    "risk_management_failure", "data_quality_issue",
]


class MistakeClassifier:
    """Classifies failed trades into mistake categories."""

    @staticmethod
    def classify_mistake(
        prediction: dict[str, Any] | None,
        outcome: dict[str, Any] | None,
        feedback: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Analyze a single trade for mistakes. Returns None if no mistake."""
        if not prediction:
            return None

        # Skip if no outcome (trade may not have completed)
        if not outcome:
            return None

        # Skip winning/neutral trades with high scores
        actual_return = outcome.get("actual_return", 0)
        if isinstance(actual_return, (int, float)) and actual_return > 0:
            return None

        mistakes: list[dict[str, Any]] = []

        # 1. Late Entry
        entry_err = MistakeClassifier._detect_late_entry(prediction, outcome, feedback)
        if entry_err:
            mistakes.append(entry_err)

        # 2. Early Exit
        early_exit = MistakeClassifier._detect_early_exit(outcome)
        if early_exit:
            mistakes.append(early_exit)

        # 3. Weak Confirmation
        weak = MistakeClassifier._detect_weak_confirmation(prediction)
        if weak:
            mistakes.append(weak)

        # 4. False Breakout
        false_bo = MistakeClassifier._detect_false_breakout(outcome)
        if false_bo:
            mistakes.append(false_bo)

        # 5. Wrong Trend
        wrong_trend = MistakeClassifier._detect_wrong_trend(prediction)
        if wrong_trend:
            mistakes.append(wrong_trend)

        # 6. Low Liquidity
        low_liq = MistakeClassifier._detect_low_liquidity(prediction)
        if low_liq:
            mistakes.append(low_liq)

        # 7. High Slippage
        high_slip = MistakeClassifier._detect_high_slippage(feedback)
        if high_slip:
            mistakes.append(high_slip)

        # 8. News Impact
        news = MistakeClassifier._detect_news_impact(outcome)
        if news:
            mistakes.append(news)

        # 9. Risk Management Failure
        risk_fail = MistakeClassifier._detect_risk_failure(prediction, feedback)
        if risk_fail:
            mistakes.append(risk_fail)

        # 10. Data Quality Issue
        data_issue = MistakeClassifier._detect_data_quality(outcome)
        if data_issue:
            mistakes.append(data_issue)

        if not mistakes:
            return None

        # Return the primary (most severe) mistake
        primary = max(mistakes, key=lambda m: {"critical": 3, "major": 2, "minor": 1}.get(m["severity"], 0))
        primary["secondary_types"] = [m["mistake_type"] for m in mistakes if m != primary]
        return primary

    @staticmethod
    def classify_batch(
        predictions: list[dict[str, Any]],
        outcomes: dict[str, dict[str, Any]] | None = None,
        feedbacks: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Classify mistakes across all predictions."""
        results = []
        for p in predictions:
            pid = p.get("id") or p.get("prediction_id", "")
            o = (outcomes or {}).get(pid)
            f = (feedbacks or {}).get(pid)
            mistake = MistakeClassifier.classify_mistake(p, o, f)
            if mistake:
                mistake["prediction_id"] = pid
                results.append(mistake)
        return results

    @staticmethod
    def get_mistake_summary(mistakes: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate mistake statistics."""
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        total_impact = 0.0
        for m in mistakes:
            mt = m.get("mistake_type", "unknown")
            by_type[mt] = by_type.get(mt, 0) + 1
            sev = m.get("severity", "minor")
            by_severity[sev] = by_severity.get(sev, 0) + 1
            total_impact += abs(m.get("impact", 0))

        most_common = max(by_type, key=by_type.get) if by_type else "none"
        return {
            "total_count": len(mistakes),
            "by_type": by_type,
            "by_severity": by_severity,
            "total_impact": round(total_impact, 2),
            "most_common": most_common,
        }

    @staticmethod
    def store_mistakes(db_conn: Any, mistakes: list[dict[str, Any]]) -> int:
        """Persist mistake records to ai_perf_mistake_log."""
        count = 0
        now = _now()
        for m in mistakes:
            mid = _new_id()
            pred_id = m.get("prediction_id", "")
            if not pred_id:
                continue
            try:
                db_conn.execute(
                    "INSERT OR IGNORE INTO ai_perf_mistake_log "
                    "(id, prediction_id, mistake_type, severity, description, impact, lesson, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        mid, pred_id, m["mistake_type"], m.get("severity"),
                        m.get("description"), m.get("impact", 0),
                        m.get("lesson"), now,
                    ),
                )
                count += 1
            except Exception:
                pass
        db_conn.commit()
        return count

    # ── Individual detectors ──

    @staticmethod
    def _detect_late_entry(prediction: dict, outcome: dict, feedback: dict | None) -> dict | None:
        entry_price = prediction.get("entry_price")
        direction = prediction.get("direction", "BUY")
        indicator_snap = prediction.get("indicator_snapshot")
        if not entry_price or not indicator_snap:
            return None
        try:
            import json
            ind = json.loads(indicator_snap) if isinstance(indicator_snap, str) else (indicator_snap or {})
            close = ind.get("candle_close", entry_price)
            if direction == "BUY" and close and close > entry_price * 1.005:
                impact = (close - entry_price) * prediction.get("quantity", 1) * -1
                return {"mistake_type": "late_entry", "severity": "major", "description": f"Entry at {entry_price:.1f}, price had already moved to {close:.1f}", "impact": round(impact, 2), "lesson": "Enter at first confirmation, not after price has already moved"}
            if direction == "SELL" and close and close < entry_price * 0.995:
                impact = (entry_price - close) * prediction.get("quantity", 1) * -1
                return {"mistake_type": "late_entry", "severity": "major", "description": f"Entry at {entry_price:.1f}, price had already dropped to {close:.1f}", "impact": round(impact, 2), "lesson": "Enter at first confirmation, not after price has already moved"}
        except Exception:
            pass
        return None

    @staticmethod
    def _detect_early_exit(outcome: dict) -> dict | None:
        mfe = outcome.get("max_favorable_excursion") or outcome.get("max_favorable", 0)
        actual_return = outcome.get("actual_return", 0)
        if isinstance(mfe, (int, float)) and isinstance(actual_return, (int, float)) and mfe > 0 and actual_return > 0:
            if actual_return < mfe * 0.5:
                return {"mistake_type": "early_exit", "severity": "major", "description": f"Exited at {actual_return:.1f}, MFE was {mfe:.1f} — left {((mfe - actual_return) / mfe * 100):.0f}% on the table", "impact": round(mfe - actual_return, 2), "lesson": "Let winners run closer to target"}
        return None

    @staticmethod
    def _detect_weak_confirmation(prediction: dict) -> dict | None:
        confidence = prediction.get("confidence", 0)
        if isinstance(confidence, (int, float)) and confidence < 60:
            return {"mistake_type": "weak_confirmation", "severity": "major", "description": f"Trade taken with low confidence ({confidence}%)", "impact": 0, "lesson": "Avoid trades below 60% confidence"}
        return None

    @staticmethod
    def _detect_false_breakout(outcome: dict) -> dict | None:
        error_cat = outcome.get("error_category", "")
        error_reason = outcome.get("error_reason", "")
        if error_cat == "FALSE_BREAKOUT" or "false breakout" in error_reason.lower():
            return {"mistake_type": "false_breakout", "severity": "minor", "description": "Trade activated on false breakout signal", "impact": 0, "lesson": "Confirm breakout with volume and close beyond S/R"}
        return None

    @staticmethod
    def _detect_wrong_trend(prediction: dict) -> dict | None:
        direction = prediction.get("direction", "WAIT")
        regime = prediction.get("market_regime") or prediction.get("regime", "")
        if isinstance(regime, str):
            regime_upper = regime.upper()
            if direction == "BUY" and regime_upper in ("BEARISH", "DOWNTREND"):
                return {"mistake_type": "wrong_trend", "severity": "critical", "description": f"Bought in {regime} market", "impact": 0, "lesson": "Trade with the trend, not against it"}
            if direction == "SELL" and regime_upper in ("BULLISH", "UPTREND"):
                return {"mistake_type": "wrong_trend", "severity": "critical", "description": f"Sold in {regime} market", "impact": 0, "lesson": "Trade with the trend, not against it"}
        return None

    @staticmethod
    def _detect_low_liquidity(prediction: dict) -> dict | None:
        ind_snap = prediction.get("indicator_snapshot")
        if not ind_snap:
            return None
        try:
            import json
            ind = json.loads(ind_snap) if isinstance(ind_snap, str) else ind_snap
            volume = ind.get("candle_volume") or ind.get("volume", 0)
            avg_vol = ind.get("average_volume", 0)
            if volume and avg_vol and avg_vol > 0 and (volume / avg_vol) < 0.5:
                return {"mistake_type": "low_liquidity", "severity": "major", "description": f"Volume {volume:.0f} is {(volume/avg_vol)*100:.0f}% of average — low liquidity", "impact": 0, "lesson": "Avoid trades with volume below 50% of average"}
        except Exception:
            pass
        return None

    @staticmethod
    def _detect_high_slippage(feedback: dict | None) -> dict | None:
        if not feedback:
            return None
        entry_slip = feedback.get("entry_slippage", 0) or 0
        exit_slip = feedback.get("exit_slippage", 0) or 0
        planned_risk = feedback.get("planned_risk", 1) or 1
        total_slip = abs(entry_slip) + abs(exit_slip)
        if planned_risk and planned_risk > 0 and (total_slip / abs(planned_risk)) > 0.01:
            return {"mistake_type": "high_slippage", "severity": "minor", "description": f"Total slippage {total_slip:.2f} vs planned risk {planned_risk:.2f}", "impact": round(total_slip, 2), "lesson": "Use limit orders or adjust for expected slippage"}
        return None

    @staticmethod
    def _detect_news_impact(outcome: dict) -> dict | None:
        error_cat = outcome.get("error_category", "")
        error_reason = outcome.get("error_reason", "")
        if error_cat == "NEWS_SHOCK" or "news" in error_reason.lower():
            return {"mistake_type": "news_impact", "severity": "minor", "description": "Trade impacted by news event", "impact": 0, "lesson": "Check economic calendar before entry"}
        return None

    @staticmethod
    def _detect_risk_failure(prediction: dict, feedback: dict | None) -> dict | None:
        if not feedback:
            return None
        actual_risk = feedback.get("actual_risk", 0) or 0
        planned_risk = feedback.get("planned_risk", 1) or 1
        if planned_risk > 0 and (actual_risk / planned_risk) > 1.5:
            return {"mistake_type": "risk_management_failure", "severity": "critical", "description": f"Actual risk {actual_risk:.2f} exceeds planned risk {planned_risk:.2f} by {(actual_risk/planned_risk - 1)*100:.0f}%", "impact": round(actual_risk - planned_risk, 2), "lesson": "Strictly enforce position sizing"}
        return None

    @staticmethod
    def _detect_data_quality(outcome: dict) -> dict | None:
        error_cat = outcome.get("error_category", "")
        if error_cat == "DATA_QUALITY_ISSUE":
            return {"mistake_type": "data_quality_issue", "severity": "minor", "description": "Trade affected by data quality issue", "impact": 0, "lesson": "Verify data feed quality before trading"}
        return None
