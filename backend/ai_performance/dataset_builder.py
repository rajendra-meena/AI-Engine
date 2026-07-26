"""
Continuous Learning Dataset Builder — builds evaluation datasets for offline model training.

JOINs prediction_journal + prediction_outcome + trade_feedback + trade_evaluation.
For offline model retraining only. No online self-training.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any


class AIPerformanceDatasetBuilder:
    """Builds and exports evaluation datasets for offline training."""

    @staticmethod
    def build_evaluation_dataset(
        db_conn: Any,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Build enriched dataset joining all evaluation tables."""
        try:
            rows = db_conn.execute(
                """
                SELECT
                    pj.id as prediction_id, pj.symbol, pj.timestamp, pj.interval,
                    pj.decision, pj.direction, pj.score, pj.confidence, pj.risk_score,
                    pj.entry_price, pj.stop_loss, pj.target, pj.risk_reward,
                    pj.strategy_id, pj.market_regime, pj.trend, pj.market_phase,
                    pj.mtf_alignment, pj.volatility, pj.momentum,
                    po.outcome_eod, po.actual_return, po.max_favorable_excursion,
                    po.max_adverse_excursion, po.target_hit, po.stop_loss_hit,
                    po.error_category, po.error_reason, po.maximum_return,
                    po.maximum_drawdown,
                    tf.entry_slippage, tf.exit_slippage, tf.gross_pnl, tf.net_pnl,
                    tf.actual_risk, tf.actual_rr, tf.holding_duration, tf.exit_reason,
                    te.overall_score, te.outcome_class, te.entry_accuracy,
                    te.exit_quality, te.sl_quality, te.target_quality,
                    te.mfe_mae_ratio, te.slippage_impact
                FROM prediction_journal pj
                LEFT JOIN prediction_outcome po ON po.prediction_id = pj.id
                LEFT JOIN trade_feedback tf ON tf.prediction_id = pj.id
                LEFT JOIN ai_perf_trade_evaluation te ON te.prediction_id = pj.id
                ORDER BY pj.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def export_dataset(
        db_conn: Any,
        fmt: str = "json",
        limit: int = 1000,
    ) -> str | bytes:
        """Export dataset as JSON string or CSV bytes."""
        records = AIPerformanceDatasetBuilder.build_evaluation_dataset(db_conn, limit)

        if fmt == "csv":
            if not records:
                return b""
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
            return output.getvalue().encode("utf-8")
        else:
            return json.dumps(records, default=str, indent=2)

    @staticmethod
    def get_dataset_stats(db_conn: Any) -> dict[str, Any]:
        """Get stats about the evaluation dataset."""
        stats = {
            "total_records": 0,
            "with_outcome": 0,
            "with_feedback": 0,
            "with_evaluation": 0,
            "by_outcome_class": {},
            "by_decision": {},
            "date_range": {"earliest": None, "latest": None},
        }
        try:
            row = db_conn.execute("SELECT COUNT(*) as c FROM prediction_journal").fetchone()
            stats["total_records"] = row["c"] if row else 0

            row = db_conn.execute("SELECT COUNT(*) as c FROM prediction_outcome").fetchone()
            stats["with_outcome"] = row["c"] if row else 0

            row = db_conn.execute("SELECT COUNT(*) as c FROM trade_feedback").fetchone()
            stats["with_feedback"] = row["c"] if row else 0

            row = db_conn.execute("SELECT COUNT(*) as c FROM ai_perf_trade_evaluation").fetchone()
            stats["with_evaluation"] = row["c"] if row else 0

            rows = db_conn.execute(
                "SELECT outcome_class, COUNT(*) as c FROM ai_perf_trade_evaluation GROUP BY outcome_class"
            ).fetchall()
            for r in rows:
                stats["by_outcome_class"][r["outcome_class"]] = r["c"]

            rows = db_conn.execute(
                "SELECT decision, COUNT(*) as c FROM prediction_journal GROUP BY decision"
            ).fetchall()
            for r in rows:
                stats["by_decision"][r["decision"]] = r["c"]

            row = db_conn.execute("SELECT MIN(created_at) as e, MAX(created_at) as l FROM prediction_journal").fetchone()
            if row:
                stats["date_range"]["earliest"] = row["e"]
                stats["date_range"]["latest"] = row["l"]
        except Exception:
            pass

        return stats
