"""
Walk-Forward Validation Engine — rolling and expanding window out-of-sample testing.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from performance.advanced_metrics import compute_sharpe, compute_sortino


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"wf_{uuid.uuid4().hex[:12]}"


class WalkForwardEngine:
    """Generates walk-forward windows and computes generalization scores."""

    @staticmethod
    def generate_windows(
        total_candles: int,
        train_size: int = 60,
        val_size: int = 20,
        step_size: int = 20,
        window_type: str = "rolling",
    ) -> list[dict[str, Any]]:
        """Generate chronological walk-forward windows."""
        windows = []
        idx = 0
        wf_id = _new_id()

        while idx + train_size + val_size <= total_candles:
            windows.append({
                "window_id": f"{wf_id}_w{len(windows)}",
                "window_index": len(windows),
                "train_start": idx,
                "train_end": idx + train_size,
                "val_start": idx + train_size,
                "val_end": idx + train_size + val_size,
                "train_size": train_size,
                "val_size": val_size,
            })

            if window_type == "rolling":
                idx += step_size
            elif window_type == "expanding":
                idx += step_size
                train_size = idx + train_size  # expanding window grows

        return windows

    @staticmethod
    def compute_window_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute standard metrics for a set of trades."""
        if not trades:
            return {"total_trades": 0, "win_rate": 0, "profit_factor": 0, "sharpe_ratio": None,
                    "sortino_ratio": None, "max_drawdown": 0, "expectancy": 0}

        total = len(trades)
        wins = [t for t in trades if (t.get("actual_return") or t.get("pnl", 0)) > 0]
        losses = [t for t in trades if (t.get("actual_return") or t.get("pnl", 0)) <= 0]
        win_count = len(wins)
        win_rate = (win_count / total * 100) if total > 0 else 0

        returns = [t.get("actual_return") or t.get("pnl", 0) for t in trades]
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

        return {
            "total_trades": total,
            "win_rate": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "expectancy": round(expectancy, 2),
            "sharpe_ratio": round(sharpe, 2) if sharpe is not None else None,
            "sortino_ratio": round(sortino, 2) if sortino is not None else None,
            "max_drawdown": round(max_dd, 2),
        }

    @staticmethod
    def compute_generalization(
        in_sample_metrics: dict[str, Any],
        val_metrics: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare validation vs in-sample metrics to compute generalization score."""
        comparisons = {}
        metrics_list = ["win_rate", "profit_factor", "expectancy", "sharpe_ratio", "max_drawdown"]

        for metric in metrics_list:
            is_val = in_sample_metrics.get(metric, 0) or 0
            val_val = val_metrics.get(metric, 0) or 0

            if is_val != 0:
                if metric == "max_drawdown":
                    # Higher drawdown is worse — invert ratio
                    ratio = val_val / is_val if is_val > 0 else 1.0
                else:
                    ratio = val_val / abs(is_val)
            else:
                ratio = 1.0 if val_val == 0 else 0.0

            comparisons[metric] = {
                "in_sample": is_val,
                "validation": val_val,
                "ratio": round(ratio, 3),
            }

        # Generalization score: average of metric ratios (capped)
        ratios = [abs(c["ratio"]) for c in comparisons.values()]
        avg_ratio = sum(ratios) / len(ratios) if ratios else 0
        score = round(min(100, avg_ratio * 100), 1)

        if score >= 80:
            classification = "strong"
        elif score >= 60:
            classification = "acceptable"
        elif score >= 40:
            classification = "weak"
        else:
            classification = "failed"

        return {
            "generalization_score": score,
            "classification": classification,
            "comparisons": comparisons,
        }
