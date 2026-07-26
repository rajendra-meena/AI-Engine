"""
AI Learning Dataset Builder — auto-saves decision context for ML training.

Captures signal data, indicators, confidence breakdown, decision metadata,
market context, trade outcome, PnL, and screenshot references.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"ds_{uuid.uuid4().hex[:12]}"


class LearningDatasetBuilder:
    """Records decision data for future model training."""

    @staticmethod
    def record(
        symbol: str,
        decision_snap: dict[str, Any] | None = None,
        indicator_snap: dict[str, Any] | None = None,
        context_snap: dict[str, Any] | None = None,
        detailed_confidence: dict[str, Any] | None = None,
        trade_quality: dict[str, Any] | None = None,
        mtf_agreement: dict[str, Any] | None = None,
        signal_validations: dict[str, Any] | None = None,
        false_signal_check: dict[str, Any] | None = None,
        confidence_adjustments: dict[str, Any] | None = None,
        approval_result: dict[str, Any] | None = None,
        ai_explanation: dict[str, Any] | None = None,
        trade_outcome: str | None = None,
        pnl: float | None = None,
        screenshot_id: str | None = None,
        db_session: Any = None,
    ) -> dict[str, Any]:
        """Record a decision dataset entry."""
        record_id = _new_id()
        timestamp = _now()

        record = {
            "id": record_id,
            "symbol": symbol,
            "timestamp": timestamp,
            "decision": (decision_snap or {}).get("decision", "NO_TRADE"),
            "direction": (decision_snap or {}).get("direction", "WAIT"),
            "score": (decision_snap or {}).get("score"),
            "confidence": (decision_snap or {}).get("confidence"),
            "trade_quality_grade": (trade_quality or {}).get("grade") if trade_quality else None,
            "trade_quality_score": (trade_quality or {}).get("total_score") if trade_quality else None,
            "mtf_agreement_percent": (mtf_agreement or {}).get("agreement_percent") if mtf_agreement else None,
            "detailed_confidence": json.dumps(detailed_confidence) if detailed_confidence else None,
            "signal_validations": json.dumps(signal_validations) if signal_validations else None,
            "false_signal_detections": json.dumps(false_signal_check) if false_signal_check else None,
            "dynamic_adjustments": json.dumps(confidence_adjustments) if confidence_adjustments else None,
            "trade_approval": json.dumps(approval_result) if approval_result else None,
            "ai_explanation": json.dumps(ai_explanation) if ai_explanation else None,
            "indicators_snapshot": json.dumps(indicator_snap) if indicator_snap else None,
            "market_context": json.dumps(context_snap) if context_snap else None,
            "trade_outcome": trade_outcome,
            "pnl": pnl,
            "screenshot_id": screenshot_id,
            "created_at": timestamp,
        }

        # Persist via database if db_session provided
        if db_session is not None:
            try:
                db_session.execute(
                    "INSERT INTO ai_decision_training_dataset (id, symbol, timestamp, decision, score, confidence, "
                    "trade_quality_grade, trade_quality_score, mtf_agreement_percent, detailed_confidence, "
                    "signal_validations, false_signal_detections, dynamic_adjustments, trade_approval, "
                    "ai_explanation, indicators_snapshot, market_context, trade_outcome, pnl, screenshot_id, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        record["id"], record["symbol"], record["timestamp"], record["decision"],
                        record["score"], record["confidence"], record["trade_quality_grade"],
                        record["trade_quality_score"], record["mtf_agreement_percent"],
                        record["detailed_confidence"], record["signal_validations"],
                        record["false_signal_detections"], record["dynamic_adjustments"],
                        record["trade_approval"], record["ai_explanation"],
                        record["indicators_snapshot"], record["market_context"],
                        record["trade_outcome"], record["pnl"], record["screenshot_id"],
                        record["created_at"],
                    ),
                )
                db_session.commit()
            except Exception:
                if db_session:
                    db_session.rollback()

        return record

    @staticmethod
    def get_stats(db_session: Any = None) -> dict[str, Any]:
        """Get dataset statistics."""
        stats = {
            "total_records": 0,
            "by_decision": {},
            "by_grade": {},
            "by_outcome": {},
            "latest_timestamp": None,
        }
        if db_session is None:
            return stats
        try:
            rows = db_session.execute("SELECT decision, trade_quality_grade, trade_outcome, created_at FROM ai_decision_training_dataset").fetchall()
            stats["total_records"] = len(rows)
            for row in rows:
                if row[0]:
                    stats["by_decision"][row[0]] = stats["by_decision"].get(row[0], 0) + 1
                if row[1]:
                    stats["by_grade"][row[1]] = stats["by_grade"].get(row[1], 0) + 1
                if row[2]:
                    stats["by_outcome"][row[2]] = stats["by_outcome"].get(row[2], 0) + 1
                if row[3] and (stats["latest_timestamp"] is None or row[3] > stats["latest_timestamp"]):
                    stats["latest_timestamp"] = row[3]
        except Exception:
            pass
        return stats

    @staticmethod
    def export_records(db_session: Any = None, limit: int = 1000, offset: int = 0) -> list[dict[str, Any]]:
        """Export records for model training."""
        if db_session is None:
            return []
        try:
            rows = db_session.execute(
                "SELECT * FROM ai_decision_training_dataset ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            columns = [desc[0] for desc in db_session.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception:
            return []
