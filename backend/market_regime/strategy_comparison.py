"""
Strategy Comparison Engine — compares strategies across key metrics.
Reuses backend/performance/advanced_metrics for statistical computations.
"""

from __future__ import annotations

from typing import Any

from performance.advanced_metrics import compute_sharpe, compute_sortino, compute_recovery_factor


SUPPORTED_STRATEGIES = [
    "trend_following", "momentum", "breakout", "scalping",
    "reversal", "pullback", "range", "mean_reversion",
]


class StrategyComparisonEngine:
    """Compares strategy performance across all key metrics."""

    @staticmethod
    def compare_all(
        predictions: list[dict[str, Any]],
        outcomes: dict[str, dict[str, Any]] | None = None,
        feedbacks: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Compute full metrics for each strategy and return ranked list."""
        # Group by strategy_id
        groups: dict[str, list[dict[str, Any]]] = {}
        for p in predictions:
            sid = p.get("strategy_id") or "unknown"
            if sid not in groups:
                groups[sid] = []
            pid = p.get("id") or p.get("prediction_id", "")
            merged = dict(p)
            if outcomes and pid in outcomes:
                merged.update(outcomes[pid])
            groups[sid].append(merged)

        results = []
        for sid, trades in groups.items():
            if not trades:
                continue
            total = len(trades)
            wins = [t for t in trades if (t.get("actual_return") or 0) > 0]
            losses = [t for t in trades if (t.get("actual_return") or 0) <= 0]
            win_count = len(wins)
            loss_count = len(losses)
            win_rate = (win_count / total * 100) if total > 0 else 0.0

            returns = [t.get("actual_return", 0) for t in trades]
            gross_profit = sum(r for r in returns if r > 0)
            gross_loss = abs(sum(r for r in returns if r < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)
            expectancy = sum(returns) / len(returns) if returns else 0

            max_dd = 0
            peak = 0
            for r in returns:
                peak = max(peak, r)
                max_dd = max(max_dd, peak - r)

            sharpe = compute_sharpe(returns)
            sortino = compute_sortino(returns)
            recovery = compute_recovery_factor(sum(returns), max_dd) if max_dd > 0 else None

            # Consistency: % of trades that are within 1 std of mean
            if len(returns) > 1:
                avg_r = sum(returns) / len(returns)
                variance = sum((r - avg_r) ** 2 for r in returns) / len(returns)
                std = variance ** 0.5
                consistent = sum(1 for r in returns if abs(r - avg_r) <= std)
                consistency = (consistent / len(returns)) * 100
            else:
                consistency = 100.0

            name = sid.replace("_", " ").title()

            results.append({
                "strategy_id": sid,
                "strategy_name": name,
                "total_trades": total,
                "win_rate": round(win_rate, 1),
                "profit_factor": round(profit_factor, 2),
                "expectancy": round(expectancy, 2),
                "sharpe_ratio": round(sharpe, 2) if sharpe is not None else None,
                "sortino_ratio": round(sortino, 2) if sortino is not None else None,
                "expected_return": round(expectancy, 2),
                "max_drawdown": round(max_dd, 2),
                "avg_holding_hours": 0,
                "consistency_score": round(consistency, 1),
                "trade_count": total,
            })

        results.sort(key=lambda r: r.get("win_rate", 0), reverse=True)
        return results

    @staticmethod
    def compare_two(
        strategy_a: str, strategy_b: str,
        predictions: list[dict[str, Any]],
        outcomes: dict[str, dict[str, Any]] | None = None,
        feedbacks: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Head-to-head comparison of two strategies."""
        all_results = StrategyComparisonEngine.compare_all(predictions, outcomes, feedbacks)
        a_result = next((r for r in all_results if r["strategy_id"] == strategy_a), None)
        b_result = next((r for r in all_results if r["strategy_id"] == strategy_b), None)

        return {
            "strategy_a": a_result,
            "strategy_b": b_result,
            "comparison": {
                "a_wins": a_result and b_result and a_result["win_rate"] > b_result["win_rate"],
                "b_wins": a_result and b_result and b_result["win_rate"] > a_result["win_rate"],
                "difference": round(a_result["win_rate"] - b_result["win_rate"], 1) if a_result and b_result else 0,
            },
        }
