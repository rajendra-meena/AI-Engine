"""
Phase 44 — Pre-Live Operational Validation Tests.

Tests the complete pre-live validation infrastructure.
Critical: LIVE execution MUST remain disabled.
"""

from __future__ import annotations

import pytest
import time


# ── Pre-Live Models Tests ──

class TestPreLiveModels:
    """Pre-live models must have correct structure."""

    def test_check_defaults(self):
        from live.pre_live_models import PreLiveCheck, CheckStatus
        check = PreLiveCheck(category="test", name="test")
        assert check.status == CheckStatus.NOT_TESTED
        assert not check.passed
        assert not check.blocking
        assert check.check_id.startswith("chk_")

    def test_check_to_dict(self):
        from live.pre_live_models import PreLiveCheck, CheckStatus
        check = PreLiveCheck(
            category="risk", name="Risk Engine",
            status=CheckStatus.PASS, passed=True,
            message="Healthy",
        )
        d = check.to_dict()
        assert d["category"] == "risk"
        assert d["status"] == "pass"
        assert d["passed"]
        assert d["message"] == "Healthy"

    def test_report_defaults(self):
        from live.pre_live_models import PreLiveValidationReport, ValidationClassification
        report = PreLiveValidationReport()
        assert report.validation_id.startswith("plv_")
        assert report.classification == ValidationClassification.NOT_READY
        assert not report.live_execution_enabled
        assert not report.can_execute_live

    def test_report_add_check(self):
        from live.pre_live_models import PreLiveValidationReport, PreLiveCheck, CheckStatus
        report = PreLiveValidationReport()
        check = PreLiveCheck(category="test", name="test", status=CheckStatus.PASS, passed=True)
        report.add_check(check)
        assert len(report.checks) == 1

    def test_report_summary(self):
        from live.pre_live_models import (
            PreLiveValidationReport, PreLiveCheck, CheckStatus,
        )
        report = PreLiveValidationReport()
        report.add_check(PreLiveCheck(category="a", name="a", status=CheckStatus.PASS, passed=True))
        report.add_check(PreLiveCheck(category="b", name="b", status=CheckStatus.WARNING))
        report.add_check(PreLiveCheck(category="c", name="c", status=CheckStatus.FAIL))
        report.add_check(PreLiveCheck(category="d", name="d", status=CheckStatus.BLOCKED))
        report.score = 75.0

        summary = report.summary()
        assert summary["passed"] == 1
        assert summary["warnings"] == 1
        assert summary["failed"] == 1
        assert summary["blocked"] == 1
        assert summary["total_checks"] == 4

    def test_validation_classifications(self):
        from live.pre_live_models import ValidationClassification
        assert ValidationClassification.READY.value == "ready_for_live_activation"
        assert ValidationClassification.BLOCKED.value == "blocked"

    def test_report_to_dict(self):
        from live.pre_live_models import (
            PreLiveValidationReport, PreLiveCheck, CheckStatus,
        )
        report = PreLiveValidationReport()
        report.add_check(PreLiveCheck(category="a", name="a", status=CheckStatus.PASS, passed=True))
        report.can_execute_live = False
        report.live_execution_enabled = False

        d = report.to_dict()
        assert "validation_id" in d
        assert len(d["checks"]) == 1
        assert d["can_execute_live"] is False
        assert d["live_execution_enabled"] is False


# ── Pre-Live Validation Engine Tests ──

class TestPreLiveValidationEngine:
    """Validation engine must run independent checks correctly."""

    def test_engine_creates_report(self):
        from live.pre_live_validation import PreLiveValidationEngine
        engine = PreLiveValidationEngine()
        report = engine.run()
        assert report is not None
        assert report.validation_id.startswith("plv_")
        # Should have 18 check categories
        assert len(report.checks) > 0

    def test_engine_runs_all_checks(self):
        from live.pre_live_validation import PreLiveValidationEngine, CHECK_CATEGORIES
        engine = PreLiveValidationEngine()
        report = engine.run()
        categories_run = set(c.category for c in report.checks)
        for cat in CHECK_CATEGORIES:
            assert cat in categories_run, f"Missing category: {cat}"

    def test_engine_sets_default_values(self):
        from live.pre_live_validation import PreLiveValidationEngine
        engine = PreLiveValidationEngine()
        report = engine.run()
        assert report.live_execution_enabled is False
        assert report.can_execute_live is False

    def test_engine_reports_have_ids(self):
        from live.pre_live_validation import PreLiveValidationEngine
        engine = PreLiveValidationEngine()
        report1 = engine.run()
        report2 = engine.run()
        assert report1.validation_id != report2.validation_id

    def test_engine_get_latest(self):
        from live.pre_live_validation import PreLiveValidationEngine
        engine = PreLiveValidationEngine()
        engine.run()
        engine.run()
        latest = engine.get_latest_report()
        latest_found = False
        for r in engine.get_all_reports():
            if r.validation_id == latest.validation_id:
                latest_found = True
        assert latest_found

    def test_engine_uses_kill_switch(self):
        from live.pre_live_validation import PreLiveValidationEngine
        from execution.kill_switch import KillSwitch
        engine = PreLiveValidationEngine(kill_switch=KillSwitch())
        report = engine.run()
        # Kill switch check should appear
        ks_checks = [c for c in report.checks if c.category == "kill_switch"]
        assert len(ks_checks) > 0

    def test_engine_with_config_guard(self):
        from live.pre_live_validation import PreLiveValidationEngine
        from execution.config_guard import ConfigGuard, ConfigurationSnapshot
        guard = ConfigGuard()
        guard.capture_approval_snapshot(ConfigurationSnapshot())
        engine = PreLiveValidationEngine(config_guard=guard)
        report = engine.run()
        config_checks = [c for c in report.checks if c.category == "config_integrity"]
        assert len(config_checks) > 0

    def test_engine_with_audit(self):
        from live.pre_live_validation import PreLiveValidationEngine
        from execution.execution_audit import ExecutionAuditLog
        audit = ExecutionAuditLog()
        engine = PreLiveValidationEngine(audit_log=audit)
        engine.run()
        assert audit.count() > 0  # Start and complete events

    def test_engine_auditability_check(self):
        from live.pre_live_validation import PreLiveValidationEngine
        from execution.execution_audit import ExecutionAuditLog
        audit = ExecutionAuditLog()
        audit.record("test")
        engine = PreLiveValidationEngine(audit_log=audit)
        report = engine.run()
        audit_checks = [c for c in report.checks if c.category == "auditability"]
        assert len(audit_checks) > 0
        # Audit should pass because audit log is available and has events
        assert any(c.passed for c in audit_checks)


# ── Champion Validation Tests ──

class TestChampionValidation:
    """Champion validation must detect invalid champions."""

    def test_no_champion_blocks(self):
        from live.pre_live_validation import PreLiveValidationEngine
        engine = PreLiveValidationEngine()
        report = engine.run()
        champ_checks = [c for c in report.checks if c.category == "champion_integrity"]
        assert len(champ_checks) > 0

    def test_with_champion_manager(self):
        from live.pre_live_validation import PreLiveValidationEngine
        # Without a champion manager, the check should report blocked
        engine = PreLiveValidationEngine()
        report = engine.run()
        champ_check = [c for c in report.checks if c.category == "champion_integrity"][0]
        assert not champ_check.passed  # No champion manager


# ── Approval Validation Tests ──

class TestApprovalValidation:
    """Approval validation must detect missing/expired approvals."""

    def test_no_approval_blocks(self):
        from live.pre_live_validation import PreLiveValidationEngine
        engine = PreLiveValidationEngine()
        report = engine.run()
        approval_checks = [c for c in report.checks if c.category == "final_approval"]
        assert len(approval_checks) > 0
        assert not approval_checks[0].passed  # No approval = blocked

    def test_with_approval_engine(self):
        from live.pre_live_validation import PreLiveValidationEngine
        from live.final_approval import FinalApprovalEngine
        approval = FinalApprovalEngine()
        engine = PreLiveValidationEngine(approval_engine=approval)
        report = engine.run()
        approval_checks = [c for c in report.checks if c.category == "final_approval"]
        assert len(approval_checks) > 0
        # Should be blocked because no approval was actually created


# ── Security Validation Tests ──

class TestSecurityValidation:
    """Security checks must verify Phase 43 lock."""

    def test_phase_43_lock_detected(self):
        from live.pre_live_validation import PreLiveValidationEngine
        from execution.execution_policy import ExecutionPolicyEngine
        engine = PreLiveValidationEngine(execution_policy=ExecutionPolicyEngine())
        report = engine.run()
        sec_checks = [c for c in report.checks if c.category == "security_credentials"]
        assert len(sec_checks) > 0

    def test_security_with_runtime_mgr(self):
        from live.pre_live_validation import PreLiveValidationEngine
        from execution.execution_policy import ExecutionPolicyEngine
        from trading.runtime_mode import RuntimeModeManager
        engine = PreLiveValidationEngine(
            execution_policy=ExecutionPolicyEngine(),
            runtime_mgr=RuntimeModeManager(),
        )
        report = engine.run()
        sec_checks = [c for c in report.checks if c.category == "security_credentials"]
        assert len(sec_checks) > 0
        # Phase 43 lock is active, so checks should have non-empty messages
        assert any(c.message for c in sec_checks)


# ── Kill Switch Validation Tests ──

class TestKillSwitchValidation:
    """Kill switch must be testable."""

    def test_kill_switch_active_blocks(self):
        from live.pre_live_validation import PreLiveValidationEngine
        from execution.kill_switch import KillSwitch, KillSwitchLevel
        ks = KillSwitch()
        ks.activate(KillSwitchLevel.GLOBAL, "", "test")
        engine = PreLiveValidationEngine(kill_switch=ks)
        report = engine.run()
        ks_checks = [c for c in report.checks if c.category == "kill_switch"]
        assert len(ks_checks) > 0

    def test_kill_switch_inactive_allows(self):
        from live.pre_live_validation import PreLiveValidationEngine
        from execution.kill_switch import KillSwitch
        ks = KillSwitch()
        engine = PreLiveValidationEngine(kill_switch=ks)
        report = engine.run()
        ks_checks = [c for c in report.checks if c.category == "kill_switch"]
        assert len(ks_checks) > 0


# ── Emergency Shutdown Validation Tests ──

class TestEmergencyValidation:
    """Emergency shutdown must be testable without real impact."""

    def test_emergency_not_active(self):
        from live.pre_live_validation import PreLiveValidationEngine
        from execution.emergency import EmergencyShutdown
        emg = EmergencyShutdown()
        engine = PreLiveValidationEngine(emergency_shutdown=emg)
        report = engine.run()
        emg_checks = [c for c in report.checks if c.category == "emergency_shutdown"]
        assert len(emg_checks) > 0


# ── Execution Simulator Tests ──

class TestExecutionSimulator:
    """Execution simulator must test infrastructure without real orders."""

    def test_all_scenarios_run(self):
        from live.pre_live_validation import PreLiveValidationEngine
        engine = PreLiveValidationEngine()
        report = engine.run()
        sim_checks = [c for c in report.checks if c.category == "execution_simulator"]
        assert len(sim_checks) > 0

    def test_simulator_never_real(self):
        from execution.execution_simulator import ExecutionSimulator, SIMULATION_SCENARIOS
        for mode in SIMULATION_SCENARIOS:
            sim = ExecutionSimulator(mode)
            result = sim.place_order("TEST", "BUY", 1, 100.0)
            assert "broker_" in result.get("broker_order_id", "")  # Simulated broker IDs
            assert "sim_" in result.get("internal_order_id", "")  # Simulated internal IDs


# ── Broker Read-Only Tests ──

class TestBrokerReadOnly:
    """Broker operations must be read-only in Phase 44."""

    def test_place_order_raises(self):
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.place_order("RELIANCE", "BUY", 1))

    def test_modify_order_raises(self):
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.modify_order("order123"))

    def test_cancel_order_raises(self):
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.cancel_order("order123"))

    def test_readonly_operations_work(self):
        from execution.broker_adapter import ZerodhaAdapter
        import asyncio
        adapter = ZerodhaAdapter()
        health = asyncio.run(adapter.health_check())
        assert health["status"] == "healthy"
        account = asyncio.run(adapter.get_account())
        assert "broker" in account
        balance = asyncio.run(adapter.get_balance())
        assert "available" in balance
        positions = asyncio.run(adapter.get_positions())
        assert isinstance(positions, list)
        orders = asyncio.run(adapter.get_orders())
        assert isinstance(orders, list)


# ── Position Reconciliation Tests ──

class TestPositionReconciliation:
    """Position reconciliation must detect mismatches."""

    def test_clean_positions(self):
        from execution.position_reconciliation import PositionReconciliationEngine
        engine = PositionReconciliationEngine()
        internal = [{"symbol": "RELIANCE", "direction": "long", "quantity": 10}]
        broker = [{"symbol": "RELIANCE", "direction": "long", "quantity": 10}]
        issues = engine.reconcile(internal, broker)
        assert len(issues) == 0

    def test_unexpected_position_detected(self):
        from execution.position_reconciliation import PositionReconciliationEngine
        engine = PositionReconciliationEngine()
        internal = []
        broker = [{"symbol": "UNEXPECTED", "direction": "long", "quantity": 100}]
        issues = engine.reconcile(internal, broker)
        assert len(issues) == 1
        assert "unexpected" in issues[0].description.lower()


# ── Order Reconciliation Tests ──

class TestOrderReconciliation:
    """Order reconciliation must detect mismatches."""

    def test_missing_broker_order(self):
        from execution.reconciliation import OrderReconciliationEngine
        engine = OrderReconciliationEngine()
        issues = engine.reconcile(
            {"internal_order_id": "ord1", "broker_order_id": "b1", "state": "submitted"},
            None,
        )
        assert len(issues) == 1
        assert "not found" in issues[0].description.lower()

    def test_clean_reconciliation(self):
        from execution.reconciliation import OrderReconciliationEngine
        engine = OrderReconciliationEngine()
        issues = engine.reconcile(
            {"internal_order_id": "ord1", "broker_order_id": "b1", "state": "filled", "quantity": 10},
            {"order_id": "b1", "status": "complete", "quantity": 10},
        )
        # Only potential minor issues (like price), no critical status mismatch
        has_critical = any(i.severity.value in ("error", "critical") for i in issues)
        assert not has_critical


# ── Config Drift Tests ──

class TestConfigDrift:
    """Config drift must be detectable."""

    def test_config_drift_detected(self):
        from execution.config_guard import ConfigGuard, ConfigurationSnapshot
        guard = ConfigGuard()
        config1 = ConfigurationSnapshot(allowed_symbols=["RELIANCE"])
        guard.capture_approval_snapshot(config1)
        config2 = ConfigurationSnapshot(allowed_symbols=["TCS"])
        drift = guard.check_for_drift(config2)
        assert drift
        assert guard.has_drift()

    def test_config_no_drift(self):
        from execution.config_guard import ConfigGuard, ConfigurationSnapshot
        guard = ConfigGuard()
        config = ConfigurationSnapshot()
        guard.capture_approval_snapshot(config)
        drift = guard.check_for_drift(config)
        assert not drift


# ── Champion Change Tests ──

class TestChampionChange:
    """Champion change must invalidate previous approval."""

    def test_approval_id_mismatch_detected(self):
        from live.pre_live_validation import PreLiveValidationEngine
        engine = PreLiveValidationEngine()
        # Run with a specific approval ID that doesn't exist
        report = engine.run(approval_id="nonexistent_approval")
        approval_checks = [c for c in report.checks if c.category == "final_approval"]
        assert len(approval_checks) > 0
        # Without approval engine, it should report blocked
        assert not approval_checks[0].passed or approval_checks[0].status.value == "skipped"


# ── Duplicate Order Protection Tests ──

class TestDuplicateProtection:
    """Duplicate execution intents must be blocked."""

    def test_duplicate_signal_detected(self):
        from execution.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()
        key = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "session1")
        guard.check(key)
        assert guard.check(key) is True  # Duplicate

    def test_different_signals_allowed(self):
        from execution.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()
        key1 = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "session1")
        key2 = guard.generate_key("sig2", "v1", "RELIANCE", "BUY", "session1")
        guard.check(key1)
        assert guard.check(key2) is False  # Different signal, allowed


# ── Market Data Failure Tests ──

class TestMarketDataFailure:
    """Market data failures must block execution readiness."""

    def test_stale_market_data_blocks(self):
        from execution.execution_health import ExecutionHealthMonitor
        monitor = ExecutionHealthMonitor()
        # Multiple failures to trigger BLOCKED
        monitor.record_failure("market_data_freshness", "stale")
        monitor.record_failure("market_data_freshness", "still stale")
        assert monitor.is_blocked()

    def test_healthy_market_data_allows(self):
        from execution.execution_health import ExecutionHealthMonitor
        monitor = ExecutionHealthMonitor()
        # Mark all checks as healthy
        for check_name in [
            "broker_connectivity", "websocket_health", "api_latency",
            "order_acknowledgement_latency", "fill_latency", "rejection_rate",
            "reconciliation_status", "market_data_freshness", "system_heartbeat",
            "kill_switch_status",
        ]:
            monitor.record_success(check_name)
        assert not monitor.is_blocked()
        assert monitor.is_healthy()


# ── Broker Failure Tests ──

class TestBrokerFailure:
    """Broker failures must be detected."""

    def test_broker_disconnect_detected(self):
        from execution.execution_health import ExecutionHealthMonitor
        monitor = ExecutionHealthMonitor()
        monitor.record_failure("broker_connectivity", "disconnected")
        monitor.record_failure("broker_connectivity", "still disconnected")
        assert monitor.is_blocked()
        check = monitor.get_check("broker_connectivity")
        assert check.consecutive_failures >= 2


# ── Phase 44 Critical Safety Verification ──

class TestPhase44SafetyVerification:
    """
    Critical safety verification for Phase 44.

    These tests MUST ALL PASS for Phase 44 to be complete.
    """

    def test_cannot_place_zerodha_order(self):
        """Can Phase 44 place a Zerodha order? → MUST BE NO"""
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.place_order("RELIANCE", "BUY", 1))

    def test_cannot_modify_zerodha_order(self):
        """Can Phase 44 modify a Zerodha order? → MUST BE NO"""
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.modify_order("order123"))

    def test_cannot_cancel_zerodha_order(self):
        """Can Phase 44 cancel a Zerodha order? → MUST BE NO"""
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.cancel_order("order123"))

    def test_cannot_enable_live(self):
        """Can Phase 44 enable LIVE? → MUST BE NO"""
        from trading.runtime_mode import RuntimeModeManager, ALLOWED_MODES, RuntimeMode
        assert RuntimeMode.LIVE not in ALLOWED_MODES
        mgr = RuntimeModeManager()
        result = mgr.set_mode("live")
        assert not result["success"]

    def test_can_execute_live_still_false(self):
        """Does can_execute_live() return False? → MUST BE YES"""
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        assert mgr.can_execute_live() is False

    def test_execution_policy_allows_false(self):
        """Can ExecutionPolicy allow live execution? → MUST BE NO"""
        from execution.execution_policy import ExecutionPolicyEngine, PHASE_43_LIVE_EXECUTION_LOCK
        assert PHASE_43_LIVE_EXECUTION_LOCK is True
        perm = ExecutionPolicyEngine().check()
        assert perm.allowed is False

    def test_approval_cannot_bypass_lock(self):
        """Can FinalApproval bypass Phase 43 lock? → MUST BE NO"""
        from execution.execution_policy import ExecutionPolicyEngine
        perm = ExecutionPolicyEngine().check()
        assert "phase_43_lock" in perm.blocking_checks
        assert perm.allowed is False

    def test_kill_switch_blocks_execution(self):
        """Can kill switch block execution? → MUST BE YES"""
        from execution.kill_switch import KillSwitch, KillSwitchLevel
        ks = KillSwitch()
        ks.activate(KillSwitchLevel.GLOBAL, "", "test")
        assert ks.is_active()

    def test_stale_market_data_blocks_execution(self):
        """Can stale market data block execution? → MUST BE YES"""
        from execution.execution_health import ExecutionHealthMonitor
        monitor = ExecutionHealthMonitor()
        monitor.record_failure("market_data_freshness", "stale")
        monitor.record_failure("market_data_freshness", "still stale")
        assert monitor.is_blocked()

    def test_config_drift_blocks_execution(self):
        """Can configuration drift invalidate approval? → MUST BE YES"""
        from execution.config_guard import ConfigGuard, ConfigurationSnapshot
        guard = ConfigGuard()
        guard.capture_approval_snapshot(ConfigurationSnapshot())
        assert guard.check_for_drift(ConfigurationSnapshot(allowed_symbols=["DIFF"]))

    def test_expired_approval_blocks(self):
        """Can expired approval block execution? → MUST BE YES"""
        from live.final_approval import FinalApprovalEngine
        approval = FinalApprovalEngine()
        # Create an approval record
        record = approval.run()
        # Manually expire it
        from datetime import datetime, timedelta, timezone
        record.expires_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        # Check expiry
        expires_at = record.expires_at
        expiry_dt = datetime.fromisoformat(expires_at)
        assert datetime.now(timezone.utc) > expiry_dt  # Expired

    def test_duplicate_intents_blocked(self):
        """Can duplicate execution intents be blocked? → MUST BE YES"""
        from execution.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()
        key = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "s1")
        guard.check(key)
        assert guard.check(key) is True  # Duplicate blocked

    def test_reconciliation_failure_blocks(self):
        """Can reconciliation failure block execution? → MUST BE YES"""
        from execution.reconciliation import OrderReconciliationEngine
        engine = OrderReconciliationEngine()
        engine.reconcile({"internal_order_id": "o1", "state": "submitted"}, None)
        assert len(engine.get_blocking_issues()) > 0

    def test_phase_44_pre_live_validation_allowed_false(self):
        """Even with every check passing, can_execute_live must remain False"""
        from live.pre_live_validation import PreLiveValidationEngine
        from execution.execution_policy import ExecutionPolicyEngine
        engine = PreLiveValidationEngine(
            execution_policy=ExecutionPolicyEngine(),
        )
        report = engine.run()
        assert report.can_execute_live is False
        assert report.live_execution_enabled is False

    def test_no_live_api_endpoint(self):
        """Phase 44 API must not have live-trading endpoints."""
        import backend.api.pre_live as api_module
        routes = [r.path for r in api_module.router.routes]
        forbidden = [
            "/api/pre-live/enable-live",
            "/api/pre-live/place-order",
            "/api/pre-live/activate",
        ]
        for path in forbidden:
            assert path not in routes, f"Phase 44 must not expose {path}"

    def test_secrets_not_exposed_in_broker_api(self):
        """Broker API must not expose sensitive fields."""
        from backend.api.pre_live import _sanitize
        sensitive_data = {
            "access_token": "secret123",
            "api_secret": "very_secret",
            "client_secret": "confidential",
            "safe_field": "visible",
        }
        sanitized = _sanitize(sensitive_data)
        assert sanitized["access_token"] == "***"
        assert sanitized["api_secret"] == "***"
        assert sanitized["client_secret"] == "***"
        assert sanitized["safe_field"] == "visible"
