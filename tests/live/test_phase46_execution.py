"""
Phase 46 — Controlled Live Execution Integration & Canary Trading Tests.

Tests the complete execution pipeline from preflight through canary trading.
Critical: LIVE execution MUST remain disabled.
PHASE_43_LIVE_EXECUTION_LOCK must remain TRUE.
"""

from __future__ import annotations

import pytest
import asyncio
from datetime import datetime, timezone


# ═══════════════════════════════════════════════
# Broker Session Tests
# ═══════════════════════════════════════════════

class TestBrokerSession:
    """Broker session validation."""

    def test_session_status_defaults(self):
        from live.broker_session import BrokerSessionStatus
        status = BrokerSessionStatus()
        assert not status.authenticated
        assert not status.session_valid
        assert not status.all_valid

    def test_session_validate_without_broker(self):
        from live.broker_session import BrokerSessionManager
        import asyncio
        mgr = BrokerSessionManager()
        status = asyncio.run(mgr.validate_session())
        assert not status.all_valid
        assert "not configured" in status.error

    def test_session_status_sanitized(self):
        from live.broker_session import _sanitize
        data = {"access_token": "secret123", "api_secret": "very_secret", "ok": "visible"}
        result = _sanitize(data)
        assert result["access_token"] == "***"
        assert result["api_secret"] == "***"
        assert result["ok"] == "visible"

    def test_session_to_dict(self):
        from live.broker_session import BrokerSessionStatus
        status = BrokerSessionStatus(authenticated=True, session_valid=True)
        d = status.to_dict()
        assert d["authenticated"] is True
        assert d["all_valid"] is False  # account_valid and segments_valid still False


# ═══════════════════════════════════════════════
# Preflight Validator Tests
# ═══════════════════════════════════════════════

class TestPreflightValidator:
    """Preflight validation checks."""

    def test_preflight_fails_without_deps(self):
        from live.preflight import PreflightValidator
        validator = PreflightValidator()
        result = validator.validate(symbol="RELIANCE", side="BUY", quantity=10, price=2500.0)
        assert not result.passed
        assert len(result.blockers) > 0

    def test_preflight_requires_sl(self):
        from live.preflight import PreflightValidator
        validator = PreflightValidator()
        result = validator.validate(symbol="RELIANCE", side="BUY", quantity=10,
                                     price=2500.0, stop_loss=None, target=2600.0)
        assert not result.passed
        assert any("stop_loss" in b for b in result.blockers)

    def test_preflight_requires_target(self):
        from live.preflight import PreflightValidator
        validator = PreflightValidator()
        result = validator.validate(symbol="RELIANCE", side="BUY", quantity=10,
                                     price=2500.0, stop_loss=2450.0, target=None)
        assert not result.passed
        assert any("target" in b for b in result.blockers)

    def test_preflight_checks_rr(self):
        from live.preflight import PreflightValidator
        validator = PreflightValidator()
        # Bad R:R (1:2 risk:reward = 0.5)
        result = validator.validate(symbol="RELIANCE", side="BUY", quantity=10,
                                     price=2500.0, stop_loss=2400.0, target=2550.0)
        assert not result.passed
        assert any("risk_reward" in b for b in result.blockers)

    def test_preflight_result_structure(self):
        from live.preflight import PreflightResult
        r = PreflightResult(passed=True, blockers=[], checks={"check1": {"passed": True}})
        d = r.to_dict()
        assert d["passed"] is True
        assert "check1" in d["checks"]

    def test_valid_preflight_rr_passes_check(self):
        from live.preflight import PreflightValidator
        validator = PreflightValidator()
        # Good R:R (1:2 = 2.0)
        result = validator.validate(symbol="RELIANCE", side="BUY", quantity=1,
                                     price=100.0, stop_loss=99.0, target=102.0)
        # Should fail on other checks (no activation, etc.) but RR check alone would pass
        rr_check = result.checks.get("risk_reward_valid", {})
        assert rr_check.get("passed") is True
        assert "risk_reward" not in " ".join(result.blockers[:5])


# ═══════════════════════════════════════════════
# Dry-Run Executor Tests
# ═══════════════════════════════════════════════

class TestDryRunExecutor:
    """Dry-run execution must not send to broker."""

    def test_dry_run_without_deps(self):
        from live.dry_run_executor import DryRunExecutor
        executor = DryRunExecutor()
        result = executor.execute(symbol="RELIANCE", side="BUY", quantity=10, price=2500.0)
        assert not result.passed
        assert len(result.blockers) > 0

    def test_dry_run_creates_order_payload(self):
        from live.dry_run_executor import DryRunExecutor
        executor = DryRunExecutor()
        result = executor.execute(symbol="RELIANCE", side="BUY", quantity=10, price=2500.0)
        assert "symbol" in result.order_payload
        assert result.order_payload["symbol"] == "RELIANCE"
        assert result.order_payload["exchange"] == "NSE"

    def test_dry_run_id_generated(self):
        from live.dry_run_executor import DryRunExecutor
        executor = DryRunExecutor()
        result = executor.execute(symbol="TEST", side="SELL", quantity=1, price=100.0)
        assert result.dry_run_id.startswith("dry_")

    def test_dry_run_result_structure(self):
        from live.dry_run_executor import DryRunResult
        r = DryRunResult(passed=True)
        d = r.to_dict()
        assert d["passed"] is True
        assert "order_payload" in d


# ═══════════════════════════════════════════════
# Execution Limits Tests
# ═══════════════════════════════════════════════

class TestExecutionLimits:
    """Hard limit enforcement."""

    def test_limits_pass_for_small_order(self):
        from live.execution_limits import ExecutionRiskLimiter
        limiter = ExecutionRiskLimiter()
        result = limiter.check(
            symbol="RELIANCE", side="BUY", quantity=1,
            price=2500.0, stop_loss=2450.0, target=2600.0,
        )
        assert result.passed

    def test_max_quantity_limit(self):
        from live.execution_limits import ExecutionRiskLimiter
        limiter = ExecutionRiskLimiter()
        result = limiter.check(
            symbol="RELIANCE", side="BUY", quantity=999,
            price=2500.0, stop_loss=2450.0, target=2600.0,
        )
        assert not result.passed
        assert any("max_order_quantity" in b for b in result.blockers)

    def test_max_notional_limit(self):
        from live.execution_limits import ExecutionRiskLimiter
        limiter = ExecutionRiskLimiter()
        result = limiter.check(
            symbol="RELIANCE", side="BUY", quantity=100,
            price=999999, stop_loss=990000, target=1000000,
        )
        assert not result.passed
        assert any("max_order_notional" in b for b in result.blockers)

    def test_max_open_positions(self):
        from live.execution_limits import ExecutionRiskLimiter
        limiter = ExecutionRiskLimiter()
        limiter.update_state(open_positions=[{"symbol": "POS1"}])
        result = limiter.check(
            symbol="RELIANCE", side="BUY", quantity=1,
            price=2500.0, stop_loss=2450.0, target=2600.0,
        )
        assert not result.passed
        assert any("max_open_positions" in b for b in result.blockers)

    def test_max_daily_trades(self):
        from live.execution_limits import ExecutionRiskLimiter
        limiter = ExecutionRiskLimiter()
        limiter.update_state(daily_trade_count=5)
        result = limiter.check(
            symbol="RELIANCE", side="BUY", quantity=1,
            price=2500.0, stop_loss=2450.0, target=2600.0,
        )
        assert not result.passed
        assert any("max_daily_trades" in b for b in result.blockers)

    def test_max_consecutive_losses(self):
        from live.execution_limits import ExecutionRiskLimiter
        limiter = ExecutionRiskLimiter()
        limiter.update_state(consecutive_losses=3)
        result = limiter.check(
            symbol="RELIANCE", side="BUY", quantity=1,
            price=2500.0, stop_loss=2450.0, target=2600.0,
        )
        assert not result.passed
        assert any("max_consecutive_losses" in b for b in result.blockers)

    def test_record_trade_updates_counters(self):
        from live.execution_limits import ExecutionRiskLimiter
        limiter = ExecutionRiskLimiter()
        limiter.record_trade_executed(pnl=50.0)
        limiter.record_trade_executed(pnl=-30.0)
        limiter.record_trade_executed(pnl=-20.0)
        status = limiter.get_status()
        assert status["current_state"]["daily_trade_count"] == 3
        assert status["current_state"]["daily_loss"] == 0.0
        assert status["current_state"]["consecutive_losses"] == 2

    def test_limit_check_result_structure(self):
        from live.execution_limits import LimitCheckResult
        r = LimitCheckResult(passed=True)
        d = r.to_dict()
        assert d["passed"] is True

    def test_limits_config_defaults(self):
        from live.execution_limits import LimitsConfig
        config = LimitsConfig()
        assert config.max_order_quantity == 100
        assert config.max_order_notional == 500000


# ═══════════════════════════════════════════════
# Order State Machine Tests
# ═══════════════════════════════════════════════

class TestOrderStateMachine:
    """Order state machine for live execution."""

    def test_initial_state(self):
        from live.order_state import LiveOrderStateMachine
        sm = LiveOrderStateMachine("order_1")
        assert sm.state == "created"
        assert not sm.is_preflight_passed()

    def test_preflight_passed_marking(self):
        from live.order_state import LiveOrderStateMachine
        sm = LiveOrderStateMachine("order_1")
        sm.mark_preflight_passed()
        assert sm.is_preflight_passed()
        assert sm.get_history() is not None

    def test_state_transition(self):
        from live.order_state import LiveOrderStateMachine
        from execution.order_state import OrderStatus
        sm = LiveOrderStateMachine("order_1")
        result = sm.transition_to(OrderStatus.VALIDATING, reason="Starting validation")
        assert result is True
        assert sm.state == "validating"


# ═══════════════════════════════════════════════
# Idempotency Manager Tests
# ═══════════════════════════════════════════════

class TestIdempotency:
    """Duplicate order prevention."""

    def test_generate_key(self):
        from live.idempotency import ExecutionIdempotencyManager
        mgr = ExecutionIdempotencyManager()
        key = mgr.generate_key(signal_id="sig1", strategy_version="v1",
                                symbol="RELIANCE", side="BUY")
        assert len(key) == 16
        assert isinstance(key, str)

    def test_deterministic_key(self):
        from live.idempotency import ExecutionIdempotencyManager
        mgr = ExecutionIdempotencyManager()
        key1 = mgr.generate_key(signal_id="sig1", strategy_version="v1",
                                 symbol="RELIANCE", side="BUY", session="s1")
        key2 = mgr.generate_key(signal_id="sig1", strategy_version="v1",
                                 symbol="RELIANCE", side="BUY", session="s1")
        assert key1 == key2

    def test_different_signal_different_key(self):
        from live.idempotency import ExecutionIdempotencyManager
        mgr = ExecutionIdempotencyManager()
        key1 = mgr.generate_key(signal_id="sig1", symbol="A", side="BUY")
        key2 = mgr.generate_key(signal_id="sig2", symbol="B", side="SELL")
        assert key1 != key2

    def test_duplicate_detected(self):
        from live.idempotency import ExecutionIdempotencyManager
        mgr = ExecutionIdempotencyManager()
        key = mgr.generate_key(signal_id="sig1", strategy_version="v1",
                                symbol="R", side="BUY", session="s1")
        first = mgr.check(key)
        assert first is False  # New
        second = mgr.check(key)
        assert second is True  # Duplicate

    def test_mark_submitted(self):
        from live.idempotency import ExecutionIdempotencyManager
        mgr = ExecutionIdempotencyManager()
        key = mgr.generate_key(signal_id="sig1", symbol="R", side="BUY")
        mgr.check(key)
        mgr.mark_submitted(key, broker_order_id="ZD123")
        record = mgr.get(key)
        assert record["status"] == "submitted"
        assert record["broker_order_id"] == "ZD123"


# ═══════════════════════════════════════════════
# Order Reconciliation Tests
# ═══════════════════════════════════════════════

class TestOrderReconciliation:
    """Order reconciliation after submission."""

    def test_matching_orders(self):
        from live.order_reconciliation import LiveOrderReconciliation
        recon = LiveOrderReconciliation()
        internal = {"internal_order_id": "ord1", "broker_order_id": "b1",
                     "symbol": "R", "side": "BUY", "quantity": 10, "status": "filled"}
        broker = {"order_id": "b1", "symbol": "R", "transaction_type": "BUY",
                   "quantity": 10, "status": "filled"}
        result = recon.reconcile(internal, broker)
        assert result.matched

    def test_mismatched_quantity(self):
        from live.order_reconciliation import LiveOrderReconciliation
        recon = LiveOrderReconciliation()
        internal = {"internal_order_id": "ord1", "symbol": "R", "side": "BUY",
                     "quantity": 10, "status": "filled"}
        broker = {"order_id": "b1", "symbol": "R", "transaction_type": "BUY",
                   "quantity": 5, "status": "complete"}
        result = recon.reconcile(internal, broker)
        assert not result.matched
        assert len(result.mismatches) > 0

    def test_broker_order_not_found(self):
        from live.order_reconciliation import LiveOrderReconciliation
        recon = LiveOrderReconciliation()
        internal = {"internal_order_id": "ord1", "status": "submitted"}
        result = recon.reconcile(internal, None)
        assert not result.matched
        assert result.blocking
        assert recon.is_blocked()

    def test_reconciliation_not_blocked_by_default(self):
        from live.order_reconciliation import LiveOrderReconciliation
        recon = LiveOrderReconciliation()
        assert not recon.is_blocked()


# ═══════════════════════════════════════════════
# Position Reconciliation Tests
# ═══════════════════════════════════════════════

class TestPositionReconciliation:
    """Position reconciliation after execution."""

    def test_matching_positions(self):
        from live.position_reconciliation import LivePositionReconciliation
        recon = LivePositionReconciliation()
        internal = [{"symbol": "R", "quantity": 10}]
        broker = [{"symbol": "R", "quantity": 10}]
        results = recon.reconcile(internal, broker)
        assert all(r.matched for r in results)

    def test_unexpected_position_detected(self):
        from live.position_reconciliation import LivePositionReconciliation
        recon = LivePositionReconciliation()
        internal = []
        broker = [{"symbol": "UNEXPECTED", "quantity": 100}]
        results = recon.reconcile(internal, broker)
        assert any(not r.matched for r in results)
        assert recon.is_blocked()

    def test_quantity_mismatch_detected(self):
        from live.position_reconciliation import LivePositionReconciliation
        recon = LivePositionReconciliation()
        internal = [{"symbol": "R", "quantity": 10}]
        broker = [{"symbol": "R", "quantity": 5}]
        results = recon.reconcile(internal, broker)
        assert any(not r.matched for r in results)
        assert recon.is_blocked()

    def test_not_blocked_by_default(self):
        from live.position_reconciliation import LivePositionReconciliation
        recon = LivePositionReconciliation()
        assert not recon.is_blocked()


# ═══════════════════════════════════════════════
# Emergency Cancel Tests
# ═══════════════════════════════════════════════

class TestEmergencyCancel:
    """Emergency cancellation."""

    def test_emergency_not_active_by_default(self):
        from live.emergency_cancel import EmergencyCancelManager
        mgr = EmergencyCancelManager()
        assert not mgr.is_emergency_active()

    def test_emergency_without_broker(self):
        from live.emergency_cancel import EmergencyCancelManager
        import asyncio
        mgr = EmergencyCancelManager()
        result = asyncio.run(mgr.cancel_all_open_orders(reason="test"))
        assert result.success
        assert result.blocked_new_entries
        assert mgr.is_emergency_active()

    def test_reset_requires_reviewer(self):
        from live.emergency_cancel import EmergencyCancelManager
        mgr = EmergencyCancelManager()
        result = mgr.reset_emergency(reviewer="", reason="")
        assert not result["success"]

    def test_reset_with_reviewer(self):
        from live.emergency_cancel import EmergencyCancelManager
        mgr = EmergencyCancelManager()
        import asyncio
        asyncio.run(mgr.cancel_all_open_orders(reason="test"))
        assert mgr.is_emergency_active()
        result = mgr.reset_emergency(reviewer="admin", reason="Reviewed")
        assert result["success"]
        assert not mgr.is_emergency_active()


# ═══════════════════════════════════════════════
# Canary Execution Tests
# ═══════════════════════════════════════════════

class TestCanaryExecution:
    """Canary trading mode."""

    def test_canary_disarmed_by_default(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        assert not mgr.is_armed()

    def test_arm_requires_reviewer(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        result = mgr.arm(reviewer="", reason="")
        assert not result["success"]

    def test_arm_requires_reason(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        result = mgr.arm(reviewer="admin", reason="")
        assert not result["success"]

    def test_arm_success(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        result = mgr.arm(reviewer="admin", reason="Testing canary")
        assert result["success"]
        assert mgr.is_armed()

    def test_disarm(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        mgr.arm(reviewer="admin", reason="Testing")
        assert mgr.is_armed()
        mgr.disarm()
        assert not mgr.is_armed()

    def test_canary_blocks_when_disarmed(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        result = mgr.can_execute(symbol="RELIANCE", quantity=1, price=2500.0)
        assert not result.allowed
        assert any("not_armed" in b for b in result.blockers)

    def test_canary_quantity_limit(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        mgr.arm(reviewer="admin", reason="Testing")
        result = mgr.can_execute(symbol="RELIANCE", quantity=999, price=2500.0)
        assert not result.allowed
        assert any("max_canary_quantity" in b for b in result.blockers)

    def test_canary_notional_limit(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        mgr.arm(reviewer="admin", reason="Testing")
        result = mgr.can_execute(symbol="RELIANCE", quantity=1, price=9999999)
        assert not result.allowed
        assert any("max_canary_notional" in b for b in result.blockers)

    def test_canary_trade_count_limit(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        mgr.arm(reviewer="admin", reason="Testing")
        # Record 3 trades (max = 3)
        for _ in range(3):
            mgr.record_canary_trade(0)
        result = mgr.can_execute(symbol="RELIANCE", quantity=1, price=100.0)
        assert not result.allowed
        assert any("max_canary_trades" in b for b in result.blockers)

    def test_canary_daily_loss_limit(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        mgr.arm(reviewer="admin", reason="Testing")
        mgr.record_canary_trade(-600)  # Exceeds max_daily_loss of 500
        result = mgr.can_execute(symbol="RELIANCE", quantity=1, price=100.0)
        assert not result.allowed
        assert any("max_canary_daily_loss" in b for b in result.blockers)

    def test_canary_symbol_allowlist(self):
        from live.canary import CanaryExecutionManager, CanaryConfig
        mgr = CanaryExecutionManager()
        config = CanaryConfig(symbol_allowlist=["TCS"])
        mgr.update_config(config)
        mgr.arm(reviewer="admin", reason="Testing")
        result = mgr.can_execute(symbol="RELIANCE", quantity=1, price=100.0)
        assert not result.allowed
        assert any("symbol_not_in_allowlist" in b for b in result.blockers)

    def test_canary_trades_remaining(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        mgr.arm(reviewer="admin", reason="Testing")
        status = mgr.get_status()
        assert status["current_state"]["trades_remaining"] == 3

    def test_canary_result_structure(self):
        from live.canary import CanaryResult
        r = CanaryResult(allowed=True, trades_remaining=3, loss_remaining=500.0)
        d = r.to_dict()
        assert d["allowed"] is True
        assert d["trades_remaining"] == 3


# ═══════════════════════════════════════════════
# Execution Controller Tests
# ═══════════════════════════════════════════════

class TestExecutionController:
    """Phase46ExecutionController pipeline."""

    def test_controller_blocks_without_deps(self):
        from live.execution_controller import Phase46ExecutionController
        import asyncio
        controller = Phase46ExecutionController()
        result = asyncio.run(controller.execute(
            symbol="RELIANCE", side="BUY", quantity=10, price=2500.0,
        ))
        assert not result.success
        assert len(result.blockers) > 0

    def test_execution_id_generated(self):
        from live.execution_controller import Phase46ExecutionController
        import asyncio
        controller = Phase46ExecutionController()
        result = asyncio.run(controller.execute(
            symbol="TEST", side="BUY", quantity=1, price=100.0,
        ))
        assert result.execution_id.startswith("exec_")

    def test_execution_tracking(self):
        from live.execution_controller import Phase46ExecutionController
        import asyncio
        controller = Phase46ExecutionController()
        asyncio.run(controller.execute(symbol="A", side="BUY", quantity=1, price=100.0))
        asyncio.run(controller.execute(symbol="B", side="SELL", quantity=1, price=200.0))
        status = controller.get_status()
        assert status["total_executions"] == 2
        assert status["recent_results"]["total"] == 2

    def test_get_execution_by_id(self):
        from live.execution_controller import Phase46ExecutionController
        import asyncio
        controller = Phase46ExecutionController()
        result = asyncio.run(controller.execute(symbol="T", side="BUY", quantity=1, price=100.0))
        found = controller.get_execution(result.execution_id)
        assert found is not None
        assert found.execution_id == result.execution_id

    def test_execution_result_structure(self):
        from live.execution_controller import ExecutionResult
        r = ExecutionResult(success=True, execution_id="exec_123")
        d = r.to_dict()
        assert d["success"] is True
        assert d["execution_id"] == "exec_123"


# ═══════════════════════════════════════════════
# Phase 46 Safety Regression Tests
# ═══════════════════════════════════════════════

class TestPhase46SafetyVerification:
    """Critical safety verification for Phase 46."""

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

    def test_activation_gate_default_locked(self):
        from live.activation_gate import ControlledLiveActivationGate
        gate = ControlledLiveActivationGate()
        assert gate.get_state().value == "locked"

    def test_canary_disarmed_by_default(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        assert not mgr.is_armed()

    def test_no_unrestricted_live_endpoint(self):
        """Phase 46 must not have unrestricted live trading endpoints."""
        import backend.api.live_execution as api_module
        routes = [r.path for r in api_module.router.routes]
        forbidden = [
            "enable", "start-unrestricted", "activate-auto",
        ]
        for path in routes:
            for f in forbidden:
                assert f not in path, f"Route {path} contains '{f}'"

    def test_broker_session_sanitizes_secrets(self):
        from live.broker_session import _sanitize
        secrets = {"access_token": "secret", "api_secret": "key", "safe": "ok"}
        result = _sanitize(secrets)
        assert result["access_token"] == "***"
        assert result["api_secret"] == "***"
        assert result["safe"] == "ok"

    def test_all_previous_tests_importable(self):
        import tests.live.test_phase44_pre_live  # noqa
        import tests.live.test_phase45_live_activation  # noqa

    def test_no_order_placed_automatically(self):
        """Verify no execution controller auto-places orders."""
        from live.execution_controller import Phase46ExecutionController
        import asyncio
        controller = Phase46ExecutionController()
        result = asyncio.run(controller.execute(symbol="T", side="BUY", quantity=1, price=100.0))
        # Without proper activation, execution must always be blocked
        assert not result.success
        assert result.status == "blocked" or len(result.blockers) > 0
