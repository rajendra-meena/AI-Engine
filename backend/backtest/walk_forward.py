"""
Walk-Forward Validation Engine — tests strategy robustness across sequential time windows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class WalkForwardWindow:
    window_id: str = ""
    train_start: str = ""
    train_end: str = ""
    val_start: str = ""
    val_end: str = ""
    train_trades: int = 0
    val_trades: int = 0
    train_metrics: dict[str, Any] = field(default_factory=dict)
    val_metrics: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "train_start": self.train_start,
            "train_end": self.train_end,
            "val_start": self.val_start,
            "val_end": self.val_end,
            "train_trades": self.train_trades,
            "val_trades": self.val_trades,
            "train_metrics": self.train_metrics,
            "val_metrics": self.val_metrics,
            "status": self.status,
        }


@dataclass
class WalkForwardResult:
    windows: list[WalkForwardWindow] = field(default_factory=list)
    in_sample: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    generalization: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    total_windows: int = 0
    completed_windows: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "windows": [w.to_dict() for w in self.windows],
            "in_sample": self.in_sample,
            "validation": self.validation,
            "generalization": self.generalization,
            "status": self.status,
            "total_windows": self.total_windows,
            "completed_windows": self.completed_windows,
        }


class WalkForwardEngine:
    """
    Generates sequential walk-forward windows and aggregates results.
    Each window: TRAIN -> VALIDATE -> slide forward -> repeat.
    """

    def __init__(self, min_trades: int = 20):
        self._min_trades = min_trades

    def generate_windows(
        self,
        candles: list[dict],
        train_days: int = 60,
        val_days: int = 20,
        step_days: int = 20,
    ) -> list[WalkForwardWindow]:
        """Generate chronological walk-forward windows from candle timestamps."""
        if len(candles) < 2:
            return []

        timestamps = []
        for c in candles:
            t = c.get("time") or c.get("timestamp") or c.get("Date") or ""
            try:
                timestamps.append(datetime.fromisoformat(t))
            except (ValueError, TypeError):
                continue

        if len(timestamps) < 2:
            return []

        first = timestamps[0]
        last = timestamps[-1]
        total_days = (last - first).days
        if total_days < train_days + val_days:
            return []

        windows: list[WalkForwardWindow] = []
        train_start = first

        while train_start + timedelta(days=train_days + val_days) <= last:
            train_end = train_start + timedelta(days=train_days)
            val_start = train_end
            val_end = val_start + timedelta(days=val_days)

            w_id = f"wf_{len(windows) + 1}"
            windows.append(WalkForwardWindow(
                window_id=w_id,
                train_start=train_start.isoformat(),
                train_end=train_end.isoformat(),
                val_start=val_start.isoformat(),
                val_end=val_end.isoformat(),
                status="pending",
            ))

            train_start += timedelta(days=step_days)

        return windows

    @staticmethod
    def compute_generalization(is_metrics: dict, val_metrics: dict) -> dict[str, Any]:
        """Compute generalization ratios between in-sample and validation."""
        ratios = {}
        for key in ("net_pnl", "win_rate", "profit_factor", "expectancy", "avg_r"):
            is_val = is_metrics.get(key, 0) or 0
            val_val = val_metrics.get(key, 0) or 0
            if is_val != 0:
                ratios[key] = round(val_val / is_val, 3)
            else:
                ratios[key] = None

        # Overall assessment
        score = 0
        for _, v in ratios.items():
            if v is not None and v >= 0.5:
                score += 1
        total = sum(1 for _, v in ratios.items() if v is not None)

        if total == 0:
            gen_class = "insufficient_data"
        elif score / total >= 0.8:
            gen_class = "strong"
        elif score / total >= 0.5:
            gen_class = "acceptable"
        elif score >= 0:
            gen_class = "weak"
        else:
            gen_class = "failed"

        return {
            "ratios": ratios,
            "classification": gen_class,
            "score": round(score / total * 100, 1) if total > 0 else 0,
        }
