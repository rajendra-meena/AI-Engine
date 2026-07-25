"""
Shadow Validation Engine — evaluates champion strategy performance on real market data.
Generates validation reports, detects degradation, and assesses live-readiness.
Never executes orders or modifies configuration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from trading.shadow_tracker import ShadowTradeTracker
from trading.shadow_performance import ShadowPerformanceEngine


DECAY_THRESHOLDS = {
    "max_win_rate_drop_pct": 15.0,
    "max_profit_factor_drop_pct": 20.0,
    "max_expectancy_drop_pct": 25.0,
    "max_avg_r_drop_pct": 25.0,
    "max_drawdown_increase_pct": 25.0,
    "min_profit_factor": 1.10,
    "min_expectancy": 0.0,
    "min_closed_trades": 30,
}


def _new_id() -> str:
    return f"svr_{uuid.uuid4().hex[:10]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ShadowValidationReport:
    validation_id: str = ""
    champion_version_id: str = ""
    created_at: str = ""
    period_start: str = ""
    period_end: str = ""
    status: str = "pending"
    classification: str = "insufficient_data"
    overall_score: float = 0.0
    shadow_metrics: dict[str, Any] = field(default_factory=dict)
    baseline_metrics: dict[str, Any] = field(default_factory=dict)
    degradation: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    critical_issues: list[str] = field(default_factory=list)
    sample_level: str = "insufficient"
    ready_for_live_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "champion_version_id": self.champion_version_id,
            "created_at": self.created_at,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "status": self.status,
            "classification": self.classification,
            "overall_score": round(self.overall_score, 1),
            "shadow_metrics": self.shadow_metrics,
            "baseline_metrics": self.baseline_metrics,
            "degradation": self.degradation,
            "warnings": self.warnings,
            "critical_issues": self.critical_issues,
            "sample_level": self.sample_level,
            "ready_for_live_review": self.ready_for_live_review,
        }


class ShadowValidationEngine:
    """
    Validates champion strategy performance on real shadow data.
    Read-only: never modifies runtime mode or configuration.
    """

    def __init__(self, perf_engine: ShadowPerformanceEngine | None = None):
        self._perf_engine = perf_engine or ShadowPerformanceEngine()
        self._reports: dict[str, ShadowValidationReport] = {}
        self._baseline: dict[str, Any] = {}

    def set_baseline(self, metrics: dict[str, Any]):
        self._baseline = metrics

    def validate(
        self,
        tracker: ShadowTradeTracker,
        champion_version_id: str = "",
    ) -> ShadowValidationReport:
        """Run shadow validation and return report."""
        report = ShadowValidationReport(
            validation_id=_new_id(),
            champion_version_id=champion_version_id,
            created_at=_now(),
            status="completed",
        )

        metrics = self._perf_engine.compute_metrics(tracker)
        report.shadow_metrics = metrics.to_dict()
        report.sample_level = metrics.sample_level

        closed = metrics.closed_trades
        if closed < DECAY_THRESHOLDS["min_closed_trades"]:
            report.classification = "insufficient_data"
            report.warnings.append(f"Only {closed} closed trades (need {DECAY_THRESHOLDS['min_closed_trades']})")
            report.ready_for_live_review = False
            return report

        # Compare against baseline if available
        degradation = {}
        if self._baseline:
            for key, label, threshold_key in [
                ("win_rate", "win_rate_drop", "max_win_rate_drop_pct"),
                ("profit_factor", "profit_factor_drop", "max_profit_factor_drop_pct"),
                ("expectancy", "expectancy_drop", "max_expectancy_drop_pct"),
                ("avg_r", "avg_r_drop", "max_avg_r_drop_pct"),
            ]:
                base = self._baseline.get(key, 0) or 0
                current = getattr(metrics, key, 0) or 0
                if base != 0:
                    pct = (current - base) / abs(base) * 100
                    degradation[label] = round(pct, 1)
                    if pct < -DECAY_THRESHOLDS.get(threshold_key, 20):
                        report.warnings.append(f"{key} degraded {pct:.0f}% vs baseline")

            # Drawdown check
            base_dd = self._baseline.get("max_drawdown_pct", 0) or 0
            shadow_dd = metrics.max_drawdown_pct
            if base_dd > 0 and shadow_dd > base_dd * (1 + DECAY_THRESHOLDS["max_drawdown_increase_pct"] / 100):
                report.critical_issues.append(f"Drawdown {shadow_dd:.1f}% exceeds baseline threshold")
        else:
            degradation["baseline_unavailable"] = 1

        report.degradation = degradation

        # Scoring
        score = 50.0
        pf = metrics.profit_factor
        if pf >= DECAY_THRESHOLDS["min_profit_factor"]:
            score += min(pf, 3.0) * 10
        else:
            report.critical_issues.append(f"Profit factor {pf:.2f} below {DECAY_THRESHOLDS['min_profit_factor']}")

        if metrics.expectancy >= DECAY_THRESHOLDS["min_expectancy"]:
            score += min(metrics.expectancy, 5) * 3
        else:
            report.critical_issues.append("Negative expectancy")

        if metrics.max_drawdown_pct <= 15:
            score += 10
        elif metrics.max_drawdown_pct <= 25:
            score += 5
        else:
            report.critical_issues.append(f"High drawdown: {metrics.max_drawdown_pct:.1f}%")

        score += (metrics.win_rate - 50) * 0.2 if metrics.win_rate > 50 else 0
        score += metrics.avg_r * 5 if metrics.avg_r > 0 else 0

        # Sample bonus
        if metrics.sample_level in ("good", "strong"):
            score += 10
        elif metrics.sample_level == "moderate":
            score += 5

        report.overall_score = max(0, min(100, score))

        # Classification
        if report.critical_issues:
            report.classification = "failed"
        elif report.overall_score >= 80:
            report.classification = "excellent"
        elif report.overall_score >= 70:
            report.classification = "strong"
        elif report.overall_score >= 60:
            report.classification = "acceptable"
        elif report.overall_score >= 40:
            report.classification = "weak"
        else:
            report.classification = "failed"

        # Live readiness
        report.ready_for_live_review = (
            report.classification in ("excellent", "strong")
            and not report.critical_issues
            and metrics.sample_level in ("moderate", "good", "strong")
            and metrics.profit_factor >= DECAY_THRESHOLDS["min_profit_factor"]
        )

        self._reports[report.validation_id] = report
        return report

    def get_report(self, report_id: str) -> ShadowValidationReport | None:
        return self._reports.get(report_id)

    def get_all_reports(self) -> list[ShadowValidationReport]:
        return list(self._reports.values())
