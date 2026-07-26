"""
Regime Performance Analytics — computes win rate, PnL, drawdown per regime.
Uses Phase 57's ai_perf_trade_evaluation and prediction_journal tables.
"""

from __future__ import annotations

from typing import Any


class RegimePerformanceAnalytics:
    """Computes performance metrics grouped by market regime."""

    @staticmethod
    def compute_regime_performance(db_conn: Any) -> dict[str, dict[str, Any]]:
        """Join prediction_journal with outcome, group by regime/market_regime."""
        try:
            rows = db_conn.execute("""
                SELECT
                    pj.regime as regime,
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN po.actual_return > 0 THEN 1 ELSE 0 END) as win_count,
                    SUM(CASE WHEN po.actual_return <= 0 THEN 1 ELSE 0 END) as loss_count,
                    AVG(po.actual_return) as avg_return,
                    COALESCE(SUM(po.actual_return), 0) as net_pnl,
                    AVG(pj.confidence) as avg_confidence,
                    AVG(tf.holding_duration) as avg_holding_minutes,
                    MAX(po.maximum_drawdown) as max_drawdown
                FROM prediction_journal pj
                LEFT JOIN prediction_outcome po ON po.prediction_id = pj.id
                LEFT JOIN trade_feedback tf ON tf.prediction_id = pj.id
                WHERE pj.regime IS NOT NULL AND pj.regime != ''
                GROUP BY pj.regime
            """).fetchall()
        except Exception:
            return {}

        regimes: dict[str, dict[str, Any]] = {}
        for r in rows:
            total = r["total_trades"] or 0
            wins = r["win_count"] or 0
            losses = r["loss_count"] or 0
            win_rate = (wins / total * 100) if total > 0 else 0.0
            gross_profit = sum(
                row["avg_return"] for row in [r] if (row["avg_return"] or 0) > 0
            )
            gross_loss = abs(sum(
                row["avg_return"] for row in [r] if (row["avg_return"] or 0) < 0
            ))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)

            regimes[str(r["regime"])] = {
                "total_trades": total,
                "win_count": int(wins),
                "loss_count": int(losses),
                "win_rate": round(win_rate, 1),
                "net_pnl": round(r["net_pnl"] or 0, 2),
                "avg_confidence": round(r["avg_confidence"] or 0, 1),
                "avg_holding_hours": round((r["avg_holding_minutes"] or 0) / 60, 1),
                "profit_factor": round(profit_factor, 2),
                "max_drawdown": round(r["max_drawdown"] or 0, 2),
            }

        return regimes

    @staticmethod
    def compute_strategy_success_by_regime(db_conn: Any) -> dict[str, dict[str, Any]]:
        """Cross-tab strategy_id x regime."""
        try:
            rows = db_conn.execute("""
                SELECT
                    pj.regime as regime,
                    pj.strategy_id as strategy_id,
                    COUNT(*) as total,
                    SUM(CASE WHEN po.actual_return > 0 THEN 1 ELSE 0 END) as wins
                FROM prediction_journal pj
                LEFT JOIN prediction_outcome po ON po.prediction_id = pj.id
                WHERE pj.regime IS NOT NULL AND pj.regime != ''
                  AND pj.strategy_id IS NOT NULL AND pj.strategy_id != ''
                GROUP BY pj.regime, pj.strategy_id
                ORDER BY pj.regime, total DESC
            """).fetchall()
        except Exception:
            return {}

        result: dict[str, dict[str, Any]] = {}
        for r in rows:
            reg = str(r["regime"])
            sid = str(r["strategy_id"])
            total = r["total"] or 0
            wins = r["wins"] or 0
            if reg not in result:
                result[reg] = {}
            result[reg][sid] = {
                "total_trades": total,
                "win_count": int(wins),
                "win_rate": round((wins / total * 100) if total > 0 else 0, 1),
            }

        return result
