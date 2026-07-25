"""
Phase 50 — Production Reliability, Recovery & 24/7 Operations Tests.

Tests heartbeats, watchdogs, alerts, persistence, recovery, reconciliation,
config integrity, disaster recovery, and safety invariants.
"""

from __future__ import annotations

import pytest
import time
from datetime import datetime, timezone, timedelta


# ═══════════════════════════════════════════════
# Operational State Tests
# ═══════════════════════════════════════════════

class TestOperationalState:
    """Operational state machine."""

    def test_valid_transitions(self):
        from ops.operational_state import validate_op_state_transition, OperationalState
        assert validate_op_state_transition(OperationalState.STARTING, OperationalState.READY)
        assert validate_op_state_transition(OperationalState.READY, OperationalState.DEGRADED)
        assert validate_op_state_transition(OperationalState.TRADING_BLOCKED, OperationalState.RECOVERY_REQUIRED)
        assert validate_op_state_transition(OperationalState.HALTED, OperationalState.STARTING)

    def test_recovery_cannot_transition_to_ready(self):
        """Recovery must never directly transition to READY."""
        from ops.operational_state import validate_op_state_transition, OperationalState
        assert not validate_op_state_transition(OperationalState.RECOVERY_REQUIRED, OperationalState.READY)
        assert not validate_op_state_transition(OperationalState.ROLLBACK_REQUIRED, OperationalState.READY)

    def test_halted_can_start(self):
        from ops.operational_state import validate_op_state_transition, OperationalState
        assert validate_op_state_transition(OperationalState.HALTED, OperationalState.STARTING)


# ═══════════════════════════════════════════════
# Heartbeat Tests
# ═══════════════════════════════════════════════

class TestHeartbeat:
    """Heartbeat service."""

    def test_beat_records(self):
        from ops.heartbeat import HeartbeatService
        hb = HeartbeatService()
        hb.beat("application", "healthy", 5.0)
        record = hb.get_record("application")
        assert record.status == "healthy"
        assert record.latency_ms == 5.0

    def test_initial_state(self):
        from ops.heartbeat import HeartbeatService, COMPONENTS
        hb = HeartbeatService()
        statuses = hb.get_statuses()
        for comp in COMPONENTS:
            assert comp in statuses
            assert statuses[comp]["status"] == "unknown"

    def test_check_missed(self):
        from ops.heartbeat import HeartbeatService
        hb = HeartbeatService(timeout_seconds=1)
        import time
        time.sleep(1.5)
        missed = hb.check_missed(timeout_seconds=1)
        assert len(missed) > 0

    def test_all_components_healthy(self):
        from ops.heartbeat import HeartbeatService, COMPONENTS
        hb = HeartbeatService()
        for comp in COMPONENTS:
            hb.beat(comp, "healthy", 0)
        summary = hb.get_summary()
        assert summary["all_healthy"]


# ═══════════════════════════════════════════════
# Health Monitor Tests
# ═══════════════════════════════════════════════

class TestHealthMonitor:
    """System health monitor."""

    def test_initial_healthy(self):
        from ops.health_monitor import SystemHealthMonitor
        mon = SystemHealthMonitor()
        assert mon.get_status() == "healthy"

    def test_snapshot_structure(self):
        from ops.health_monitor import SystemHealthMonitor
        mon = SystemHealthMonitor()
        snap = mon.snapshot()
        assert "status" in snap
        assert "component_statuses" in snap
        assert "uptime_seconds" in snap

    def test_critical_failure(self):
        from ops.health_monitor import SystemHealthMonitor
        mon = SystemHealthMonitor()
        mon.update_component("broker", "critical")
        assert mon.get_status() == "critical"


# ═══════════════════════════════════════════════
# Market Data Watchdog Tests
# ═══════════════════════════════════════════════

class TestMarketDataWatchdog:
    """Market data health."""

    def test_initial_state(self):
        from ops.market_data_watchdog import MarketDataWatchdog
        wd = MarketDataWatchdog()
        health = wd.get_health()
        assert health.state in ("unknown", "healthy")

    def test_healthy_after_tick(self):
        from ops.market_data_watchdog import MarketDataWatchdog
        wd = MarketDataWatchdog()
        wd.record_tick()
        health = wd.get_health()
        assert health.websocket_connected
        assert health.last_tick_timestamp != ""

    def test_disconnect_detected(self):
        from ops.market_data_watchdog import MarketDataWatchdog
        wd = MarketDataWatchdog()
        wd.record_disconnect()
        assert not wd._health.websocket_connected
        assert wd._health.reconnect_attempts == 1

    def test_trading_blocked_on_stale(self):
        from ops.market_data_watchdog import MarketDataWatchdog
        wd = MarketDataWatchdog()
        # Simulate stale by setting last_tick to old timestamp
        wd.record_tick("2020-01-01T00:00:00+00:00")
        assert wd.is_trading_blocked()


# ═══════════════════════════════════════════════
# Broker Watchdog Tests
# ═══════════════════════════════════════════════

class TestBrokerWatchdog:
    """Broker health monitoring."""

    def test_initial_state(self):
        from ops.broker_watchdog import BrokerWatchdog
        wd = BrokerWatchdog()
        health = wd.get_health()
        assert health.state in ("unknown", "not_configured")


# ═══════════════════════════════════════════════
# Execution Watchdog Tests
# ═══════════════════════════════════════════════

class TestExecutionWatchdog:
    """Execution health monitoring."""

    def test_initial_healthy(self):
        from ops.execution_watchdog import ExecutionWatchdog
        wd = ExecutionWatchdog()
        health = wd.get_health()
        assert health.state == "healthy"

    def test_unknown_order_triggers_reconciliation(self):
        from ops.execution_watchdog import ExecutionWatchdog
        wd = ExecutionWatchdog()
        wd.record_order_unknown("order_123")
        assert wd.is_reconciliation_required()
        health = wd.get_health()
        assert "order_123" in health.reconciliation_required

    def test_duplicate_tracking(self):
        from ops.execution_watchdog import ExecutionWatchdog
        wd = ExecutionWatchdog()
        wd.record_duplicate_attempt()
        health = wd.get_health()
        assert health.duplicate_attempts == 1


# ═══════════════════════════════════════════════
# Alert Manager Tests
# ═══════════════════════════════════════════════

class TestAlertManager:
    """Alert management."""

    def test_raise_alert(self):
        from ops.alert_manager import AlertManager, AlertSeverity, AlertCategory
        am = AlertManager()
        alert = am.raise_alert(AlertSeverity.CRITICAL, AlertCategory.BROKER,
                                message="Broker disconnected")
        assert alert.severity == "critical"
        assert alert.status == "open"
        assert am.active_count() == 1

    def test_acknowledge_alert(self):
        from ops.alert_manager import AlertManager, AlertSeverity, AlertCategory
        am = AlertManager()
        alert = am.raise_alert(AlertSeverity.WARNING, AlertCategory.SYSTEM,
                                message="Test")
        am.acknowledge(alert.alert_id, reviewer="admin")
        assert alert.status == "acknowledged"

    def test_resolve_alert(self):
        from ops.alert_manager import AlertManager
        am = AlertManager()
        alert = am.raise_alert("info", "system", "Test")
        am.resolve(alert.alert_id, resolution="Fixed")
        assert alert.status == "resolved"

    def test_alert_history(self):
        from ops.alert_manager import AlertManager
        am = AlertManager()
        am.raise_alert("info", "system", "Alert 1")
        am.raise_alert("warning", "broker", "Alert 2")
        assert len(am.get_history()) == 2


# ═══════════════════════════════════════════════
# Persistence Tests
# ═══════════════════════════════════════════════

class TestPersistence:
    """State persistence."""

    def test_save_and_load(self):
        from ops.persistence_manager import PersistenceManager, PersistedState
        import tempfile
        import os
        tmpdir = tempfile.mkdtemp()
        pm = PersistenceManager(dir_path=tmpdir)
        state = PersistedState(rollout_stage="canary_1", champion_id="champ_v1")
        saved = pm.save(state)
        assert saved

        loaded = pm.load()
        assert loaded is not None
        assert loaded.rollout_stage == "canary_1"
        assert loaded.champion_id == "champ_v1"

        # Cleanup
        import shutil
        shutil.rmtree(tmpdir)

    def test_backup_verification(self):
        from ops.persistence_manager import PersistenceManager, PersistedState
        import tempfile
        tmpdir = tempfile.mkdtemp()
        pm = PersistenceManager(dir_path=tmpdir)
        state = PersistedState()
        pm.save(state)
        info = pm.verify_backup()
        assert info["exists"]
        assert info["valid"]

        import shutil
        shutil.rmtree(tmpdir)

    def test_no_backup(self):
        from ops.persistence_manager import PersistenceManager
        import tempfile
        tmpdir = tempfile.mkdtemp()
        pm = PersistenceManager(dir_path=tmpdir)
        assert not pm.backup_exists()
        loaded = pm.load()
        assert loaded is None

        import shutil
        shutil.rmtree(tmpdir)


# ═══════════════════════════════════════════════
# Recovery Tests
# ═══════════════════════════════════════════════

class TestRecovery:
    """Recovery manager."""

    def test_startup_recovery(self):
        from ops.recovery_manager import RecoveryManager
        rm = RecoveryManager()
        result = rm.startup_recovery()
        assert not result.success or result.state == "recovery_required"

    def test_recovery_does_not_auto_resume(self):
        """Recovery must not auto-resume to ready."""
        from ops.recovery_manager import RecoveryManager
        rm = RecoveryManager()
        result = rm.startup_recovery()
        assert result.state != "ready"

    def test_human_recovery_required(self):
        from ops.recovery_manager import RecoveryManager
        rm = RecoveryManager()
        result = rm.request_human_recovery(reviewer="")
        assert not result["success"]

    def test_human_recovery_works(self):
        from ops.recovery_manager import RecoveryManager
        rm = RecoveryManager()
        result = rm.request_human_recovery(reviewer="admin")
        assert result["success"]
        assert rm.get_state() == "ready"

    def test_graceful_shutdown(self):
        from ops.recovery_manager import RecoveryManager
        rm = RecoveryManager()
        result = rm.graceful_shutdown()
        assert result["success"]
        assert result["state"] == "shutdown"


# ═══════════════════════════════════════════════
# Daily Reconciliation Tests
# ═══════════════════════════════════════════════

class TestDailyReconciliation:
    """Daily/intraday reconciliation."""

    def test_empty_reconciliation(self):
        from ops.daily_reconciliation import DailyReconciliationEngine
        engine = DailyReconciliationEngine()
        report = engine.reconcile()
        assert report.matched_orders == 0
        assert report.matched_positions == 0

    def test_order_matching(self):
        from ops.daily_reconciliation import DailyReconciliationEngine
        engine = DailyReconciliationEngine()
        internal = [{"broker_order_id": "o1", "status": "filled"}]
        broker = [{"order_id": "o1", "status": "filled"}]
        report = engine.reconcile(internal_orders=internal, broker_orders=broker)
        assert report.matched_orders >= 1

    def test_order_mismatch_detected(self):
        from ops.daily_reconciliation import DailyReconciliationEngine
        engine = DailyReconciliationEngine()
        internal = [{"broker_order_id": "o1", "status": "filled"}]
        broker = [{"order_id": "o1", "status": "open"}]
        report = engine.reconcile(internal_orders=internal, broker_orders=broker)
        assert report.mismatched_orders >= 1
        assert len(report.critical_events) > 0

    def test_missing_broker_order(self):
        from ops.daily_reconciliation import DailyReconciliationEngine
        engine = DailyReconciliationEngine()
        internal = [{"broker_order_id": "o1", "status": "filled"}]
        report = engine.reconcile(internal_orders=internal)
        assert report.unknown_orders >= 1


# ═══════════════════════════════════════════════
# Config Integrity Tests
# ═══════════════════════════════════════════════

class TestConfigIntegrity:
    """Config integrity monitoring."""

    def test_baseline_matches(self):
        from ops.config_integrity import ConfigIntegrityMonitor
        mon = ConfigIntegrityMonitor()
        result = mon.check_integrity()
        assert result.passed

    def test_result_structure(self):
        from ops.config_integrity import ConfigIntegrityResult
        r = ConfigIntegrityResult(passed=True)
        d = r.to_dict()
        assert d["passed"] is True
        assert "champion_unchanged" in d


# ═══════════════════════════════════════════════
# Safety Regression Tests
# ═══════════════════════════════════════════════

class TestPhase50SafetyVerification:
    """Critical safety tests for Phase 50."""

    def test_phase_43_lock_still_true(self):
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        assert PHASE_43_LIVE_EXECUTION_LOCK is True

    def test_can_execute_live_still_false(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        assert mgr.can_execute_live() is False

    def test_zerodha_adapter_still_raises(self):
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.place_order("RELIANCE", "BUY", 1))

    def test_no_unrestricted_live_endpoint(self):
        import backend.api.operations as api_module
        routes = [r.path for r in api_module.router.routes]
        forbidden = ["enable-live", "disable-lock", "bypass-safety",
                     "increase-limits", "start-auto-trading"]
        for path in routes:
            for f in forbidden:
                assert f not in path, f"Route {path} contains '{f}'"

    def test_recovery_never_auto_resumes(self):
        from ops.recovery_manager import RecoveryManager
        rm = RecoveryManager()
        result = rm.startup_recovery()
        assert result.state != "ready"

    def test_ops_state_recovery_no_direct_ready(self):
        from ops.operational_state import validate_op_state_transition, OperationalState
        assert not validate_op_state_transition(OperationalState.RECOVERY_REQUIRED, OperationalState.READY)

    def test_all_previous_tests_importable(self):
        import tests.live.test_phase44_pre_live  # noqa
        import tests.live.test_phase45_live_activation  # noqa
        import tests.live.test_phase46_execution  # noqa
        import tests.live.test_phase47_canary  # noqa
        import tests.live.test_phase48_canary_evaluation  # noqa
        import tests.live.test_phase49_progressive_rollout  # noqa
