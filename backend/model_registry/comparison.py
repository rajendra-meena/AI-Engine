"""
Champion-Challenger Comparison — side-by-side decision comparison and promotion recommendations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from performance.advanced_metrics import compute_sharpe, compute_sortino


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"cmp_{uuid.uuid4().hex[:12]}"


class ModelComparisonEngine:
    """Compares champion vs challenger decisions and performance."""

    @staticmethod
    def compare_decisions(
        champion_predictions: list[dict[str, Any]],
        challenger_predictions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compare decisions between champion and challenger."""
        if not champion_predictions or not challenger_predictions:
            return {"same_signal_pct": 0, "different_signal_pct": 0, "total_comparisons": 0}

        total = min(len(champion_predictions), len(challenger_predictions))
        same = 0
        champion_better_entry = 0
        champion_better_exit = 0
        confidence_diffs: list[float] = []

        for i in range(total):
            champ_dec = champion_predictions[i].get("decision", "")
            chall_dec = challenger_predictions[i].get("decision", "")

            if champ_dec == chall_dec:
                same += 1

            champ_conf = champion_predictions[i].get("confidence", 0) or 0
            chall_conf = challenger_predictions[i].get("confidence", 0) or 0
            confidence_diffs.append(champ_conf - chall_conf)

            # Entry quality comparison
            champ_entry = champion_predictions[i].get("entry_accuracy", 50) or 50
            chall_entry = challenger_predictions[i].get("entry_accuracy", 50) or 50
            if champ_entry > chall_entry:
                champion_better_entry += 1

            champ_exit = champion_predictions[i].get("exit_quality", 50) or 50
            chall_exit = challenger_predictions[i].get("exit_quality", 50) or 50
            if champ_exit > chall_exit:
                champion_better_exit += 1

        same_pct = round((same / total) * 100, 1)
        diff_pct = round(((total - same) / total) * 100, 1)
        avg_conf_diff = round(sum(confidence_diffs) / len(confidence_diffs), 1) if confidence_diffs else 0

        return {
            "total_comparisons": total,
            "same_signal_pct": same_pct,
            "different_signal_pct": diff_pct,
            "champion_better_entry_pct": round((champion_better_entry / total) * 100, 1) if total > 0 else 0,
            "champion_better_exit_pct": round((champion_better_exit / total) * 100, 1) if total > 0 else 0,
            "avg_confidence_difference": avg_conf_diff,
        }

    @staticmethod
    def compute_promotion_recommendation(
        champion_metrics: dict[str, Any],
        challenger_metrics: dict[str, Any],
        champion_predictions: list[dict[str, Any]] | None = None,
        challenger_predictions: list[dict[str, Any]] | None = None,
        walk_forward_score: float | None = None,
    ) -> dict[str, Any]:
        """Evaluate if challenger should replace champion."""
        reasons: list[str] = []
        warnings: list[str] = []
        gates: list[dict[str, Any]] = []

        champ_trades = champion_metrics.get("total_trades", 0) or 0
        chall_trades = challenger_metrics.get("total_trades", 0) or 0

        # Gate 1: Minimum trade count (30)
        min_trades = 30
        g1 = chall_trades >= min_trades
        gates.append({"name": "minimum_trades", "passed": g1, "value": chall_trades, "threshold": min_trades,
                       "detail": f"Challenger has {chall_trades} trades" if g1 else f"Only {chall_trades}/{min_trades} trades"})
        if not g1:
            warnings.append(f"Insufficient challenger trades: {chall_trades}/{min_trades}")

        # Gate 2: Better Sharpe
        champ_sharpe = champion_metrics.get("sharpe_ratio", 0) or 0
        chall_sharpe = challenger_metrics.get("sharpe_ratio", 0) or 0
        g2 = chall_sharpe > champ_sharpe
        gates.append({"name": "better_sharpe", "passed": g2, "value": chall_sharpe, "threshold": champ_sharpe,
                       "detail": f"Challenger Sharpe {chall_sharpe:.2f} vs Champion {champ_sharpe:.2f}"})
        if g2:
            reasons.append(f"Better Sharpe: {chall_sharpe:.2f} vs {champ_sharpe:.2f}")

        # Gate 3: Lower drawdown
        champ_dd = champion_metrics.get("max_drawdown", 100) or 100
        chall_dd = challenger_metrics.get("max_drawdown", 100) or 100
        g3 = chall_dd <= champ_dd * 1.2  # within 20% degradation
        gates.append({"name": "drawdown_stable", "passed": g3, "value": chall_dd, "threshold": champ_dd,
                       "detail": f"Challenger DD {chall_dd:.1f} vs Champion {champ_dd:.1f}"})
        if not g3:
            warnings.append(f"Drawdown increased: {chall_dd:.1f} vs {champ_dd:.1f}")

        # Gate 4: Walk-forward pass
        g4 = walk_forward_score is None or walk_forward_score >= 60
        gates.append({"name": "walk_forward", "passed": g4, "value": walk_forward_score or 0, "threshold": 60,
                       "detail": f"Walk-forward score: {walk_forward_score:.1f}" if walk_forward_score else "Not tested"})
        if not g4:
            warnings.append(f"Walk-forward score {walk_forward_score:.1f} < 60")

        # Gate 5: Better calibration
        champ_cal = champion_metrics.get("calibration_score", 50) or 50
        chall_cal = challenger_metrics.get("calibration_score", 50) or 50
        g5 = chall_cal >= champ_cal * 0.9
        gates.append({"name": "calibration", "passed": g5, "value": chall_cal, "threshold": champ_cal,
                       "detail": f"Challenger cal {chall_cal:.1f} vs Champion {champ_cal:.1f}"})

        # Gate 6: Better profit factor
        champ_pf = champion_metrics.get("profit_factor", 0) or 0
        chall_pf = challenger_metrics.get("profit_factor", 0) or 0
        g6 = chall_pf >= champ_pf * 0.85
        gates.append({"name": "profit_factor", "passed": g6, "value": chall_pf, "threshold": champ_pf,
                       "detail": f"Challenger PF {chall_pf:.2f} vs Champion {champ_pf:.2f}"})
        if g6 and chall_pf > champ_pf:
            reasons.append(f"Better profit factor: {chall_pf:.2f} vs {champ_pf:.2f}")

        all_passed = all(g["passed"] for g in gates)
        pass_count = sum(1 for g in gates if g["passed"])
        score = round((pass_count / len(gates)) * 100)

        if all_passed and score >= 80:
            decision = "promote"
        elif score >= 50:
            decision = "more_data_required"
        elif warnings:
            decision = "keep_champion"
        else:
            decision = "reject_challenger"

        return {
            "decision": decision,
            "score": score,
            "gates": gates,
            "reasons": reasons,
            "warnings": warnings,
            "human_review_required": decision in ("promote", "reject_challenger"),
        }

    @staticmethod
    def store_comparison(db_conn: Any, champion_id: str, challenger_id: str,
                         comparison: dict[str, Any], metrics: dict[str, Any]) -> str:
        """Persist comparison result."""
        cid = _new_id()
        now = _now()
        try:
            db_conn.execute(
                "INSERT INTO model_comparison (id, champion_model_id, challenger_model_id, "
                "same_signal_pct, different_signal_pct, champion_win_rate, challenger_win_rate, "
                "champion_sharpe, challenger_sharpe, confidence_diff, comparison_date, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, champion_id, challenger_id,
                 comparison.get("same_signal_pct"), comparison.get("different_signal_pct"),
                 metrics.get("champion_win_rate"), metrics.get("challenger_win_rate"),
                 metrics.get("champion_sharpe"), metrics.get("challenger_sharpe"),
                 comparison.get("avg_confidence_difference"), now[:10], now),
            )
            db_conn.commit()
        except Exception:
            db_conn.rollback()
        return cid
