"""
Challenger Validation Engine — Champions final OOS verification, governance scoring,
and promotion/rejection decisions. Strict dataset isolation from optimization.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backtest.strategy_version import StrategyVersion


GOVERNANCE_THRESHOLDS = {
    "minimum_oos_trades": 30,
    "max_drawdown_degradation": 10.0,
    "minimum_profit_factor": 1.10,
    "minimum_sharpe": 0.30,
    "maximum_probability_of_ruin": 10.0,
    "minimum_improvement_score": 5.0,
}


class BacktestDataLeakageError(Exception):
    """Raised when FINAL_TEST data is accessed during optimization."""
    pass


@dataclass
class ChallengerValidationReport:
    report_id: str = ""
    champion_version: str = ""
    challenger_version: str = ""
    dataset_id: str = ""
    dataset_start: str = ""
    dataset_end: str = ""
    created_at: str = ""

    champion_metrics: dict[str, Any] = field(default_factory=dict)
    challenger_metrics: dict[str, Any] = field(default_factory=dict)
    differences: dict[str, dict[str, float]] = field(default_factory=dict)
    governance_score: float = 0.0
    decision: str = "insufficient_data"
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failed_gates: list[str] = field(default_factory=list)
    passed_gates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "champion_version": self.champion_version,
            "challenger_version": self.challenger_version,
            "dataset_id": self.dataset_id,
            "dataset_start": self.dataset_start,
            "dataset_end": self.dataset_end,
            "created_at": self.created_at,
            "champion_metrics": self.champion_metrics,
            "challenger_metrics": self.challenger_metrics,
            "differences": self.differences,
            "governance_score": round(self.governance_score, 1),
            "decision": self.decision,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "failed_gates": self.failed_gates,
            "passed_gates": self.passed_gates,
        }


class DatasetTracker:
    """Tracks dataset usage to prevent data leakage."""

    def __init__(self):
        self._datasets: dict[str, dict] = {}

    def register_dataset(self, dataset_id: str, start: str, end: str, role: str) -> dict:
        entry = {
            "dataset_id": dataset_id,
            "start": start,
            "end": end,
            "role": role,
            "status": "untouched",
            "used_by": [],
        }
        self._datasets[dataset_id] = entry
        return entry

    def mark_used(self, dataset_id: str, consumer: str) -> bool:
        entry = self._datasets.get(dataset_id)
        if not entry:
            return False
        entry["status"] = "used"
        if consumer not in entry["used_by"]:
            entry["used_by"].append(consumer)
        return True

    def check_access(self, dataset_id: str, requested_role: str) -> bool:
        entry = self._datasets.get(dataset_id)
        if not entry:
            return False
        if entry["role"] == "final_test" and requested_role != "governance":
            raise BacktestDataLeakageError(
                f"FINAL_TEST dataset {dataset_id} accessed by {requested_role}"
            )
        return True


class ChallengerValidationEngine:
    """
    Compares Champion vs Challenger on untouched Final OOS data.
    Only this engine may access FINAL_TEST data.
    """

    def __init__(self, champion_manager=None):
        self._champion_manager = champion_manager
        self._dataset_tracker = DatasetTracker()
        self._reports: dict[str, ChallengerValidationReport] = {}

    def set_champion_manager(self, mgr):
        self._champion_manager = mgr

    def register_final_test_dataset(self, dataset_id: str, start: str, end: str):
        return self._dataset_tracker.register_dataset(dataset_id, start, end, "final_test")

    def validate(
        self,
        champion: StrategyVersion,
        challenger: StrategyVersion,
        champion_oos_metrics: dict[str, Any],
        challenger_oos_metrics: dict[str, Any],
        dataset_id: str = "",
    ) -> ChallengerValidationReport:
        """Run governance validation — compare champion vs challenger on final OOS data."""
        report = ChallengerValidationReport(
            report_id=f"gov_{uuid.uuid4().hex[:10]}",
            champion_version=champion.version_id,
            challenger_version=challenger.version_id,
            dataset_id=dataset_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            champion_metrics=champion_oos_metrics,
            challenger_metrics=challenger_oos_metrics,
        )

        # Check data leakage
        if dataset_id:
            self._dataset_tracker.check_access(dataset_id, "governance")
            self._dataset_tracker.mark_used(dataset_id, report.report_id)

        # Compute differences
        diff_keys = [
            "net_pnl", "win_rate", "profit_factor", "expectancy",
            "sharpe", "sortino", "max_drawdown_pct",
            "avg_r", "probability_of_ruin",
        ]
        improvements = 0
        total_checked = 0

        for key in diff_keys:
            c_val = champion_oos_metrics.get(key, 0) or 0
            ch_val = challenger_oos_metrics.get(key, 0) or 0
            diff = ch_val - c_val
            pct_diff = (diff / abs(c_val) * 100) if c_val != 0 else 0

            # Determine direction: for most metrics higher is better,
            # for drawdown and ruin lower is better
            higher_is_better = key not in ("max_drawdown_pct", "probability_of_ruin")
            better = (diff > 0 and higher_is_better) or (diff < 0 and not higher_is_better)

            report.differences[key] = {
                "champion": c_val,
                "challenger": ch_val,
                "difference": round(diff, 4),
                "pct_difference": round(pct_diff, 1),
                "better": better,
            }
            if better:
                improvements += 1
            total_checked += 1

        # Governance gates
        ch_metrics = challenger_oos_metrics
        gates = [
            ("sufficient_trades", ch_metrics.get("total_trades", 0) >= GOVERNANCE_THRESHOLDS["minimum_oos_trades"]),
            ("min_profit_factor", (ch_metrics.get("profit_factor", 0) or 0)
             >= GOVERNANCE_THRESHOLDS["minimum_profit_factor"]),
            ("min_sharpe", (ch_metrics.get("sharpe", 0) or 0) >= GOVERNANCE_THRESHOLDS["minimum_sharpe"]),
            ("min_sharpe", (ch_metrics.get("sharpe", 0) or 0)
             >= GOVERNANCE_THRESHOLDS["minimum_sharpe"]),
            ("max_ruin", (ch_metrics.get("probability_of_ruin", 0) or 0)
             <= GOVERNANCE_THRESHOLDS["maximum_probability_of_ruin"]),
            ("drawdown_stable", (ch_metrics.get("max_drawdown_pct", 0) or 0)
                <= (champion_oos_metrics.get("max_drawdown_pct", 0) or 0)
                + GOVERNANCE_THRESHOLDS["max_drawdown_degradation"]),
            ("low_overfit", challenger.overfit_risk not in ("high",)),
        ]

        for gate_name, passed in gates:
            if passed:
                report.passed_gates.append(gate_name)
            else:
                report.failed_gates.append(gate_name)

        # Improvement score
        imp_score = (improvements / max(total_checked, 1)) * 100

        # Governance score
        score = 50.0
        score += min(ch_metrics.get("profit_factor", 0) or 0, 3.0) * 8
        score += min(ch_metrics.get("sharpe", 0) or 0, 2.0) * 10
        dd = ch_metrics.get("max_drawdown_pct", 0) or 0
        score -= max(0, dd - 15) * 0.5
        score += (ch_metrics.get("win_rate", 0) or 0) * 0.1
        score += imp_score * 0.2
        score -= (ch_metrics.get("probability_of_ruin", 0) or 0) * 0.5
        passed = len(report.passed_gates)
        failed = len(report.failed_gates)
        score += (passed / max(passed + failed, 1)) * 15
        score -= failed * 5
        report.governance_score = max(0, min(100, score))

        # Decision logic
        if ch_metrics.get("total_trades", 0) < GOVERNANCE_THRESHOLDS["minimum_oos_trades"]:
            report.decision = "insufficient_data"
            report.reasons.append(f"Only {ch_metrics.get('total_trades', 0)} OOS trades")
        elif report.failed_gates and imp_score < GOVERNANCE_THRESHOLDS["minimum_improvement_score"]:
            report.decision = "reject"
            report.reasons.append(f"Failed {len(report.failed_gates)} governance gates")
        elif imp_score >= GOVERNANCE_THRESHOLDS["minimum_improvement_score"] and report.governance_score >= 60:
            report.decision = "promote"
            msg = f"Gov score {report.governance_score:.0f}"
            msg += " | " + str(improvements) + "/" + str(total_checked) + " improved"
            report.reasons.append(msg)
        elif imp_score >= GOVERNANCE_THRESHOLDS["minimum_improvement_score"]:
            report.decision = "inconclusive"
            report.reasons.append("Improvement detected but governance score insufficient")
        else:
            report.decision = "reject"
            report.reasons.append(f"Insufficient improvement ({improvements}/{total_checked} metrics)")

        # Warnings
        if ch_metrics.get("total_trades", 0) < 50:
            report.warnings.append("Small OOS sample")
        if (ch_metrics.get("max_drawdown_pct", 0) or 0) > 25:
            report.warnings.append("High OOS drawdown")
        if challenger.overfit_risk == "medium":
            report.warnings.append("Medium overfit risk")

        self._reports[report.report_id] = report
        return report

    def get_report(self, report_id: str) -> ChallengerValidationReport | None:
        return self._reports.get(report_id)

    def get_all_reports(self) -> list[ChallengerValidationReport]:
        return list(self._reports.values())
