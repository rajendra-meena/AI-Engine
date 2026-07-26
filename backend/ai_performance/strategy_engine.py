"""
Strategy Performance Engine — evaluates every strategy independently.

Computes per-strategy metrics: win rate, profit factor, expectancy, sharpe, drawdown.
Reuses backend/performance/advanced_metrics for statistical computations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from performance.advanced_metrics import compute_sharpe, compute_sortino, compute_calmar
from performance.advanced_metrics import compute_recovery_factor, compute_streaks


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"str_{uuid.uuid4().hex[:12]}"


SUPPORTED_STRATEGIES = [
    "trend_following", "breakout", "reversal", "pullback",
    "range", "momentum", "scalping",
]


class StrategyPerformanceEngine:
    """Computes per-strategy performance metrics."""

    @staticmethod
    def compute_strategy_metrics(
        strategy_id: str,
        trades: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute full metrics for a single strategy."""
        if not trades:
            return {
                "strategy_id": strategy_id,
                "strategy_name": strategy_id.replace("_", " ").title() if strategy_id != "unknown" else "Unknown",
                "total_trades": 0, "win_rate": 0, "profit_factor": 0, "expectancy": 0,
                "sharpe_ratio": None, "sortino_ratio": None, "calmar_ratio": None,
                "recovery_factor": None, "max_drawdown": 0, "avg_holding_hours": 0,
                "avg_r_multiple": 0, "largest_win": 0, "largest_loss": 0,
                "consecutive_wins": 0, "consecutive_losses": 0,
            }

        wins = [t for t in trades if (t.get("actual_return") or 0) > 0]
        losses = [t for t in trades if (t.get("actual_return") or 0) <= 0]
        total = len(trades)
        win_count = len(wins)
        loss_count = len(losses)

        win_rate = (win_count / total * 100) if total > 0 else 0

        gross_profit = sum(t.get("actual_return", 0) for t in wins)
        gross_loss = abs(sum(t.get("actual_return", 0) for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)

        returns = [t.get("actual_return", 0) for t in trades]
        avg_return = sum(returns) / len(returns) if returns else 0
        expectancy = avg_return

        sharpe = compute_sharpe(returns)
        sortino = compute_sortino(returns)
        calmar = None

        total_return_pct = (sum(returns) / abs(trades[0].get("entry_price", 1))) * 100 if trades and trades[0].get("entry_price") else 0
        max_dd = 0
        peak = 0
        for r in returns:
            peak = max(peak, r)
            dd = peak - r
            max_dd = max(max_dd, dd)
        max_dd_pct = (max_dd / abs(trades[0].get("entry_price", 1))) * 100 if trades and trades[0].get("entry_price") else 0

        if gross_profit > 0 and max_dd > 0:
            calmar = compute_calmar(returns, total_return_pct, max_dd_pct)
        recovery = compute_recovery_factor(gross_profit - gross_loss, max_dd) if max_dd > 0 else None

        streaks = compute_streaks(returns)

        holding_hours_list = [t.get("holding_duration") or t.get("duration_minutes", 0) / 60 for t in trades]
        avg_hours = sum(holding_hours_list) / len(holding_hours_list) if holding_hours_list else 0

        r_multiples = [t.get("r_multiple", 0) for t in trades if t.get("r_multiple")]
        avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0

        name = strategy_id.replace("_", " ").title() if strategy_id != "unknown" else "Unknown"

        return {
            "strategy_id": strategy_id,
            "strategy_name": name,
            "total_trades": total,
            "win_rate": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "expectancy": round(expectancy, 2),
            "sharpe_ratio": round(sharpe, 2) if sharpe is not None else None,
            "sortino_ratio": round(sortino, 2) if sortino is not None else None,
            "calmar_ratio": round(calmar, 2) if calmar is not None else None,
            "recovery_factor": round(recovery, 2) if recovery is not None else None,
            "max_drawdown": round(max_dd_pct, 2),
            "avg_holding_hours": round(avg_hours, 1),
            "avg_r_multiple": round(avg_r, 2),
            "largest_win": round(max(returns) if returns else 0, 2),
            "largest_loss": round(min(returns) if returns else 0, 2),
            "consecutive_wins": streaks.get("max_consecutive_wins", 0),
            "consecutive_losses": streaks.get("max_consecutive_losses", 0),
        }

    @staticmethod
    def compute_all_strategies(
        predictions: list[dict[str, Any]],
        outcomes: dict[str, dict[str, Any]] | None = None,
        feedbacks: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Group predictions by strategy_id and compute metrics per strategy."""
        groups: dict[str, list[dict[str, Any]]] = {}
        for p in predictions:
            sid = p.get("strategy_id") or "unknown"
            if sid not in groups:
                groups[sid] = []
            outcome = (outcomes or {}).get(p.get("id") or p.get("prediction_id", ""))
            feedback = (feedbacks or {}).get(p.get("id") or p.get("prediction_id", ""))
            merged = dict(p)
            if outcome:
                merged.update(outcome)
            if feedback:
                merged.update(feedback)
            groups[sid].append(merged)

        results = []
        for sid, trades in groups.items():
            results.append(StrategyPerformanceEngine.compute_strategy_metrics(sid, trades))

        results.sort(key=lambda r: r.get("win_rate", 0), reverse=True)
        return results

    @staticmethod
    def snapshot_strategies(db_conn: Any) -> int:
        """Compute and persist current strategy metrics."""
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

        strategies = StrategyPerformanceEngine.compute_all_strategies(predictions)
        date_str = _now()[:10]
        count = 0
        for s in strategies:
            sid = _new_id()
            try:
                db_conn.execute(
                    "INSERT OR IGNORE INTO ai_perf_strategy_snapshot "
                    "(id, strategy_id, strategy_name, total_trades, win_rate, profit_factor, "
                    "expectancy, sharpe_ratio, recovery_factor, max_drawdown, avg_holding_hours, snapshot_date) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        sid, s["strategy_id"], s["strategy_name"], s["total_trades"],
                        s["win_rate"], s["profit_factor"], s["expectancy"],
                        s["sharpe_ratio"], s["recovery_factor"], s["max_drawdown"],
                        s["avg_holding_hours"], date_str,
                    ),
                )
                count += 1
            except Exception:
                pass
        db_conn.commit()
        return count
