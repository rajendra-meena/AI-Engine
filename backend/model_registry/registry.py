"""
Model Registry — manages model metadata, versioning, status lifecycle.
Supports states: draft, validation, candidate, champion, challenger, archived, rolled_back.
"""

from __future__ import annotations

import uuid
import json
from datetime import datetime, timezone
from typing import Any


MODEL_STATES = ["draft", "validation", "candidate", "champion", "challenger", "archived", "rolled_back"]
VALID_TRANSITIONS = {
    "draft": ["validation"],
    "validation": ["candidate", "draft"],
    "candidate": ["champion", "challenger", "archived"],
    "challenger": ["champion", "candidate", "archived"],
    "champion": ["rolled_back", "archived"],
    "rolled_back": ["champion", "archived"],
    "archived": [],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"mdl_{uuid.uuid4().hex[:12]}"


class ModelRegistry:
    """Manages model lifecycle: registration, versioning, status transitions."""

    @staticmethod
    def register(
        db_conn: Any,
        name: str,
        version: str,
        model_type: str | None = None,
        algorithm: str | None = None,
        description: str | None = None,
        feature_set_version: str | None = None,
        indicator_version: str | None = None,
        regime_compatibility: list[str] | None = None,
        strategy_compatibility: list[str] | None = None,
        parent_model_id: str | None = None,
        dataset_reference: str | None = None,
        hyperparameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a new model in draft state."""
        mid = _new_id()
        now = _now()

        record = {
            "id": mid,
            "name": name,
            "description": description or "",
            "version": version,
            "status": "draft",
            "model_type": model_type or "",
            "algorithm": algorithm or "",
            "feature_set_version": feature_set_version or "",
            "indicator_version": indicator_version or "",
            "regime_compatibility": json.dumps(regime_compatibility or []),
            "strategy_compatibility": json.dumps(strategy_compatibility or []),
            "parent_model_id": parent_model_id or "",
            "dataset_reference": dataset_reference or "",
            "hyperparameters": json.dumps(hyperparameters or {}),
            "training_timestamp": now,
            "created_at": now,
            "updated_at": now,
        }

        try:
            db_conn.execute(
                "INSERT INTO model_registry (id, name, description, version, status, model_type, algorithm, "
                "feature_set_version, indicator_version, regime_compatibility, strategy_compatibility, "
                "parent_model_id, dataset_reference, hyperparameters, training_timestamp, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(record.values()),
            )
            db_conn.commit()
        except Exception:
            db_conn.rollback()
            raise

        # Record lineage
        ModelRegistry._record_lineage(db_conn, mid, parent_model_id, "created", version_before="", version_after=version)

        return record

    @staticmethod
    def set_status(db_conn: Any, model_id: str, new_status: str, reason: str = "") -> dict[str, Any] | None:
        """Transition model to a new status with validation."""
        if new_status not in MODEL_STATES:
            raise ValueError(f"Invalid status: {new_status}")

        row = db_conn.execute("SELECT * FROM model_registry WHERE id = ?", (model_id,)).fetchone()
        if not row:
            return None

        current = dict(row)
        old_status = current["status"]

        allowed = VALID_TRANSITIONS.get(old_status, [])
        if new_status not in allowed:
            raise ValueError(f"Cannot transition from {old_status} to {new_status}. Allowed: {allowed}")

        # If promoting to champion, demote existing champion
        if new_status == "champion":
            old_champ = db_conn.execute(
                "SELECT id FROM model_registry WHERE status = 'champion' AND id != ?", (model_id,)
            ).fetchone()
            if old_champ:
                ModelRegistry.set_status(db_conn, old_champ["id"], "archived", f"Superseded by {model_id}")

        now = _now()
        db_conn.execute("UPDATE model_registry SET status = ?, updated_at = ? WHERE id = ?",
                        (new_status, now, model_id))
        db_conn.commit()

        # Record promotion log
        log_id = _new_id()
        db_conn.execute(
            "INSERT INTO model_promotion_log (id, model_id, action, previous_status, new_status, reason, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (log_id, model_id, f"{old_status}->{new_status}", old_status, new_status, reason, now),
        )
        db_conn.commit()

        # Record lineage
        ModelRegistry._record_lineage(db_conn, model_id, current.get("parent_model_id"),
                                      f"status_change:{old_status}->{new_status}",
                                      version_before=current.get("version", ""),
                                      version_after=current.get("version", ""))

        return {**current, "status": new_status, "updated_at": now}

    @staticmethod
    def get_model(db_conn: Any, model_id: str) -> dict[str, Any] | None:
        row = db_conn.execute("SELECT * FROM model_registry WHERE id = ?", (model_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_champion(db_conn: Any) -> dict[str, Any] | None:
        row = db_conn.execute("SELECT * FROM model_registry WHERE status = 'champion' ORDER BY updated_at DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_challenger(db_conn: Any) -> dict[str, Any] | None:
        row = db_conn.execute("SELECT * FROM model_registry WHERE status = 'challenger' ORDER BY updated_at DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    @staticmethod
    def list_models(db_conn: Any, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            rows = db_conn.execute("SELECT * FROM model_registry WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = db_conn.execute("SELECT * FROM model_registry ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get_history(db_conn: Any, model_id: str | None = None) -> list[dict[str, Any]]:
        if model_id:
            rows = db_conn.execute(
                "SELECT * FROM model_promotion_log WHERE model_id = ? ORDER BY created_at DESC", (model_id,)
            ).fetchall()
        else:
            rows = db_conn.execute("SELECT * FROM model_promotion_log ORDER BY created_at DESC LIMIT 100").fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get_lineage(db_conn: Any, model_id: str) -> list[dict[str, Any]]:
        rows = db_conn.execute(
            "SELECT * FROM model_lineage WHERE model_id = ? OR parent_model_id = ? ORDER BY created_at ASC",
            (model_id, model_id),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get_comparison(db_conn: Any, champion_id: str | None = None, challenger_id: str | None = None) -> dict[str, Any] | None:
        if champion_id and challenger_id:
            row = db_conn.execute(
                "SELECT * FROM model_comparison WHERE champion_model_id = ? AND challenger_model_id = ? ORDER BY created_at DESC LIMIT 1",
                (champion_id, challenger_id),
            ).fetchone()
        else:
            row = db_conn.execute("SELECT * FROM model_comparison ORDER BY created_at DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    @staticmethod
    def save_evaluation(db_conn: Any, model_id: str, eval_type: str, metrics: dict[str, Any]) -> str:
        eid = _new_id()
        now = _now()
        db_conn.execute(
            "INSERT INTO model_evaluation_record (id, model_id, evaluation_type, win_rate, profit_factor, "
            "max_drawdown, sharpe_ratio, sortino_ratio, calmar_ratio, expectancy, total_trades, "
            "stability_score, calibration_score, regime_performance, strategy_performance, "
            "walk_forward_score, oos_win_rate, oos_sharpe, generalization_score, evaluated_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (eid, model_id, eval_type, metrics.get("win_rate"), metrics.get("profit_factor"),
             metrics.get("max_drawdown"), metrics.get("sharpe_ratio"), metrics.get("sortino_ratio"),
             metrics.get("calmar_ratio"), metrics.get("expectancy"), metrics.get("total_trades"),
             metrics.get("stability_score"), metrics.get("calibration_score"),
             json.dumps(metrics.get("regime_performance", {})),
             json.dumps(metrics.get("strategy_performance", {})),
             metrics.get("walk_forward_score"), metrics.get("oos_win_rate"),
             metrics.get("oos_sharpe"), metrics.get("generalization_score"), now, now),
        )
        db_conn.commit()
        return eid

    @staticmethod
    def _record_lineage(db_conn: Any, model_id: str, parent_id: str | None, event_type: str,
                        version_before: str = "", version_after: str = "") -> None:
        lid = _new_id()
        now = _now()
        try:
            db_conn.execute(
                "INSERT INTO model_lineage (id, model_id, parent_model_id, event_type, event_detail, "
                "version_before, version_after, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (lid, model_id, parent_id or "", event_type, "", version_before, version_after, now),
            )
            db_conn.commit()
        except Exception:
            pass
