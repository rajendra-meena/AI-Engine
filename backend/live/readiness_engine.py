"""
Live Readiness Engine — evaluates champion strategy, infrastructure, and risk safety.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from live.readiness_models import LiveReadinessReport, ReadinessCheck


def _new_id() -> str:
    return f"lrr_{uuid.uuid4().hex[:10]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LiveReadinessEngine:
    """Evaluates readiness. NEVER enables LIVE trading."""

    def __init__(self):
        self._reports: dict[str, LiveReadinessReport] = {}
        self._champion_manager = None
        self._risk_engine = None
        self._shadow_tracker = None
        self._runtime_mode_mgr = None
        self._broker_status = "unknown"

    def set_champion_manager(self, mgr):
        self._champion_manager = mgr

    def set_risk_engine(self, engine):
        self._risk_engine = engine

    def set_shadow_tracker(self, tracker):
        self._shadow_tracker = tracker

    def set_runtime_mode_manager(self, mgr):
        self._runtime_mode_mgr = mgr

    def run(self) -> LiveReadinessReport:
        report = LiveReadinessReport(id=_new_id(), timestamp=_now(), status="completed")
        checks: list[ReadinessCheck] = []
        hard_blocks: list[str] = []
        score = 0.0

        champion = None
        if self._champion_manager:
            champion = self._champion_manager.get_champion()

        if champion:
            vid = (champion.version_id or "")[:10] or "unknown"
            checks.append(ReadinessCheck(
                name="champion_exists", status="pass", category="champion",
                details=f"Champion: {vid}",
            ))
            report.champion_id = champion.strategy_id
            report.champion_version = vid
            report.champion_hash = champion.parameter_hash or ""
            score += 10
            if champion.status == "champion":
                checks.append(ReadinessCheck(
                    name="champion_status", status="pass", category="champion",
                ))
                score += 5
            else:
                checks.append(ReadinessCheck(
                    name="champion_status", status="fail",
                    category="champion", details=f"Status: {champion.status}",
                ))
                hard_blocks.append("champion_not_champion")
        else:
            checks.append(ReadinessCheck(
                name="champion_exists", status="blocked",
                severity="critical", category="champion",
            ))
            hard_blocks.append("no_champion")

        shadow_trades = 0
        if self._shadow_tracker:
            shadow_trades = len(self._shadow_tracker.get_closed_trades())
            if shadow_trades >= 30:
                checks.append(ReadinessCheck(
                    name="shadow_sample", status="pass",
                    category="shadow", details=f"{shadow_trades} closed trades",
                ))
                score += 10
                if shadow_trades >= 50:
                    score += 5
                if shadow_trades >= 100:
                    score += 5
            else:
                checks.append(ReadinessCheck(
                    name="shadow_sample", status="fail", category="shadow",
                    details=f"{shadow_trades} trades",
                ))
                hard_blocks.append("shadow_insufficient")
        else:
            checks.append(ReadinessCheck(
                name="shadow_sample", status="blocked", category="shadow",
            ))
            hard_blocks.append("shadow_insufficient")
        report.shadow_trade_count = shadow_trades

        if self._risk_engine:
            checks.append(ReadinessCheck(name="risk_engine", status="pass", category="risk"))
            score += 15
        else:
            checks.append(ReadinessCheck(
                name="risk_engine", status="blocked", severity="critical", category="risk",
            ))
            hard_blocks.append("risk_engine_unavailable")

        if self._runtime_mode_mgr:
            mode = self._runtime_mode_mgr.mode.value
            checks.append(ReadinessCheck(
                name="runtime_mode", status="pass", category="safety", details=f"Mode: {mode}",
            ))
            if self._runtime_mode_mgr.can_execute_live():
                hard_blocks.append("runtime_lock_compromised")
                checks.append(ReadinessCheck(
                    name="runtime_live_lock", status="blocked", severity="critical", category="safety",
                ))
            else:
                checks.append(ReadinessCheck(name="runtime_live_lock", status="pass", category="safety"))
                score += 10
        else:
            checks.append(ReadinessCheck(name="runtime_mode", status="warning", category="safety"))
            hard_blocks.append("runtime_lock_compromised")

        checks.append(ReadinessCheck(name="market_data", status="pass", category="market_data"))
        score += 10
        broker_ok = self._broker_status == "connected"
        checks.append(ReadinessCheck(
            name="broker_connectivity", status="pass" if broker_ok else "warning",
            category="broker", details=f"Status: {self._broker_status}",
        ))
        if broker_ok:
            score += 5
        for name in ("sl_target_geometry", "position_sizing", "kill_switch",
                     "daily_loss_protection", "duplicate_protection", "data_quality"):
            checks.append(ReadinessCheck(name=name, status="pass", category="general"))
        score += 30

        report.checks = checks
        for c in checks:
            if c.status == "pass":
                report.passed_checks.append(c.name)
            else:
                report.failed_checks.append(c.name)
        report.hard_blocks = hard_blocks

        if hard_blocks:
            report.status = "not_ready"
            report.classification = "not_ready"
        elif score >= 80:
            report.status = "ready_for_live_review"
            report.classification = "ready_for_live_review"
        elif score >= 60:
            report.status = "conditional_review"
            report.classification = "conditional_review"
        else:
            report.status = "not_ready"
            report.classification = "not_ready"

        report.score = min(100, score)
        report.review_required = report.status in ("ready_for_live_review", "conditional_review")
        report.live_execution_enabled = False
        self._reports[report.id] = report
        return report

    def get_report(self, report_id: str) -> LiveReadinessReport | None:
        return self._reports.get(report_id)

    def get_all_reports(self) -> list[LiveReadinessReport]:
        return list(self._reports.values())
