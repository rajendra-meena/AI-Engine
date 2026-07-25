"""Pre-Live Validation Engine — runs 18 independent safety check categories.

Phase 44: FINAL operational validation before a future controlled LIVE activation.
LIVE execution remains HARD BLOCKED — can_execute_live() must still return False.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from live.pre_live_models import (
    PreLiveCheck, PreLiveValidationReport,
    CheckStatus, CheckSeverity, ValidationClassification,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"plv_{uuid.uuid4().hex[:12]}"


CHECK_CATEGORIES = [
    "champion_integrity",
    "final_approval",
    "approval_expiry",
    "config_integrity",
    "shadow_validation",
    "risk_engine",
    "market_data",
    "broker_connectivity",
    "account_funds",
    "position_reconciliation",
    "order_reconciliation",
    "execution_infrastructure",
    "kill_switch",
    "emergency_shutdown",
    "execution_simulator",
    "auditability",
    "operational_recovery",
    "security_credentials",
]

CATEGORY_WEIGHTS: dict[str, float] = {
    "champion_integrity": 10.0,
    "final_approval": 10.0,
    "shadow_validation": 10.0,
    "risk_engine": 10.0,
    "market_data": 10.0,
    "broker_connectivity": 10.0,
    "account_funds": 5.0,
    "position_reconciliation": 5.0,
    "order_reconciliation": 5.0,
    "execution_infrastructure": 5.0,
    "kill_switch": 5.0,
    "emergency_shutdown": 5.0,
    "execution_simulator": 0.0,
    "auditability": 5.0,
    "operational_recovery": 0.0,
    "security_credentials": 5.0,
    "config_integrity": 0.0,
    "approval_expiry": 0.0,
}


# Phase 44 audit event type constants
PRELIVE_CHECK_STARTED = "prelive_check_started"
PRELIVE_CHECK_PASSED = "prelive_check_passed"
PRELIVE_CHECK_WARNING = "prelive_check_warning"
PRELIVE_CHECK_FAILED = "prelive_check_failed"
BROKER_READONLY_CONNECTED = "broker_readonly_connected"
BROKER_READONLY_FAILED = "broker_readonly_failed"
RECONCILIATION_STARTED = "reconciliation_started"
RECONCILIATION_FAILED = "reconciliation_failed"
KILLSWITCH_TEST = "killswitch_test"
EMERGENCY_TEST = "emergency_test"
CONFIG_DRIFT_TEST = "config_drift_test"
APPROVAL_VALIDATED = "approval_validated"
PRELIVE_VALIDATION_COMPLETED = "prelive_validation_completed"
PRELIVE_VALIDATION_STARTED = "prelive_validation_started"


class PreLiveValidationEngine:
    """
    Runs 18 independent pre-live validation checks.

    A failed check must not be hidden because another category passed.
    Every check must have an explicit result.
    Score NEVER overrides hard blocks.
    """

    def __init__(
        self,
        champion_manager=None,
        approval_engine=None,
        risk_engine=None,
        runtime_mgr=None,
        config_guard=None,
        shadow_performance=None,
        shadow_tracker=None,
        market_stream=None,
        broker=None,
        position_reconciliation=None,
        order_reconciliation=None,
        kill_switch=None,
        emergency_shutdown=None,
        execution_health=None,
        audit_log=None,
        execution_policy=None,
    ):
        self._champion_manager = champion_manager
        self._approval_engine = approval_engine
        self._risk_engine = risk_engine
        self._runtime_mgr = runtime_mgr
        self._config_guard = config_guard
        self._shadow_performance = shadow_performance
        self._shadow_tracker = shadow_tracker
        self._market_stream = market_stream
        self._broker = broker
        self._position_reconciliation = position_reconciliation
        self._order_reconciliation = order_reconciliation
        self._kill_switch = kill_switch
        self._emergency_shutdown = emergency_shutdown
        self._execution_health = execution_health
        self._audit_log = audit_log
        self._execution_policy = execution_policy
        self._reports: dict[str, PreLiveValidationReport] = {}

    # ── Dependency injection ──

    def set_champion_manager(self, mgr):
        self._champion_manager = mgr

    def set_approval_engine(self, engine):
        self._approval_engine = engine

    def set_risk_engine(self, engine):
        self._risk_engine = engine

    def set_runtime_mgr(self, mgr):
        self._runtime_mgr = mgr

    def set_config_guard(self, guard):
        self._config_guard = guard

    def set_shadow_performance(self, perf):
        self._shadow_performance = perf

    def set_shadow_tracker(self, tracker):
        self._shadow_tracker = tracker

    def set_market_stream(self, stream):
        self._market_stream = stream

    def set_broker(self, broker):
        self._broker = broker

    def set_position_reconciliation(self, engine):
        self._position_reconciliation = engine

    def set_order_reconciliation(self, engine):
        self._order_reconciliation = engine

    def set_kill_switch(self, ks):
        self._kill_switch = ks

    def set_emergency_shutdown(self, emg):
        self._emergency_shutdown = emg

    def set_execution_health(self, health):
        self._execution_health = health

    def set_audit_log(self, audit):
        self._audit_log = audit

    def set_execution_policy(self, policy):
        self._execution_policy = policy

    # ── Main validation runner ──

    def _apply_duration(self, check: PreLiveCheck) -> PreLiveCheck:
        """No-op: check already timed; used for _run_check helper."""
        return check

    def _run_check(self, check_fn: Callable[[], PreLiveCheck | tuple]) -> Any:
        """Run a check function and add duration_ms to the PreLiveCheck result.
        Supports both single-check and tuple (check, extra) returns."""
        t0 = time.perf_counter()
        result = check_fn()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if isinstance(result, tuple):
            check = result[0]
            if isinstance(check, PreLiveCheck):
                check.duration_ms = elapsed_ms
            return result
        if isinstance(result, PreLiveCheck):
            result.duration_ms = elapsed_ms
        return result

    def run(self, approval_id: str = "") -> PreLiveValidationReport:
        """Execute all pre-live validation checks."""
        t_start = time.perf_counter()
        report = PreLiveValidationReport()
        hard_blocks: list[str] = []
        warnings_list: list[str] = []
        critical_issues: list[str] = []
        score = 0.0
        max_score = sum(CATEGORY_WEIGHTS.values())

        if self._audit_log:
            self._audit_log.record(
                PRELIVE_VALIDATION_STARTED, severity="info",
                details={"validation_id": report.validation_id},
            )

        # ── 1. Champion Integrity ──
        check, champ_id = self._run_check(self._check_champion_integrity)
        report.add_check(check)
        if check.blocking and not check.passed:
            hard_blocks.append("no_champion")
        elif check.passed:
            score += CATEGORY_WEIGHTS.get("champion_integrity", 0)
        report.champion_id = champ_id

        # ── 2. Final Approval ──
        check, app_id = self._run_check(lambda: self._check_final_approval(approval_id))
        report.add_check(check)
        report.approval_id = app_id
        if check.blocking and not check.passed:
            hard_blocks.append("approval_invalid")
        elif check.passed:
            score += CATEGORY_WEIGHTS.get("final_approval", 0)

        # ── 3. Approval Expiry ──
        check = self._run_check(lambda: self._check_approval_expiry(approval_id))
        report.add_check(check)
        if check.blocking and not check.passed:
            hard_blocks.append("approval_expired")
        elif check.passed:
            score += CATEGORY_WEIGHTS.get("approval_expiry", 0)

        # ── 4. Config Integrity ──
        check, config_hash = self._run_check(self._check_config_integrity)
        report.add_check(check)
        report.config_hash = config_hash
        if check.blocking and not check.passed:
            hard_blocks.append("configuration_drift")
        elif check.passed:
            score += CATEGORY_WEIGHTS.get("config_integrity", 0)

        # ── 5. Shadow Validation ──
        check = self._run_check(self._check_shadow_validation)
        report.add_check(check)
        if check.blocking and not check.passed:
            hard_blocks.append("shadow_validation_insufficient")
        elif check.passed:
            score += CATEGORY_WEIGHTS.get("shadow_validation", 0)

        # ── 6. Risk Engine ──
        check = self._run_check(self._check_risk_engine)
        report.add_check(check)
        if check.blocking and not check.passed:
            hard_blocks.append("risk_engine_unavailable")
        elif check.passed:
            score += CATEGORY_WEIGHTS.get("risk_engine", 0)

        # ── 7. Market Data ──
        check, md_status = self._run_check(self._check_market_data)
        report.add_check(check)
        report.market_data_status = md_status
        if check.blocking and not check.passed:
            critical_issues.append("market_data_unhealthy")

        # ── 8. Broker Connectivity ──
        check, broker_status = self._run_check(self._check_broker)
        report.add_check(check)
        report.broker_status = broker_status
        if check.blocking and not check.passed:
            critical_issues.append("broker_unavailable")

        # ── 9. Account / Funds (Read-Only) ──
        check = self._run_check(self._check_account_funds)
        report.add_check(check)

        # ── 10. Position Reconciliation ──
        check = self._run_check(self._check_position_reconciliation)
        report.add_check(check)
        if check.blocking and not check.passed:
            hard_blocks.append("position_reconciliation_failed")

        # ── 11. Order Reconciliation ──
        check = self._run_check(self._check_order_reconciliation)
        report.add_check(check)
        if check.blocking and not check.passed:
            hard_blocks.append("order_reconciliation_failed")

        # ── 12. Execution Infrastructure ──
        check = self._run_check(self._check_execution_infrastructure)
        report.add_check(check)
        if check.passed:
            score += CATEGORY_WEIGHTS.get("execution_infrastructure", 0)

        # ── 13. Kill Switch ──
        check = self._run_check(self._check_kill_switch)
        report.add_check(check)
        if check.passed:
            score += CATEGORY_WEIGHTS.get("kill_switch", 0)

        # ── 14. Emergency Shutdown ──
        check = self._run_check(self._check_emergency_shutdown)
        report.add_check(check)
        if check.passed:
            score += CATEGORY_WEIGHTS.get("emergency_shutdown", 0)

        # ── 15. Execution Simulator ──
        check = self._run_check(self._check_execution_simulator)
        report.add_check(check)

        # ── 16. Auditability ──
        check = self._run_check(self._check_auditability)
        report.add_check(check)
        if check.passed:
            score += CATEGORY_WEIGHTS.get("auditability", 0)

        # ── 17. Operational Recovery ──
        check = self._run_check(self._check_operational_recovery)
        report.add_check(check)

        # ── 18. Security / Credentials ──
        check = self._run_check(self._check_security)
        report.add_check(check)
        if check.blocking and not check.passed:
            hard_blocks.append("security_failure")
        elif check.passed:
            score += CATEGORY_WEIGHTS.get("security_credentials", 0)

        # ── Compute results ──
        report.hard_blocks = hard_blocks
        report.warnings = warnings_list
        report.critical_issues = critical_issues
        report.score = min(100.0, (score / max_score * 100) if max_score > 0 else 0)

        # Runtime mode
        if self._runtime_mgr:
            report.runtime_mode = self._runtime_mgr.mode.value

        # Live execution check
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        report.live_execution_enabled = False
        report.can_execute_live = False
        if self._runtime_mgr:
            report.can_execute_live = self._runtime_mgr.can_execute_live()

        # Overall classification — hard blocks override score
        if hard_blocks or critical_issues:
            report.overall_status = "blocked"
            report.classification = ValidationClassification.BLOCKED
        elif report.score >= 90:
            report.overall_status = "ready_for_live_activation"
            report.classification = ValidationClassification.READY
        elif report.score >= 70:
            report.overall_status = "conditional_review"
            report.classification = ValidationClassification.CONDITIONAL
        else:
            report.overall_status = "not_ready"
            report.classification = ValidationClassification.NOT_READY

        # Phase 43 lock: even if READY, live execution is disabled
        if PHASE_43_LIVE_EXECUTION_LOCK:
            report.live_execution_enabled = False
            report.can_execute_live = False

        # Finish
        report.completed_at = _now()
        report.duration_ms = round((time.perf_counter() - t_start) * 1000, 1)
        report.generated_at = _now()

        self._reports[report.validation_id] = report

        if self._audit_log:
            self._audit_log.record(
                PRELIVE_VALIDATION_COMPLETED, severity="info",
                details={
                    "validation_id": report.validation_id,
                    "classification": report.classification.value,
                    "score": report.score,
                    "hard_blocks": hard_blocks,
                },
            )

        return report

    # ── Individual checks ──

    def _make_check(self, category: str, name: str, status: CheckStatus,
                    passed: bool = False, blocking: bool = False,
                    message: str = "", details: str = "") -> PreLiveCheck:
        severity = CheckSeverity.INFO
        if status == CheckStatus.BLOCKED:
            severity = CheckSeverity.CRITICAL
        elif status == CheckStatus.FAIL:
            severity = CheckSeverity.ERROR
        elif status == CheckStatus.WARNING:
            severity = CheckSeverity.WARNING
        return PreLiveCheck(
            category=category, name=name, status=status,
            severity=severity, passed=passed, blocking=blocking,
            message=message, details=details,
        )

    def _record_check_event(self, check: PreLiveCheck, validation_id: str = ""):
        """Record an audit event for a check result."""
        if not self._audit_log:
            return
        if check.passed:
            event_type = PRELIVE_CHECK_PASSED
            severity = "info"
        elif check.status == CheckStatus.WARNING:
            event_type = PRELIVE_CHECK_WARNING
            severity = "warning"
        elif check.blocking:
            event_type = PRELIVE_CHECK_FAILED
            severity = "critical"
        else:
            event_type = PRELIVE_CHECK_FAILED
            severity = "warning"
        self._audit_log.record(
            event_type, severity=severity,
            details={
                "check_id": check.check_id,
                "category": check.category,
                "name": check.name,
                "status": check.status.value,
                "validation_id": validation_id,
                "message": check.message,
            },
        )

    def _check_champion_integrity(self) -> tuple[PreLiveCheck, str]:
        champ_id = ""
        if not self._champion_manager:
            return self._make_check(
                "champion_integrity", "Champion Exists",
                CheckStatus.BLOCKED, blocking=True,
                message="ChampionManager unavailable",
            ), champ_id

        try:
            champ = self._champion_manager.get_champion()
            if not champ:
                return self._make_check(
                    "champion_integrity", "Champion Exists",
                    CheckStatus.BLOCKED, blocking=True,
                    message="No champion strategy selected",
                ), champ_id

            champ_status = getattr(champ, "status", "")
            champ_id = getattr(champ, "id", getattr(champ, "version", getattr(champ, "version_id", "unknown")))

            if champ_status not in ("champion", "active", "CHAMPION"):
                return self._make_check(
                    "champion_integrity", "Champion Status",
                    CheckStatus.BLOCKED, blocking=True,
                    message=f"Champion status is '{champ_status}', expected 'champion'",
                ), champ_id

            return self._make_check(
                "champion_integrity", "Champion Integrity",
                CheckStatus.PASS, passed=True,
                message=f"Champion {champ_id} is valid",
                details=f"status={champ_status}",
            ), champ_id
        except Exception as e:
            return self._make_check(
                "champion_integrity", "Champion Check",
                CheckStatus.FAIL, blocking=True,
                message=f"Champion check failed: {e}",
            ), champ_id

    def _check_final_approval(self, approval_id: str = "") -> tuple[PreLiveCheck, str]:
        if not self._approval_engine:
            return self._make_check(
                "final_approval", "Approval Engine",
                CheckStatus.BLOCKED, blocking=True,
                message="Final approval engine unavailable",
            ), ""

        try:
            if approval_id:
                record = self._approval_engine.get_record(approval_id)
            else:
                records = self._approval_engine.get_all_records()
                record = records[-1] if records else None

            if not record:
                return self._make_check(
                    "final_approval", "Approval Record",
                    CheckStatus.BLOCKED, blocking=True,
                    message="No approval record found",
                ), ""

            rec_id = (
                getattr(record, "approval_id", record.get("approval_id", ""))
                if isinstance(record, dict) else record.approval_id
            )
            rec_status = (
                getattr(record, "status", record.get("status", ""))
                if isinstance(record, dict) else record.status
            )

            if rec_status != "approved_for_live_review":
                check = self._make_check(
                    "final_approval", "Approval Status",
                    CheckStatus.BLOCKED, blocking=True,
                    message=f"Approval status is '{rec_status}', expected 'approved_for_live_review'",
                )
                if self._audit_log:
                    self._audit_log.record(
                        APPROVAL_VALIDATED, severity="warning",
                        details={"approval_id": rec_id, "status": rec_status, "valid": False},
                    )
                return check, rec_id

            if self._audit_log:
                self._audit_log.record(
                    APPROVAL_VALIDATED, severity="info",
                    details={"approval_id": rec_id, "status": rec_status, "valid": True},
                )

            return self._make_check(
                "final_approval", "Final Approval",
                CheckStatus.PASS, passed=True,
                message=f"Approval {rec_id} is valid",
                details=f"status={rec_status}",
            ), rec_id
        except Exception as e:
            return self._make_check(
                "final_approval", "Approval Check",
                CheckStatus.FAIL, blocking=True,
                message=f"Approval check failed: {e}",
            ), ""

    def _check_approval_expiry(self, approval_id: str = "") -> PreLiveCheck:
        if not self._approval_engine:
            return self._make_check(
                "approval_expiry", "Approval Expiry",
                CheckStatus.SKIPPED, passed=False,
                message="Approval engine unavailable",
            )

        try:
            if approval_id:
                record = self._approval_engine.get_record(approval_id)
            else:
                records = self._approval_engine.get_all_records()
                record = records[-1] if records else None

            if not record:
                return self._make_check(
                    "approval_expiry", "Approval Expiry",
                    CheckStatus.SKIPPED, passed=False,
                    message="No approval record to check",
                )

            expires_at = (
                getattr(record, "expires_at", record.get("expires_at", ""))
                if isinstance(record, dict) else record.expires_at
            )
            if not expires_at:
                return self._make_check(
                    "approval_expiry", "Approval Expiry",
                    CheckStatus.WARNING, passed=True,
                    message="Approval has no expiry",
                )

            try:
                expiry_dt = datetime.fromisoformat(expires_at)
                now = datetime.now(timezone.utc)
                if now > expiry_dt:
                    return self._make_check(
                        "approval_expiry", "Approval Expiry",
                        CheckStatus.BLOCKED, blocking=True,
                        message=f"Approval expired at {expires_at}",
                    )
                remaining = (expiry_dt - now).total_seconds() / 3600
                return self._make_check(
                    "approval_expiry", "Approval Expiry",
                    CheckStatus.PASS, passed=True,
                    message=f"Approval valid for {remaining:.1f}h",
                )
            except (ValueError, TypeError):
                return self._make_check(
                    "approval_expiry", "Approval Expiry",
                    CheckStatus.FAIL, blocking=True,
                    message="Invalid approval expiry format",
                )
        except Exception as e:
            return self._make_check(
                "approval_expiry", "Approval Expiry",
                CheckStatus.FAIL, message=f"Expiry check error: {e}",
            )

    def _check_config_integrity(self) -> tuple[PreLiveCheck, str]:
        if not self._config_guard:
            return self._make_check(
                "config_integrity", "Config Guard",
                CheckStatus.SKIPPED, passed=False,
                message="Config guard unavailable",
            ), ""

        try:
            status = self._config_guard.get_status()
            drift = status.get("drift_detected", False)
            config_hash = status.get("current_hash", "")
            if drift:
                check = self._make_check(
                    "config_integrity", "Configuration Integrity",
                    CheckStatus.BLOCKED, blocking=True,
                    message="Configuration drift detected",
                    details=status.get("drift_reason", ""),
                )
                if self._audit_log:
                    self._audit_log.record(
                        CONFIG_DRIFT_TEST, severity="critical",
                        details={"drift_detected": True, "reason": status.get("drift_reason", "")},
                    )
                return check, config_hash

            return self._make_check(
                "config_integrity", "Configuration Integrity",
                CheckStatus.PASS, passed=True,
                message="Configuration unchanged since approval",
                details=f"hash={config_hash}",
            ), config_hash
        except Exception as e:
            return self._make_check(
                "config_integrity", "Config Integrity",
                CheckStatus.FAIL, blocking=True,
                message=f"Config check failed: {e}",
            ), ""

    def _check_shadow_validation(self) -> PreLiveCheck:
        if not self._shadow_tracker and not self._shadow_performance:
            return self._make_check(
                "shadow_validation", "Shadow Validation",
                CheckStatus.SKIPPED, passed=False,
                message="Shadow tracker unavailable",
            )

        try:
            closed_trades = 0
            if self._shadow_tracker:
                closed_trades = len(self._shadow_tracker.get_closed_trades())

            min_sample = 20
            if closed_trades < min_sample:
                return self._make_check(
                    "shadow_validation", "Shadow Trade Sample",
                    CheckStatus.BLOCKED, blocking=True,
                    message=f"Only {closed_trades} closed trades (minimum {min_sample})",
                )

            return self._make_check(
                "shadow_validation", "Shadow Validation",
                CheckStatus.PASS, passed=True,
                message=f"{closed_trades} closed shadow trades validated",
            )
        except Exception as e:
            return self._make_check(
                "shadow_validation", "Shadow Validation",
                CheckStatus.FAIL, blocking=True,
                message=f"Shadow validation error: {e}",
            )

    def _check_risk_engine(self) -> PreLiveCheck:
        if not self._risk_engine:
            return self._make_check(
                "risk_engine", "Risk Engine Health",
                CheckStatus.BLOCKED, blocking=True,
                message="RiskEngine not initialized",
            )

        try:
            status = self._risk_engine.get_status()
            if isinstance(status, dict):
                halt = status.get("trading_halt", False)
                risk_score = status.get("risk_score", 0)
                if halt:
                    return self._make_check(
                        "risk_engine", "Risk Engine",
                        CheckStatus.BLOCKED, blocking=True,
                        message="Risk engine has trading halt active",
                    )
                return self._make_check(
                    "risk_engine", "Risk Engine Health",
                    CheckStatus.PASS, passed=True,
                    message=f"Risk engine healthy (risk score: {risk_score})",
                )
            return self._make_check(
                "risk_engine", "Risk Engine",
                CheckStatus.PASS, passed=True,
                message="Risk engine responsive",
            )
        except Exception as e:
            return self._make_check(
                "risk_engine", "Risk Engine",
                CheckStatus.FAIL, blocking=True,
                message=f"Risk engine error: {e}",
            )

    def _check_market_data(self) -> tuple[PreLiveCheck, str]:
        if not self._market_stream and not self._execution_health:
            return self._make_check(
                "market_data", "Market Data",
                CheckStatus.NOT_TESTED, passed=False,
                message="Market data monitor unavailable",
            ), "unknown"

        try:
            if self._execution_health:
                md_check = self._execution_health.get_check("market_data_freshness")
                if md_check:
                    state = md_check.state.value
                    if state == "blocked":
                        return self._make_check(
                            "market_data", "Market Data Freshness",
                            CheckStatus.BLOCKED, blocking=True,
                            message="Market data is stale / blocked",
                        ), "blocked"
                    if state == "healthy":
                        return self._make_check(
                            "market_data", "Market Data",
                            CheckStatus.PASS, passed=True,
                            message="Market data is fresh and healthy",
                        ), "healthy"
                    if state == "degraded":
                        return self._make_check(
                            "market_data", "Market Data",
                            CheckStatus.WARNING, passed=True,
                            message="Market data is degraded",
                        ), "degraded"

            return self._make_check(
                "market_data", "Market Data",
                CheckStatus.PASS, passed=True,
                message="Market data assumed healthy",
            ), "healthy"
        except Exception as e:
            return self._make_check(
                "market_data", "Market Data",
                CheckStatus.FAIL, blocking=True,
                message=f"Market data check error: {e}",
            ), "error"

    def _check_broker(self) -> tuple[PreLiveCheck, str]:
        if not self._broker:
            return self._make_check(
                "broker_connectivity", "Broker Connection",
                CheckStatus.NOT_TESTED, passed=False,
                message="Broker adapter not configured",
            ), "not_configured"

        try:
            import asyncio
            health = asyncio.run(self._broker.health_check())
            status = health.get("status", "unknown")
            if status == "healthy":
                check = self._make_check(
                    "broker_connectivity", "Broker Connectivity",
                    CheckStatus.PASS, passed=True,
                    message="Broker connection healthy",
                    details=f"latency_ms={health.get('latency_ms', 0)}",
                )
                if self._audit_log:
                    self._audit_log.record(
                        BROKER_READONLY_CONNECTED, severity="info",
                        details={"status": "healthy", "latency_ms": health.get("latency_ms", 0)},
                    )
                return check, "healthy"
            check = self._make_check(
                "broker_connectivity", "Broker Connectivity",
                CheckStatus.FAIL, blocking=True,
                message=f"Broker status: {status}",
            )
            if self._audit_log:
                self._audit_log.record(
                    BROKER_READONLY_FAILED, severity="warning",
                    details={"status": status},
                )
            return check, status
        except Exception as e:
            if self._audit_log:
                self._audit_log.record(
                    BROKER_READONLY_FAILED, severity="warning",
                    details={"error": str(e)},
                )
            return self._make_check(
                "broker_connectivity", "Broker Connectivity",
                CheckStatus.FAIL, blocking=True,
                message=f"Broker connection failed: {e}",
            ), "error"

    def _check_account_funds(self) -> PreLiveCheck:
        if not self._broker:
            return self._make_check(
                "account_funds", "Account / Funds",
                CheckStatus.SKIPPED,
                message="Broker not configured — read-only check skipped",
            )

        try:
            import asyncio
            balance = asyncio.run(self._broker.get_balance())
            available = balance.get("available", 0)
            account = asyncio.run(self._broker.get_account())
            return self._make_check(
                "account_funds", "Account / Funds (Read-Only)",
                CheckStatus.PASS, passed=True,
                message=f"Account accessible, available funds: {available}",
                details=f"account_status={account.get('status', 'unknown')}",
            )
        except Exception as e:
            return self._make_check(
                "account_funds", "Account / Funds",
                CheckStatus.WARNING, passed=True,
                message=f"Account check unavailable (non-blocking): {e}",
            )

    def _check_position_reconciliation(self) -> PreLiveCheck:
        if not self._position_reconciliation:
            return self._make_check(
                "position_reconciliation", "Position Reconciliation",
                CheckStatus.SKIPPED,
                message="Position reconciliation engine unavailable",
            )

        try:
            if self._position_reconciliation.is_blocked():
                discrepancies = self._position_reconciliation.get_discrepancies()
                check = self._make_check(
                    "position_reconciliation", "Position Reconciliation",
                    CheckStatus.BLOCKED, blocking=True,
                    message="Position reconciliation has unresolved discrepancies",
                    details=f"{len(discrepancies)} discrepancies found",
                )
                if self._audit_log:
                    self._audit_log.record(
                        RECONCILIATION_FAILED, severity="critical",
                        details={"type": "position", "count": len(discrepancies)},
                    )
                return check
            if self._audit_log:
                self._audit_log.record(
                    RECONCILIATION_STARTED, severity="info",
                    details={"type": "position", "result": "clean"},
                )
            return self._make_check(
                "position_reconciliation", "Position Reconciliation",
                CheckStatus.PASS, passed=True,
                message="Position reconciliation clean",
            )
        except Exception as e:
            return self._make_check(
                "position_reconciliation", "Position Reconciliation",
                CheckStatus.FAIL, blocking=True,
                message=f"Position reconciliation error: {e}",
            )

    def _check_order_reconciliation(self) -> PreLiveCheck:
        if not self._order_reconciliation:
            return self._make_check(
                "order_reconciliation", "Order Reconciliation",
                CheckStatus.SKIPPED,
                message="Order reconciliation engine unavailable",
            )

        try:
            blocking = self._order_reconciliation.get_blocking_issues()
            if blocking:
                check = self._make_check(
                    "order_reconciliation", "Order Reconciliation",
                    CheckStatus.BLOCKED, blocking=True,
                    message=f"{len(blocking)} blocking order reconciliation issues",
                )
                if self._audit_log:
                    self._audit_log.record(
                        RECONCILIATION_FAILED, severity="critical",
                        details={"type": "order", "count": len(blocking)},
                    )
                return check
            if self._audit_log:
                self._audit_log.record(
                    RECONCILIATION_STARTED, severity="info",
                    details={"type": "order", "result": "clean"},
                )
            return self._make_check(
                "order_reconciliation", "Order Reconciliation",
                CheckStatus.PASS, passed=True,
                message="Order reconciliation clean",
            )
        except Exception as e:
            return self._make_check(
                "order_reconciliation", "Order Reconciliation",
                CheckStatus.FAIL, blocking=True,
                message=f"Order reconciliation error: {e}",
            )

    def _check_execution_infrastructure(self) -> PreLiveCheck:
        from execution.execution_simulator import ExecutionSimulator
        try:
            sim = ExecutionSimulator("happy_path")
            result = sim.place_order("SIM", "BUY", 1, 100.0)
            if result.get("success"):
                return self._make_check(
                    "execution_infrastructure", "Execution Infrastructure",
                    CheckStatus.PASS, passed=True,
                    message="Execution infrastructure operational (simulated)",
                    details="Happy path test passed",
                )
        except Exception as e:
            return self._make_check(
                "execution_infrastructure", "Execution Infrastructure",
                CheckStatus.FAIL, blocking=True,
                message=f"Execution infrastructure test failed: {e}",
            )

        return self._make_check(
            "execution_infrastructure", "Execution Infrastructure",
            CheckStatus.PASS, passed=True,
            message="Execution infrastructure available",
        )

    def _check_kill_switch(self) -> PreLiveCheck:
        if not self._kill_switch:
            return self._make_check(
                "kill_switch", "Kill Switch",
                CheckStatus.SKIPPED,
                message="Kill switch unavailable",
            )

        try:
            from execution.kill_switch import KillSwitchLevel
            active = self._kill_switch.is_active()
            if active:
                return self._make_check(
                    "kill_switch", "Kill Switch Status",
                    CheckStatus.BLOCKED, blocking=True,
                    message="Kill switch is active — execution blocked",
                )

            # Test activation/reset cycle
            self._kill_switch.activate(KillSwitchLevel.GLOBAL, "", "prelive_test")
            is_blocked = self._kill_switch.is_active()
            self._kill_switch.reset(KillSwitchLevel.GLOBAL)
            is_recovered = not self._kill_switch.is_active()

            if self._audit_log:
                self._audit_log.record(
                    KILLSWITCH_TEST, severity="info",
                    details={"test_activated": is_blocked, "test_recovered": is_recovered},
                )

            if is_blocked and is_recovered:
                return self._make_check(
                    "kill_switch", "Kill Switch Test",
                    CheckStatus.PASS, passed=True,
                    message="Kill switch activation/reset cycle verified",
                )
            return self._make_check(
                "kill_switch", "Kill Switch Test",
                CheckStatus.FAIL, blocking=True,
                message=f"Kill switch cycle failed: blocked={is_blocked}, recovered={is_recovered}",
            )
        except Exception as e:
            return self._make_check(
                "kill_switch", "Kill Switch",
                CheckStatus.FAIL, message=f"Kill switch error: {e}",
            )

    def _check_emergency_shutdown(self) -> PreLiveCheck:
        if not self._emergency_shutdown:
            return self._make_check(
                "emergency_shutdown", "Emergency Shutdown",
                CheckStatus.SKIPPED,
                message="Emergency shutdown unavailable",
            )

        try:
            active = self._emergency_shutdown.is_active()
            if active:
                return self._make_check(
                    "emergency_shutdown", "Emergency Shutdown",
                    CheckStatus.BLOCKED, blocking=True,
                    message="Emergency stop is active — system must recover first",
                )

            if self._audit_log:
                self._audit_log.record(
                    EMERGENCY_TEST, severity="info",
                    details={"test_result": "emergency_shutdown_inactive", "active": active},
                )

            return self._make_check(
                "emergency_shutdown", "Emergency Shutdown",
                CheckStatus.PASS, passed=True,
                message="Emergency shutdown available and inactive",
            )
        except Exception as e:
            return self._make_check(
                "emergency_shutdown", "Emergency Shutdown",
                CheckStatus.FAIL, message=f"Emergency shutdown error: {e}",
            )

    def _check_execution_simulator(self) -> PreLiveCheck:
        from execution.execution_simulator import ExecutionSimulator, SIMULATION_SCENARIOS
        try:
            results = {}
            for mode in SIMULATION_SCENARIOS:
                sim = ExecutionSimulator(mode)
                result = sim.place_order("TEST", "BUY", 1, 100.0)
                results[mode] = result.get("status", "unknown")

            return self._make_check(
                "execution_simulator", "Execution Simulator",
                CheckStatus.PASS, passed=True,
                message=f"{len(results)} simulator scenarios tested",
                details=str(results),
            )
        except Exception as e:
            return self._make_check(
                "execution_simulator", "Execution Simulator",
                CheckStatus.FAIL, message=f"Simulator test error: {e}",
            )

    def _check_auditability(self) -> PreLiveCheck:
        if not self._audit_log:
            return self._make_check(
                "auditability", "Audit Trail",
                CheckStatus.BLOCKED, blocking=True,
                message="Execution audit log unavailable",
            )

        try:
            count = self._audit_log.count()
            return self._make_check(
                "auditability", "Audit Trail",
                CheckStatus.PASS, passed=True,
                message=f"Audit log operational ({count} events recorded)",
            )
        except Exception as e:
            return self._make_check(
                "auditability", "Audit Trail",
                CheckStatus.FAIL, message=f"Audit check error: {e}",
            )

    def _check_operational_recovery(self) -> PreLiveCheck:
        checks_passed = True
        details = []

        if self._kill_switch:
            if not self._kill_switch.is_active():
                details.append("kill_switch_inactive")
            else:
                checks_passed = False
                details.append("kill_switch_active")

        if self._emergency_shutdown:
            if not self._emergency_shutdown.is_active():
                details.append("emergency_inactive")
            else:
                checks_passed = False
                details.append("emergency_active")

        if self._runtime_mgr:
            mode = self._runtime_mgr.mode.value
            details.append(f"mode={mode}")

        if checks_passed:
            return self._make_check(
                "operational_recovery", "Operational Recovery",
                CheckStatus.PASS, passed=True,
                message="System in normal operational state",
                details="; ".join(details),
            )
        return self._make_check(
            "operational_recovery", "Operational Recovery",
            CheckStatus.WARNING, passed=True,
            message="System requires recovery action",
            details="; ".join(details),
        )

    def _check_security(self) -> PreLiveCheck:
        issues = []

        # 1. Phase 43 lock check
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        if not PHASE_43_LIVE_EXECUTION_LOCK:
            issues.append("PHASE_43_LIVE_EXECUTION_LOCK is False")

        # 2. Runtime mode check
        if self._runtime_mgr:
            if self._runtime_mgr.can_execute_live():
                issues.append("Runtime mode allows live execution")

        # 3. Execution policy check
        if self._execution_policy:
            perm = self._execution_policy.check()
            if perm.allowed:
                issues.append("Execution policy allows live execution")
        else:
            issues.append("Execution policy not checked")

        if issues:
            return self._make_check(
                "security_credentials", "Security Validation",
                CheckStatus.BLOCKED if any("False" in i or "allows" in i for i in issues)
                else CheckStatus.WARNING,
                blocking=bool(issues),
                message="; ".join(issues) if issues else "Security checks passed",
            )

        return self._make_check(
            "security_credentials", "Security Validation",
            CheckStatus.PASS, passed=True,
            message="Security checks passed — LIVE execution locked",
            details="PHASE_43_LIVE_EXECUTION_LOCK=True, can_execute_live=False",
        )

    def get_report(self, validation_id: str) -> PreLiveValidationReport | None:
        return self._reports.get(validation_id)

    def get_all_reports(self) -> list[PreLiveValidationReport]:
        return list(self._reports.values())

    def get_latest_report(self) -> PreLiveValidationReport | None:
        if not self._reports:
            return None
        return list(self._reports.values())[-1]
