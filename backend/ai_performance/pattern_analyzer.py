"""
Pattern Performance Analyzer — tracks and analyzes performance by pattern type.

Extracts pattern names from prediction_journal.pattern_snapshot JSON.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"pp_{uuid.uuid4().hex[:12]}"


TRACKED_PATTERNS = [
    "bull_flag", "bear_flag", "double_top", "double_bottom",
    "triangle", "breakout", "fake_breakout", "liquidity_grab", "gap_fill",
]


class PatternPerformanceAnalyzer:
    """Analyzes trade performance grouped by detected pattern."""

    @staticmethod
    def compute_pattern_performance(
        predictions: list[dict[str, Any]],
        outcomes: dict[str, dict[str, Any]] | None = None,
        feedbacks: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """For each pattern, compute win rate, avg return, failure rate, avg duration."""
        pattern_trades: dict[str, list[dict[str, Any]]] = {p: [] for p in TRACKED_PATTERNS}
        pattern_trades["other"] = []

        for p in predictions:
            patterns_found = PatternPerformanceAnalyzer.extract_patterns_from_snapshot(
                p.get("pattern_snapshot")
            )
            outcome = (outcomes or {}).get(p.get("id") or p.get("prediction_id", ""))
            feedback = (feedbacks or {}).get(p.get("id") or p.get("prediction_id", ""))
            merged = dict(p)
            if outcome:
                merged.update(outcome)
            if feedback:
                merged.update(feedback)

            if patterns_found:
                for pat in patterns_found:
                    if pat in pattern_trades:
                        pattern_trades[pat].append(merged)
            else:
                pattern_trades["other"].append(merged)

        results = []
        for pat_name, trades in pattern_trades.items():
            if not trades:
                continue
            total = len(trades)
            wins = [t for t in trades if (t.get("actual_return") or 0) > 0]
            losses = [t for t in trades if (t.get("actual_return") or 0) <= 0]
            win_count = len(wins)
            loss_count = len(losses)
            win_rate = round((win_count / total) * 100, 1) if total > 0 else 0.0
            returns = [t.get("actual_return", 0) for t in trades]
            avg_return = round(sum(returns) / len(returns), 2) if returns else 0.0
            durations = [
                (t.get("holding_duration") or t.get("duration_minutes", 0)) / 60
                for t in trades if t.get("holding_duration") or t.get("duration_minutes")
            ]
            avg_dur = round(sum(durations) / len(durations), 1) if durations else 0.0
            failure_rate = round((loss_count / total) * 100, 1) if total > 0 else 0.0

            results.append({
                "pattern_name": pat_name,
                "pattern_type": "technical",
                "total_occurrences": total,
                "win_count": win_count,
                "loss_count": loss_count,
                "win_rate": win_rate,
                "avg_return": avg_return,
                "failure_rate": failure_rate,
                "avg_duration_hours": avg_dur,
            })

        results.sort(key=lambda r: r["total_occurrences"], reverse=True)
        return results

    @staticmethod
    def extract_patterns_from_snapshot(pattern_snapshot_json: str | None) -> list[str]:
        """Parse pattern_snapshot JSON and extract pattern names."""
        if not pattern_snapshot_json:
            return []
        try:
            data = json.loads(pattern_snapshot_json)
        except (json.JSONDecodeError, TypeError):
            return []

        patterns = []
        if isinstance(data, dict):
            # Handle various JSON shapes
            for key in ("candlestick_patterns", "chart_patterns", "breakout_patterns"):
                items = data.get(key, [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get("name", item.get("pattern", ""))
                            if name:
                                patterns.append(str(name).lower().replace(" ", "_"))
            # Check for strongest_pattern field
            strongest = data.get("strongest_pattern")
            if strongest and isinstance(strongest, str):
                normalized = strongest.lower().replace(" ", "_")
                if normalized not in patterns:
                    patterns.append(normalized)
            # Check for flat pattern_name field
            pname = data.get("pattern_name")
            if pname and isinstance(pname, str):
                normalized = pname.lower().replace(" ", "_")
                if normalized not in patterns:
                    patterns.append(normalized)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    name = item.get("name", item.get("pattern", ""))
                    if name:
                        patterns.append(str(name).lower().replace(" ", "_"))

        return patterns

    @staticmethod
    def snapshot_patterns(db_conn: Any) -> int:
        """Compute and persist current pattern performance."""
        from learning.engine import _get_db as get_learning_db
        try:
            ldb = get_learning_db()
            rows = ldb.execute(
                "SELECT pj.*, po.*, tf.* FROM prediction_journal pj "
                "LEFT JOIN prediction_outcome po ON po.prediction_id = pj.id "
                "LEFT JOIN trade_feedback tf ON tf.prediction_id = pj.id "
                "ORDER BY pj.created_at DESC"
            ).fetchall()
            predictions = [dict(r) for r in rows]
            ldb.close()
        except Exception:
            predictions = []

        outcomes: dict[str, dict[str, Any]] = {}
        feedbacks: dict[str, dict[str, Any]] = {}
        for p in predictions:
            pid = p.get("id") or p.get("prediction_id", "")
            if any(k in p for k in ("actual_return", "max_favorable_excursion")):
                outcomes[pid] = p
            if any(k in p for k in ("entry_slippage", "gross_pnl")):
                feedbacks[pid] = p

        patterns = PatternPerformanceAnalyzer.compute_pattern_performance(predictions, outcomes, feedbacks)
        date_str = _now()[:10]
        count = 0
        for pat in patterns:
            pid = _new_id()
            try:
                db_conn.execute(
                    "INSERT OR IGNORE INTO ai_perf_pattern_performance "
                    "(id, pattern_name, total_occurrences, win_count, loss_count, "
                    "win_rate, avg_return, avg_duration_hours, failure_rate, observation_date) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        pid, pat["pattern_name"], pat["total_occurrences"],
                        pat["win_count"], pat["loss_count"], pat["win_rate"],
                        pat["avg_return"], pat["avg_duration_hours"],
                        pat["failure_rate"], date_str,
                    ),
                )
                count += 1
            except Exception:
                pass
        db_conn.commit()
        return count
