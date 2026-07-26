"""
Rollback Framework — manages rollback audit trail, history, and governance.
Never automatic. Always requires human review.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"rb_{uuid.uuid4().hex[:12]}"


ROLLBACK_REASONS = [
    "performance_degradation",
    "drawdown_exceeded",
    "calibration_drift",
    "regime_mismatch",
    "false_signal_increase",
    "human_decision",
    "challenger_superseded",
]


class RollbackGovernor:
    """Governs rollback operations. Never automatic — always requires human approval."""

    @staticmethod
    def request_rollback(
        db_conn: Any,
        model_id: str,
        reason: str,
        requested_by: str = "",
    ) -> dict[str, Any]:
        """Create a rollback request for human review."""
        model = db_conn.execute("SELECT * FROM model_registry WHERE id = ?", (model_id,)).fetchone()
        if not model:
            raise ValueError(f"Model {model_id} not found")

        model = dict(model)
        if model["status"] != "champion":
            raise ValueError(f"Model is {model['status']}, not champion. Cannot roll back non-champion models.")

        # Find the previous champion
        prev_champion = db_conn.execute(
            "SELECT * FROM model_registry WHERE id IN ("
            "SELECT model_id FROM model_promotion_log WHERE action LIKE '%champion%' AND model_id != ? "
            "ORDER BY created_at DESC LIMIT 1"
            ")",
            (model_id,),
        ).fetchone()

        now = _now()
        rid = _new_id()

        # Record as promotion log entry with special action
        db_conn.execute(
            "INSERT INTO model_promotion_log (id, model_id, action, previous_status, new_status, reason, "
            "human_reviewed, reviewer_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (rid, model_id, "rollback_request", model["status"], "rolled_back", reason, 0, requested_by, now),
        )
        db_conn.commit()

        return {
            "rollback_id": rid,
            "model_id": model_id,
            "model_name": model["name"],
            "model_version": model["version"],
            "reason": reason,
            "requested_by": requested_by or "system",
            "status": "pending_review",
            "previous_champion_id": prev_champion["id"] if prev_champion else None,
            "previous_champion_name": prev_champion["name"] if prev_champion else None,
            "created_at": now,
        }

    @staticmethod
    def approve_rollback(
        db_conn: Any,
        rollback_id: str,
        reviewer_id: str = "",
    ) -> dict[str, Any]:
        """Approve a rollback request. Only this can change status to rolled_back."""
        log = db_conn.execute(
            "SELECT * FROM model_promotion_log WHERE id = ? AND action = 'rollback_request'",
            (rollback_id,),
        ).fetchone()
        if not log:
            raise ValueError(f"Rollback request {rollback_id} not found")

        log = dict(log)
        model_id = log["model_id"]

        # Find previous champion to restore
        prev_champion = db_conn.execute(
            "SELECT * FROM model_registry WHERE status = 'archived' AND id != ? "
            "ORDER BY updated_at DESC LIMIT 1",
            (model_id,),
        ).fetchone()

        now = _now()

        # Mark current champion as rolled_back
        db_conn.execute(
            "UPDATE model_registry SET status = 'rolled_back', updated_at = ? WHERE id = ?",
            (now, model_id),
        )

        # Update the log entry
        db_conn.execute(
            "UPDATE model_promotion_log SET human_reviewed = 1, reviewer_id = ?, new_status = 'rolled_back' WHERE id = ?",
            (reviewer_id, rollback_id),
        )

        # Record immediate rollback action
        rb_id = _new_id()
        db_conn.execute(
            "INSERT INTO model_promotion_log (id, model_id, action, previous_status, new_status, reason, "
            "human_reviewed, reviewer_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (rb_id, model_id, "rollback_executed", "champion", "rolled_back",
             f"Rollback approved by {reviewer_id}", 1, reviewer_id, now),
        )

        # Restore previous champion if available
        restored = None
        if prev_champion:
            db_conn.execute(
                "UPDATE model_registry SET status = 'champion', updated_at = ? WHERE id = ?",
                (now, prev_champion["id"]),
            )
            restored = dict(prev_champion)
            restored["status"] = "champion"

        db_conn.commit()

        return {
            "success": True,
            "rollback_id": rollback_id,
            "rolled_back_model_id": model_id,
            "restored_champion": restored,
            "approved_by": reviewer_id,
            "timestamp": now,
        }

    @staticmethod
    def get_rollback_history(db_conn: Any) -> list[dict[str, Any]]:
        """Get all rollback-related log entries."""
        rows = db_conn.execute(
            "SELECT * FROM model_promotion_log WHERE action LIKE '%rollback%' ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]
