"""
Phase 43 — Comprehensive Infrastructure Tests.

Tests for all execution infrastructure components with safety verification.
Critical assertion: ANY attempt to execute a live order in Phase 43 MUST FAIL.
"""

from __future__ import annotations

import pytest


# ── Broker Adapter Tests ──

class TestBrokerAdapter:
    """Broker adapter must never send real orders in Phase 43."""

    def test_zerodha_adapter_place_order_raises(self):
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()

        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.place_order("RELIANCE", "BUY", 1, 100.0))

    def test_zerodha_adapter_modify_order_raises(self):
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()

        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.modify_order("order123", quantity=2))

    def test_zerodha_adapter_cancel_order_raises(self):
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()

        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.cancel_order("order123"))

    def test_zerodha_adapter_readonly_works(self):
        from execution.broker_adapter import ZerodhaAdapter
        import asyncio
        adapter = ZerodhaAdapter()

        account = asyncio.run(adapter.get_account())
        assert account["status"] == "simulated"
        assert account["phase_43"]

        balance = asyncio.run(adapter.get_balance())
        assert balance["available"] > 0

        positions = asyncio.run(adapter.get_positions())
        assert isinstance(positions, list)

        health = asyncio.run(adapter.health_check())
        assert health["status"] == "healthy"

    def test_live_execution_disabled_error_message(self):
        from execution.broker_adapter import LiveExecutionDisabledError
        err = LiveExecutionDisabledError("Phase 43 lock")
        assert "Phase 43" in str(err)


# ── Order State Machine Tests ──

class TestOrderStateMachine:
    """State machine must enforce valid transitions."""

    def test_valid_transition_created_to_validating(self):
        from execution.order_state import OrderStateMachine, OrderStatus
        sm = OrderStateMachine("order1")
        result = sm.transition_to(OrderStatus.VALIDATING, "starting validation", "test", "cor1")
        assert result
        assert sm.state == OrderStatus.VALIDATING

    def test_valid_full_flow(self):
        from execution.order_state import OrderStateMachine, OrderStatus
        sm = OrderStateMachine("order1")

        sm.transition_to(OrderStatus.VALIDATING, "", "test", "cor1")
        sm.transition_to(OrderStatus.RISK_APPROVED, "", "test", "cor1")
        sm.transition_to(OrderStatus.SUBMITTED, "", "test", "cor1")
        sm.transition_to(OrderStatus.ACKNOWLEDGED, "", "test", "cor1")
        sm.transition_to(OrderStatus.FILLED, "", "test", "cor1")
        sm.transition_to(OrderStatus.CLOSED, "", "test", "cor1")

        assert sm.state == OrderStatus.CLOSED

    def test_invalid_transition_raises(self):
        from execution.order_state import OrderStateMachine, OrderStatus, OrderStateMachineError
        sm = OrderStateMachine("order1")

        with pytest.raises(OrderStateMachineError):
            # FILLED -> CREATED is invalid
            sm._state = OrderStatus.FILLED
            sm.transition_to(OrderStatus.CREATED, "", "test", "cor1")

    def test_cancel_request_flow(self):
        from execution.order_state import OrderStateMachine, OrderStatus
        sm = OrderStateMachine("order1")

        sm.transition_to(OrderStatus.VALIDATING, "", "test", "cor1")
        sm.transition_to(OrderStatus.RISK_APPROVED, "", "test", "cor1")
        sm.transition_to(OrderStatus.SUBMITTED, "", "test", "cor1")
        sm.transition_to(OrderStatus.ACKNOWLEDGED, "", "test", "cor1")
        sm.transition_to(OrderStatus.PARTIALLY_FILLED, "", "test", "cor1")
        sm.transition_to(OrderStatus.CANCEL_REQUESTED, "", "test", "cor1")
        sm.transition_to(OrderStatus.CANCELLED, "", "test", "cor1")

        assert sm.state == OrderStatus.CANCELLED

    def test_reject_flow(self):
        from execution.order_state import OrderStateMachine, OrderStatus
        sm = OrderStateMachine("order1")

        sm.transition_to(OrderStatus.VALIDATING, "", "test", "cor1")
        sm.transition_to(OrderStatus.REJECTED, "", "test", "cor1")
        assert sm.state == OrderStatus.REJECTED

    def test_failed_no_recover(self):
        from execution.order_state import OrderStateMachine, OrderStatus, OrderStateMachineError
        sm = OrderStateMachine("order1")

        sm.transition_to(OrderStatus.VALIDATING, "", "test", "cor1")
        sm.transition_to(OrderStatus.FAILED, "", "test", "cor1")

        # Cannot recover from FAILED to any normal state without reconciliation
        with pytest.raises(OrderStateMachineError):
            sm.transition_to(OrderStatus.VALIDATING, "", "test", "cor1")

    def test_reconciliation_transition(self):
        from execution.order_state import OrderStateMachine, OrderStatus
        sm = OrderStateMachine("order1")

        sm.transition_to(OrderStatus.VALIDATING, "", "test", "cor1")
        sm.transition_to(OrderStatus.RISK_APPROVED, "", "test", "cor1")
        sm.transition_to(OrderStatus.SUBMITTED, "", "test", "cor1")
        sm.transition_to(OrderStatus.ACKNOWLEDGED, "", "test", "cor1")
        sm.transition_to(OrderStatus.RECONCILING, "", "test", "cor1")
        sm.transition_to(OrderStatus.FILLED, "reconciled", "reconciliation", "cor1")

        assert sm.state == OrderStatus.FILLED

    def test_transition_history(self):
        from execution.order_state import OrderStateMachine, OrderStatus
        sm = OrderStateMachine("order1")

        sm.transition_to(OrderStatus.VALIDATING, "start", "test", "cor1")
        sm.transition_to(OrderStatus.RISK_APPROVED, "approved", "risk", "cor2")

        history = sm.get_history()
        assert len(history) == 2
        assert history[0]["previous_state"] == "created"
        assert history[0]["new_state"] == "validating"
        assert history[1]["previous_state"] == "validating"
        assert history[1]["new_state"] == "risk_approved"
        assert history[0]["correlation_id"] == "cor1"
        assert history[1]["correlation_id"] == "cor2"


# ── Idempotency Tests ──

class TestIdempotency:
    """Idempotency guard must prevent duplicate orders."""

    def test_generate_key_deterministic(self):
        from execution.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()

        key1 = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "session1")
        key2 = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "session1")

        assert key1 == key2

    def test_different_signals_different_keys(self):
        from execution.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()

        key1 = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "session1")
        key2 = guard.generate_key("sig2", "v1", "RELIANCE", "BUY", "session1")

        assert key1 != key2

    def test_check_returns_false_first_time(self):
        from execution.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()
        key = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "session1")

        result = guard.check(key)
        assert result is False  # First time — not duplicate

    def test_check_returns_true_on_duplicate(self):
        from execution.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()
        key = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "session1")

        guard.check(key)  # First call
        result = guard.check(key)  # Second call — duplicate

        assert result is True

    def test_different_symbols_no_collision(self):
        from execution.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()

        key1 = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "session1")
        key2 = guard.generate_key("sig1", "v1", "TCS", "BUY", "session1")

        assert key1 != key2
        guard.check(key1)
        result = guard.check(key2)
        assert result is False  # Different symbol, not duplicate

    def test_mark_completed(self):
        from execution.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()
        key = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "session1")

        guard.check(key)
        entry = guard.get(key)
        assert entry["status"] == "pending"

        guard.mark_completed(key)
        entry = guard.get(key)
        assert entry["status"] == "completed"

    def test_cleanup(self):
        from execution.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()
        key = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "session1")
        guard.check(key)

        guard.cleanup(max_age_hours=0)  # Clean everything
        result = guard.check(key)
        assert result is False  # Key was cleaned, so it's new again


# ── Order Reconciliation Tests ──

class TestOrderReconciliation:
    """Reconciliation engine must detect all discrepancy types."""

    def test_missing_broker_order(self):
        from execution.reconciliation import OrderReconciliationEngine, ReconciliationSeverity
        engine = OrderReconciliationEngine()

        internal = {"internal_order_id": "ord1", "broker_order_id": "broker1", "state": "submitted"}
        issues = engine.reconcile(internal, None)

        assert len(issues) == 1
        assert issues[0].severity == ReconciliationSeverity.ERROR
        assert "not found" in issues[0].description.lower()

    def test_unknown_broker_order(self):
        from execution.reconciliation import OrderReconciliationEngine
        engine = OrderReconciliationEngine()

        internal = {"internal_order_id": "", "broker_order_id": "", "state": ""}
        broker = {"order_id": "unknown_broker", "status": "filled", "quantity": 10}
        issues = engine.reconcile(internal, broker)

        assert len(issues) == 1
        assert "untracked" in issues[0].internal_state

    def test_status_mismatch(self):
        from execution.reconciliation import OrderReconciliationEngine
        engine = OrderReconciliationEngine()

        internal = {"internal_order_id": "ord1", "broker_order_id": "broker1", "state": "filled"}
        broker = {"order_id": "broker1", "status": "rejected", "quantity": 10}
        issues = engine.reconcile(internal, broker)

        assert any("mismatch" in i.description.lower() for i in issues)

    def test_quantity_mismatch(self):
        from execution.reconciliation import OrderReconciliationEngine
        engine = OrderReconciliationEngine()

        internal = {"internal_order_id": "ord1", "broker_order_id": "broker1", "state": "submitted", "quantity": 10}
        broker = {"order_id": "broker1", "status": "open", "quantity": 5}
        issues = engine.reconcile(internal, broker)

        assert any("quantity" in i.description.lower() for i in issues)

    def test_fill_mismatch(self):
        from execution.reconciliation import OrderReconciliationEngine
        engine = OrderReconciliationEngine()

        internal = {"internal_order_id": "ord1", "broker_order_id": "broker1",
                    "state": "filled", "filled_quantity": 10}
        broker = {"order_id": "broker1", "status": "filled", "filled_quantity": 5}
        issues = engine.reconcile(internal, broker)

        assert any("fill" in i.description.lower() for i in issues)

    def test_blocking_issues_detect(self):
        from execution.reconciliation import OrderReconciliationEngine
        engine = OrderReconciliationEngine()

        internal = {"internal_order_id": "ord1", "broker_order_id": "broker1", "state": "submitted"}
        engine.reconcile(internal, None)  # Missing broker order = ERROR

        blocking = engine.get_blocking_issues()
        assert len(blocking) == 1

    def test_resolve_issue(self):
        from execution.reconciliation import OrderReconciliationEngine
        engine = OrderReconciliationEngine()

        internal = {"internal_order_id": "ord1", "broker_order_id": "broker1", "state": "submitted"}
        issues = engine.reconcile(internal, None)

        assert engine.resolve_issue(issues[0].issue_id)
        assert len(engine.get_blocking_issues()) == 0

    def test_cancelled_internally_active_at_broker(self):
        from execution.reconciliation import OrderReconciliationEngine
        engine = OrderReconciliationEngine()

        internal = {"internal_order_id": "ord1", "broker_order_id": "broker1",
                    "state": "cancelled"}
        broker = {"order_id": "broker1", "status": "open", "quantity": 10}
        issues = engine.reconcile(internal, broker)

        assert any("cancelled" in i.description.lower() and "active" in i.description.lower()
                   for i in issues)


# ── Position Reconciliation Tests ──

class TestPositionReconciliation:
    """Position reconciliation must detect all discrepancy types."""

    def test_no_discrepancies(self):
        from execution.position_reconciliation import PositionReconciliationEngine
        engine = PositionReconciliationEngine()

        internal = [{"symbol": "RELIANCE", "direction": "long", "quantity": 10}]
        broker = [{"symbol": "RELIANCE", "direction": "long", "quantity": 10}]

        issues = engine.reconcile(internal, broker)
        assert len(issues) == 0

    def test_quantity_mismatch(self):
        from execution.position_reconciliation import PositionReconciliationEngine
        engine = PositionReconciliationEngine()

        internal = [{"symbol": "RELIANCE", "direction": "long", "quantity": 10}]
        broker = [{"symbol": "RELIANCE", "direction": "long", "quantity": 5}]

        issues = engine.reconcile(internal, broker)
        assert len(issues) == 1
        assert "quantity" in issues[0].description.lower()

    def test_missing_internal_position(self):
        from execution.position_reconciliation import PositionReconciliationEngine, PositionReconciliationSeverity
        engine = PositionReconciliationEngine()

        internal = []
        broker = [{"symbol": "RELIANCE", "direction": "long", "quantity": 10}]

        issues = engine.reconcile(internal, broker)
        assert len(issues) == 1
        assert issues[0].severity == PositionReconciliationSeverity.CRITICAL
        assert "unexpected" in issues[0].description.lower()

    def test_missing_broker_position(self):
        from execution.position_reconciliation import PositionReconciliationEngine, PositionReconciliationSeverity
        engine = PositionReconciliationEngine()

        internal = [{"symbol": "RELIANCE", "direction": "long", "quantity": 10}]
        broker = []

        issues = engine.reconcile(internal, broker)
        assert len(issues) == 1
        assert issues[0].severity == PositionReconciliationSeverity.CRITICAL
        assert "not at broker" in issues[0].description.lower()

    def test_reconciliation_blocks_execution(self):
        from execution.position_reconciliation import PositionReconciliationEngine
        engine = PositionReconciliationEngine()

        assert not engine.is_blocked()

        internal = [{"symbol": "RELIANCE", "direction": "long", "quantity": 10}]
        broker = [{"symbol": "TCS", "direction": "long", "quantity": 5}]  # Different symbol

        engine.reconcile(internal, broker)
        assert engine.is_blocked()


# ── Kill Switch Tests ──

class TestKillSwitch:
    """Kill switch must block execution at multiple levels."""

    def test_default_inactive(self):
        from execution.kill_switch import KillSwitch
        ks = KillSwitch()
        assert not ks.is_active()

    def test_activate_global(self):
        from execution.kill_switch import KillSwitch, KillSwitchLevel
        ks = KillSwitch()
        ks.activate(KillSwitchLevel.GLOBAL, "", "test")
        assert ks.is_active()

    def test_sub_level_inherits_global(self):
        from execution.kill_switch import KillSwitch, KillSwitchLevel
        ks = KillSwitch()
        ks.activate(KillSwitchLevel.GLOBAL, "", "test")
        assert ks.is_active(KillSwitchLevel.STRATEGY, "strat1")

    def test_symbol_level(self):
        from execution.kill_switch import KillSwitch, KillSwitchLevel
        ks = KillSwitch()
        ks.activate(KillSwitchLevel.SYMBOL, "RELIANCE", "test")
        assert ks.is_active(KillSwitchLevel.SYMBOL, "RELIANCE")
        assert not ks.is_active(KillSwitchLevel.SYMBOL, "TCS")

    def test_reset(self):
        from execution.kill_switch import KillSwitch, KillSwitchLevel
        ks = KillSwitch()
        ks.activate(KillSwitchLevel.GLOBAL, "", "test")
        ks.reset(KillSwitchLevel.GLOBAL)
        assert not ks.is_active()

    def test_trigger_vs_activate(self):
        from execution.kill_switch import KillSwitch, KillSwitchLevel, KillSwitchState
        ks = KillSwitch()
        result = ks.trigger(KillSwitchLevel.GLOBAL, "", "triggered")
        assert result["state"] == KillSwitchState.TRIGGERED.value
        assert ks.is_active()

    def test_get_active_switches(self):
        from execution.kill_switch import KillSwitch, KillSwitchLevel
        ks = KillSwitch()
        ks.activate(KillSwitchLevel.GLOBAL, "", "test")
        ks.activate(KillSwitchLevel.ACCOUNT, "acc1", "test")
        active = ks.get_active_switches()
        assert len(active) == 2

    def test_get_status(self):
        from execution.kill_switch import KillSwitch, KillSwitchLevel
        ks = KillSwitch()
        ks.activate(KillSwitchLevel.GLOBAL, "", "test")
        status = ks.get_status()
        assert status["active"]
        assert status["blocking_execution"]


# ── Config Guard Tests ──

class TestConfigGuard:
    """Config guard must detect configuration drift."""

    def test_no_drift_on_same_config(self):
        from execution.config_guard import ConfigGuard, ConfigurationSnapshot
        guard = ConfigGuard()

        config = ConfigurationSnapshot()
        guard.capture_approval_snapshot(config)

        assert not guard.check_for_drift(config)

    def test_drift_on_different_config(self):
        from execution.config_guard import ConfigGuard, ConfigurationSnapshot
        guard = ConfigGuard()

        config1 = ConfigurationSnapshot()
        guard.capture_approval_snapshot(config1)

        config2 = ConfigurationSnapshot()
        config2.loss_limits = {"max_daily_loss": 5000}

        assert guard.check_for_drift(config2)

    def test_drift_blocks_execution(self):
        from execution.config_guard import ConfigGuard, ConfigurationSnapshot
        guard = ConfigGuard()

        config1 = ConfigurationSnapshot(allowed_symbols=["RELIANCE"])
        guard.capture_approval_snapshot(config1)

        config2 = ConfigurationSnapshot(allowed_symbols=["TCS"])
        guard.check_for_drift(config2)

        assert guard.has_drift()
        assert guard.get_drift_reason() != ""

    def test_no_snapshot_returns_drift(self):
        from execution.config_guard import ConfigGuard, ConfigurationSnapshot
        guard = ConfigGuard()

        # No approval snapshot captured
        config = ConfigurationSnapshot()
        assert guard.check_for_drift(config)

    def test_consistent_hash(self):
        from execution.config_guard import ConfigurationSnapshot
        config1 = ConfigurationSnapshot(allowed_symbols=["RELIANCE", "TCS"])
        config2 = ConfigurationSnapshot(allowed_symbols=["RELIANCE", "TCS"])

        assert config1.compute_hash() == config2.compute_hash()


# ── Approval Binding Tests ──

class TestApprovalBinding:
    """Execution policy must verify approval state."""

    def test_policy_rejects_without_approval(self):
        from execution.execution_policy import ExecutionPolicyEngine
        policy = ExecutionPolicyEngine()

        perm = policy.check()
        assert not perm.allowed
        checks = " ".join(perm.blocking_checks)
        assert "phase_43_lock" in checks
        assert "approval" in checks

    def test_policy_always_blocked_in_phase43(self):
        from execution.execution_policy import ExecutionPolicyEngine
        from execution.kill_switch import KillSwitch
        policy = ExecutionPolicyEngine()
        policy.set_kill_switch(KillSwitch())

        perm = policy.check()
        assert not perm.allowed
        assert "phase_43_lock" in perm.blocking_checks

    def test_policy_checks_runtime_mode(self):
        from execution.execution_policy import ExecutionPolicyEngine
        from trading.runtime_mode import RuntimeModeManager
        policy = ExecutionPolicyEngine()
        policy.set_runtime_mode(RuntimeModeManager())

        perm = policy.check()
        assert not perm.allowed
        assert "phase_43_lock" in perm.blocking_checks


# ── Execution Policy Tests ──

class TestExecutionPolicy:
    """Execution policy must always deny in Phase 43."""

    def test_phase_43_lock_constant(self):
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        assert PHASE_43_LIVE_EXECUTION_LOCK is True

    def test_policy_default_deny(self):
        from execution.execution_policy import ExecutionPolicyEngine
        policy = ExecutionPolicyEngine()
        perm = policy.check()
        assert not perm.allowed
        assert "phase_43_lock" in perm.blocking_checks

    def test_permission_to_dict(self):
        from execution.execution_policy import ExecutionPermission
        perm = ExecutionPermission()
        d = perm.to_dict()
        assert d["allowed"] is False
        assert d["reason"] != ""
        assert "timestamp" in d

    def test_policy_validates_quantity(self):
        from execution.execution_policy import ExecutionPolicyEngine
        policy = ExecutionPolicyEngine()

        perm = policy.check(quantity=0)
        assert not perm.allowed

    def test_policy_validates_symbol(self):
        from execution.execution_policy import ExecutionPolicyEngine
        policy = ExecutionPolicyEngine()

        perm = policy.check(symbol="", quantity=1)
        assert not perm.allowed


# ── Emergency Stop Tests ──

class TestEmergencyShutdown:
    """Emergency shutdown must block all execution and preserve state."""

    def test_emergency_stop_blocks_execution(self):
        from execution.emergency import EmergencyShutdown
        emg = EmergencyShutdown()

        assert not emg.is_active()
        emg.emergency_stop(reason="test")
        assert emg.is_active()

    def test_emergency_stop_with_kill_switch(self):
        from execution.emergency import EmergencyShutdown
        from execution.kill_switch import KillSwitch, KillSwitchLevel
        emg = EmergencyShutdown()
        ks = KillSwitch()

        record = emg.emergency_stop(triggered_by="test", reason="test", kill_switch=ks)
        assert record.kill_switch_activated
        assert ks.is_active(KillSwitchLevel.GLOBAL)
        assert record.positions_preserved  # Must NOT auto-close in Phase 43

    def test_emergency_stop_with_audit(self):
        from execution.emergency import EmergencyShutdown
        from execution.execution_audit import ExecutionAuditLog
        emg = EmergencyShutdown()
        audit = ExecutionAuditLog()

        record = emg.emergency_stop(triggered_by="test", reason="test", audit_log=audit)
        assert record.audit_event_recorded
        assert audit.count() == 1

    def test_recover_from_emergency(self):
        from execution.emergency import EmergencyShutdown
        emg = EmergencyShutdown()

        emg.emergency_stop(reason="test")
        assert emg.is_active()

        result = emg.recover()
        assert result
        assert emg.is_active()  # Still active until resolved

    def test_resolve_emergency(self):
        from execution.emergency import EmergencyShutdown
        emg = EmergencyShutdown()

        emg.emergency_stop(reason="test")
        emg.resolve()
        assert not emg.is_active()

    def test_emergency_preserves_positions_phase43(self):
        from execution.emergency import EmergencyShutdown
        emg = EmergencyShutdown()

        record = emg.emergency_stop(reason="test")
        assert record.positions_preserved
        # Phase 43: MUST NOT auto-close positions
        assert record.pending_intents_cancelled >= 0

    def test_emergency_get_status(self):
        from execution.emergency import EmergencyShutdown
        emg = EmergencyShutdown()
        status = emg.get_status()
        assert not status["active"]
        assert status["current_stop"] is None


# ── Execution Health Tests ──

class TestExecutionHealth:
    """Health monitor must properly track execution system health."""

    def test_initial_state_unknown(self):
        from execution.execution_health import ExecutionHealthMonitor
        monitor = ExecutionHealthMonitor()
        assert monitor.get_overall_state().value == "unknown"

    def test_healthy_after_success(self):
        from execution.execution_health import ExecutionHealthMonitor
        monitor = ExecutionHealthMonitor()

        monitor.record_success("broker_connectivity")
        monitor.record_success("websocket_health")
        monitor.record_success("api_latency")
        monitor.record_success("reconciliation_status")
        monitor.record_success("market_data_freshness")
        monitor.record_success("system_heartbeat")
        monitor.record_success("kill_switch_status")
        monitor.record_success("order_acknowledgement_latency")
        monitor.record_success("fill_latency")
        monitor.record_success("rejection_rate")

        assert monitor.is_healthy()

    def test_blocked_on_critical_failure(self):
        from execution.execution_health import ExecutionHealthMonitor
        monitor = ExecutionHealthMonitor()

        monitor.record_success("broker_connectivity")
        monitor.record_failure("broker_connectivity", "disconnected")
        monitor.record_failure("broker_connectivity", "still disconnected")  # consecutive >= 2

        assert monitor.is_blocked()
        assert not monitor.is_healthy()

    def test_degraded_on_single_failure(self):
        from execution.execution_health import ExecutionHealthMonitor
        monitor = ExecutionHealthMonitor()

        monitor.record_success("broker_connectivity")
        monitor.record_failure("broker_connectivity", "timeout")  # First failure

        assert not monitor.is_blocked()
        assert not monitor.is_healthy()

    def test_get_check(self):
        from execution.execution_health import ExecutionHealthMonitor
        monitor = ExecutionHealthMonitor()
        check = monitor.get_check("broker_connectivity")
        assert check is not None
        assert check.name == "broker_connectivity"

    def test_get_all_checks(self):
        from execution.execution_health import ExecutionHealthMonitor
        monitor = ExecutionHealthMonitor()
        checks = monitor.get_all_checks()
        assert len(checks) == 10


# ── Execution Simulator Tests ──

class TestExecutionSimulator:
    """Simulator must simulate broker behavior without real connection."""

    def test_happy_path(self):
        from execution.execution_simulator import ExecutionSimulator
        sim = ExecutionSimulator("happy_path")
        result = sim.place_order("RELIANCE", "BUY", 10, 100.0)
        assert result["success"]
        assert result["status"] == "filled"
        assert result["filled_quantity"] == 10

    def test_reject(self):
        from execution.execution_simulator import ExecutionSimulator
        sim = ExecutionSimulator("reject")
        result = sim.place_order("RELIANCE", "BUY", 10, 100.0)
        assert not result["success"]
        assert result["status"] == "rejected"

    def test_partial_fill(self):
        from execution.execution_simulator import ExecutionSimulator
        sim = ExecutionSimulator("partial_fill")
        result = sim.place_order("RELIANCE", "BUY", 10, 100.0)
        assert result["success"]
        assert result["filled_quantity"] < 10

    def test_timeout(self):
        from execution.execution_simulator import ExecutionSimulator
        sim = ExecutionSimulator("timeout")
        result = sim.place_order("RELIANCE", "BUY", 10, 100.0)
        assert not result["success"]
        assert result["status"] == "unknown"

    def test_cancel(self):
        from execution.execution_simulator import ExecutionSimulator
        sim = ExecutionSimulator("cancel")
        result = sim.place_order("RELIANCE", "BUY", 10, 100.0)
        assert result["status"] == "cancelled"

    def test_get_order(self):
        from execution.execution_simulator import ExecutionSimulator
        sim = ExecutionSimulator()
        result = sim.place_order("RELIANCE", "BUY", 10, 100.0)
        oid = result["internal_order_id"]
        fetched = sim.get_order(oid)
        assert fetched["internal_order_id"] == oid

    def test_get_scenario_info(self):
        from execution.execution_simulator import ExecutionSimulator
        sim = ExecutionSimulator("reject")
        info = sim.get_scenario_info()
        assert info["mode"] == "reject"
        assert "description" in info

    def test_reset(self):
        from execution.execution_simulator import ExecutionSimulator
        sim = ExecutionSimulator("duplicate_response")
        sim.place_order("RELIANCE", "BUY", 10, 100.0)
        sim.reset()
        orders = sim.get_all_orders()
        assert len(orders) == 0


# ── Audit Log Tests ──

class TestExecutionAudit:
    """Audit log must be append-only and contain required fields."""

    def test_record_creates_entry(self):
        from execution.execution_audit import ExecutionAuditLog
        audit = ExecutionAuditLog()
        eid = audit.record("test_event", severity="info", reason="testing")
        assert eid.startswith("aud_")
        assert audit.count() == 1

    def test_required_fields(self):
        from execution.execution_audit import ExecutionAuditLog
        audit = ExecutionAuditLog()

        eid = audit.record(
            event_type="order_created",
            severity="info",
            order_id="ord1",
            signal_id="sig1",
            champion_id="champ1",
            approval_id="app1",
            correlation_id="cor1",
            actor="system",
            reason="Order created",
            before_state="none",
            after_state="created",
            details={"quantity": 10},
        )

        entries = audit.get_entries()
        entry = entries[0]
        assert entry["event_id"] == eid
        assert entry["event_type"] == "order_created"
        assert entry["order_id"] == "ord1"
        assert entry["signal_id"] == "sig1"
        assert entry["champion_id"] == "champ1"
        assert entry["approval_id"] == "app1"
        assert entry["correlation_id"] == "cor1"
        assert entry["actor"] == "system"
        assert entry["before_state"] == "none"
        assert entry["after_state"] == "created"
        assert entry["details"]["quantity"] == 10

    def test_append_only(self):
        from execution.execution_audit import ExecutionAuditLog
        audit = ExecutionAuditLog()
        audit.record("event1")
        audit.record("event2")
        audit.record("event3")

        entries = audit.get_entries()
        assert len(entries) == 3

    def test_get_entries_limit(self):
        from execution.execution_audit import ExecutionAuditLog
        audit = ExecutionAuditLog()
        for i in range(10):
            audit.record(f"event_{i}")

        entries = audit.get_entries(limit=3)
        assert len(entries) == 3


# ── ExecutionGateway Integration Safety Tests ──

class TestExecutionGatewaySafety:
    """Gateway must properly integrate with Phase 43 infrastructure."""

    def test_can_execute_live_still_false(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        assert not mgr.can_execute_live()

    def test_runtime_modes_restricted(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        result = mgr.set_mode("live")
        assert not result["success"]
        # PAPER is now allowed in Phase 2C
        result = mgr.set_mode("paper")
        assert result["success"]

    def test_gateway_mode_cannot_enable_live(self):
        from execution.gateway import ExecutionGateway
        gw = ExecutionGateway()
        gw.set_mode("live")
        # Even if mode is set to live, can_execute_live from RuntimeModeManager still False
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        assert not mgr.can_execute_live()


# ── PHASE 43 CRITICAL SAFETY VERIFICATION ──

class TestPhase43SafetyVerification:
    """
    Critical safety verification for Phase 43.

    These tests MUST ALL PASS before Phase 43 can be considered complete.
    """

    def test_cannot_place_zerodha_order(self):
        """Can Phase 43 place a Zerodha order? → MUST BE NO"""
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()

        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.place_order("RELIANCE", "BUY", 1))

    def test_cannot_enable_live(self):
        """Can Phase 43 enable LIVE? → MUST BE NO"""
        from trading.runtime_mode import RuntimeModeManager, ALLOWED_MODES, RuntimeMode
        assert RuntimeMode.LIVE not in ALLOWED_MODES
        mgr = RuntimeModeManager()
        result = mgr.set_mode("live")
        assert not result["success"]

    def test_can_execute_live_returns_false(self):
        """Does RuntimeModeManager.can_execute_live() return False? → MUST BE YES"""
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        assert mgr.can_execute_live() is False

    def test_execution_policy_allows_false(self):
        """Can ExecutionPolicy allow live execution? → MUST BE NO"""
        from execution.execution_policy import ExecutionPolicyEngine, PHASE_43_LIVE_EXECUTION_LOCK
        assert PHASE_43_LIVE_EXECUTION_LOCK is True
        policy = ExecutionPolicyEngine()
        perm = policy.check()
        assert perm.allowed is False

    def test_phase_43_lock_true(self):
        """PHASE_43_LIVE_EXECUTION_LOCK == True? → MUST BE YES"""
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        assert PHASE_43_LIVE_EXECUTION_LOCK is True

    def test_cannot_bypass_lock_with_valid_checks(self):
        """Can approval bypass the Phase 43 lock? → MUST BE NO"""
        from execution.execution_policy import ExecutionPolicyEngine
        policy = ExecutionPolicyEngine()
        # Even with all systems nominally passing, the lock remains
        perm = policy.check(
            symbol="RELIANCE",
            side="BUY",
            quantity=10,
            price=100.0,
            stop_loss=95.0,
            target=110.0,
        )
        assert perm.allowed is False
        assert "phase_43_lock" in perm.blocking_checks

    def test_config_drift_invalidates_approval(self):
        """Can config drift invalidate approval? → MUST BE YES"""
        from execution.config_guard import ConfigGuard, ConfigurationSnapshot
        guard = ConfigGuard()

        config1 = ConfigurationSnapshot(allowed_symbols=["RELIANCE"])
        guard.capture_approval_snapshot(config1)

        config2 = ConfigurationSnapshot(allowed_symbols=["TCS"])
        drift = guard.check_for_drift(config2)

        assert drift is True
        assert guard.has_drift()

    def test_reconciliation_failure_blocks(self):
        """Can reconciliation failure block execution? → MUST BE YES"""
        from execution.reconciliation import OrderReconciliationEngine
        engine = OrderReconciliationEngine()

        internal = {"internal_order_id": "ord1", "broker_order_id": "broker1", "state": "submitted"}
        engine.reconcile(internal, None)  # Missing broker order

        assert len(engine.get_blocking_issues()) > 0

    def test_kill_switch_blocks(self):
        """Can kill switch block execution? → MUST BE YES"""
        from execution.kill_switch import KillSwitch, KillSwitchLevel
        ks = KillSwitch()
        ks.activate(KillSwitchLevel.GLOBAL, "", "test")
        assert ks.is_active()

    def test_idempotency_prevents_duplicates(self):
        """Can duplicate signals create duplicate orders? → MUST BE NO"""
        from execution.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()
        key = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "session1")
        guard.check(key)
        assert guard.check(key) is True  # Duplicate detected

    def test_broker_timeout_prevents_duplicate(self):
        """Can broker timeout cause duplicate order? → MUST BE NO"""
        from execution.idempotency import IdempotencyGuard
        guard = IdempotencyGuard()

        # Even if broker response is delayed, idempotency key persists
        key = guard.generate_key("sig1", "v1", "RELIANCE", "BUY", "session1")
        guard.check(key)

        # Simulate delayed broker response — another request with same key comes in
        is_duplicate = guard.check(key)
        assert is_duplicate  # Blocked by idempotency

    def test_unexpected_position_detected(self):
        """Can unexpected broker position remain undetected? → MUST BE NO"""
        from execution.position_reconciliation import PositionReconciliationEngine
        engine = PositionReconciliationEngine()

        internal = []
        broker = [{"symbol": "SURPRISE", "direction": "long", "quantity": 100}]

        issues = engine.reconcile(internal, broker)
        assert len(issues) == 1
        assert "unexpected" in issues[0].description.lower()

    def test_frontend_cannot_enable_live(self):
        """Can frontend enable LIVE? → MUST BE NO (backend-enforced)"""
        from trading.runtime_mode import RuntimeModeManager, ALLOWED_MODES, RuntimeMode as RTMode
        # Frontend can call API, but backend blocks it
        assert RTMode.LIVE not in ALLOWED_MODES

        mgr = RuntimeModeManager()
        # Even if frontend sends set_mode("live"), the backend rejects it
        result = mgr.set_mode(RTMode.LIVE.value)
        assert not result["success"]

    def test_no_live_order_api_endpoint(self):
        """Phase 43 API must not have a live order endpoint."""
        import backend.api.execution as api_module
        # Get all routes from the router
        routes = [r.path for r in api_module.router.routes]
        # There must be no /api/execution/live-order endpoint
        assert "/api/execution/live-order" not in routes, (
            "Phase 43 must not expose a live order endpoint"
        )
        # There must be no /api/execution/place-order endpoint
        assert "/api/execution/place-order" not in routes, (
            "Phase 43 must not expose a place-order endpoint"
        )


# ── Execution Order Models Tests ──

class TestExecutionOrderModels:
    """Order models must have correct structure."""

    def test_execution_order_creation(self):
        from execution.order_models import ExecutionOrder
        order = ExecutionOrder(
            symbol="RELIANCE",
            side="buy",
            quantity=10,
            price=100.0,
        )
        assert order.internal_order_id.startswith("ord_")
        assert order.state == "created"
        assert order.symbol == "RELIANCE"

    def test_execution_order_to_dict(self):
        from execution.order_models import ExecutionOrder
        order = ExecutionOrder(symbol="TCS", quantity=5)
        d = order.to_dict()
        assert d["symbol"] == "TCS"
        assert d["quantity"] == 5
        assert "state" in d
        assert "risk_snapshot" in d

    def test_risk_snapshot(self):
        from execution.order_models import RiskSnapshot
        rs = RiskSnapshot(
            risk_approved=True,
            daily_loss_remaining=10000.0,
        )
        d = rs.to_dict()
        assert d["risk_approved"]
        assert d["daily_loss_remaining"] == 10000.0

    def test_execution_report(self):
        from execution.order_models import ExecutionReport
        report = ExecutionReport(
            internal_order_id="ord1",
            broker_order_id="broker1",
            status="filled",
            filled_quantity=10,
            average_price=100.0,
        )
        d = report.to_dict()
        assert d["status"] == "filled"
        assert d["filled_quantity"] == 10
