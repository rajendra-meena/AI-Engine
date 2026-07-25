"""
Phase 47 — Controlled Canary Live Execution & Production Reconciliation Tests.

Tests the complete canary authorization workflow: request -> approve -> arm -> precheck -> execute.
Critical: PHASE_43_LIVE_EXECUTION_LOCK remains TRUE.
"""

from __future__ import annotations

import pytest
import time
from datetime import datetime, timezone, timedelta


# ═══════════════════════════════════════════════
# Canary Authorization Model Tests
# ═══════════════════════════════════════════════

class TestCanaryAuthorization:
    """Authorization model and state machine."""

    def test_default_state_requested(self):
        from live.canary_authorization import CanaryAuthorization
        auth = CanaryAuthorization()
        assert auth.state == "requested"
        assert auth.authorization_id.startswith("can_auth_")

    def test_valid_transitions(self):
        from live.canary_authorization import validate_transition, CanaryAuthState
        assert validate_transition(CanaryAuthState.REQUESTED, CanaryAuthState.APPROVED)
        assert validate_transition(CanaryAuthState.APPROVED, CanaryAuthState.ARMED)
        assert validate_transition(CanaryAuthState.ARMED, CanaryAuthState.EXECUTING)
        assert validate_transition(CanaryAuthState.EXECUTING, CanaryAuthState.COMPLETED)
        assert validate_transition(CanaryAuthState.EXECUTING, CanaryAuthState.FAILED)

    def test_invalid_transitions(self):
        from live.canary_authorization import validate_transition, CanaryAuthState
        assert not validate_transition(CanaryAuthState.REQUESTED, CanaryAuthState.EXECUTING)
        assert not validate_transition(CanaryAuthState.COMPLETED, CanaryAuthState.ARMED)
        assert not validate_transition(CanaryAuthState.FAILED, CanaryAuthState.COMPLETED)

    def test_to_dict(self):
        from live.canary_authorization import CanaryAuthorization
        auth = CanaryAuthorization(approved_symbol="RELIANCE", approved_direction="BUY",
                                    approved_quantity=1, reviewer="admin", reason="Test")
        d = auth.to_dict()
        assert d["state"] == "requested"
        assert d["approved_symbol"] == "RELIANCE"
        assert d["approved_direction"] == "BUY"
        assert d["reviewer"] == "admin"

    def test_summary(self):
        from live.canary_authorization import CanaryAuthorization
        auth = CanaryAuthorization(approved_symbol="TCS")
        s = auth.summary()
        assert "authorization_id" in s
        assert s["approved_symbol"] == "TCS"

    def test_persistence_path(self):
        from live.canary_authorization import _get_store_path
        path = _get_store_path()
        assert path.endswith("canary_store.json")
        assert "data_cache" in path

    def test_save_load_cycle(self):
        from live.canary_authorization import _save_authorizations, _load_authorizations
        data = {"test_auth": {"authorization_id": "test_auth", "state": "requested"}}
        _save_authorizations(data)
        loaded = _load_authorizations()
        assert loaded["test_auth"]["state"] == "requested"
        # Cleanup
        import os
        os.remove(__import__('live.canary_authorization').canary_authorization.CANARY_STORE_PATH)


# ═══════════════════════════════════════════════
# Canary Precheck Tests
# ═══════════════════════════════════════════════

class TestCanaryPreCheck:
    """Final precheck before canary execution."""

    def test_precheck_fails_without_deps(self):
        from live.canary_precheck import CanaryPreCheck
        precheck = CanaryPreCheck()
        result = precheck.check(
            symbol="RELIANCE", side="BUY", quantity=1, price=2500.0,
            stop_loss=2450.0, target=2600.0,
        )
        assert not result.passed
        assert len(result.blockers) > 0

    def test_precheck_checks_structure(self):
        from live.canary_precheck import CanaryPreCheckResult
        result = CanaryPreCheckResult(passed=True)
        d = result.to_dict()
        assert d["passed"] is True
        assert "checks" in d


# ═══════════════════════════════════════════════
# Canary Lifecycle Tests
# ═══════════════════════════════════════════════

class TestCanaryLifecycle:
    """Full canary workflow."""

    def test_request_requires_reviewer(self):
        from live.canary_lifecycle import CanaryLifecycleManager, CanaryLifecycleError
        mgr = CanaryLifecycleManager()
        with pytest.raises(CanaryLifecycleError, match="Reviewer identity is required"):
            mgr.request(reviewer="", reason="test", symbol="RELIANCE", quantity=1)

    def test_request_requires_symbol(self):
        from live.canary_lifecycle import CanaryLifecycleManager, CanaryLifecycleError
        mgr = CanaryLifecycleManager()
        with pytest.raises(CanaryLifecycleError, match="Symbol is required"):
            mgr.request(reviewer="admin", reason="test", symbol="", quantity=1)

    def test_request_creates_auth(self):
        from live.canary_lifecycle import CanaryLifecycleManager
        mgr = CanaryLifecycleManager()
        auth = mgr.request(
            reviewer="admin", reason="Test canary",
            symbol="RELIANCE", direction="BUY", quantity=1,
            price=2500.0, stop_loss=2450.0, target=2600.0,
            strategy_version="v1",
        )
        assert auth.state == "requested"
        assert auth.approved_symbol == "RELIANCE"
        assert auth.approved_direction == "BUY"
        assert auth.approved_quantity == 1

    def test_approve_transitions_state(self):
        from live.canary_lifecycle import CanaryLifecycleManager
        mgr = CanaryLifecycleManager()
        auth = mgr.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        auth = mgr.approve(auth.authorization_id, reviewer="approver")
        assert auth.state == "approved"
        assert auth.expires_at != ""

    def test_approve_requires_reviewer(self):
        from live.canary_lifecycle import CanaryLifecycleManager, CanaryLifecycleError
        mgr = CanaryLifecycleManager()
        auth = mgr.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        with pytest.raises(CanaryLifecycleError, match="Reviewer identity required"):
            mgr.approve(auth.authorization_id, reviewer="")

    def test_arm_transitions_state(self):
        from live.canary_lifecycle import CanaryLifecycleManager
        mgr = CanaryLifecycleManager()
        auth = mgr.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        auth = mgr.approve(auth.authorization_id, reviewer="approver")
        auth = mgr.arm(auth.authorization_id, reviewer="approver")
        assert auth.state == "armed"

    def test_arm_requires_reviewer(self):
        from live.canary_lifecycle import CanaryLifecycleManager, CanaryLifecycleError
        mgr = CanaryLifecycleManager()
        auth = mgr.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        auth = mgr.approve(auth.authorization_id, reviewer="approver")
        with pytest.raises(CanaryLifecycleError, match="Reviewer identity required"):
            mgr.arm(auth.authorization_id, reviewer="")

    def test_cancel_from_requested(self):
        from live.canary_lifecycle import CanaryLifecycleManager
        mgr = CanaryLifecycleManager()
        auth = mgr.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        auth = mgr.cancel(auth.authorization_id, reason="Changed mind")
        assert auth.state == "cancelled"

    def test_cancel_from_approved(self):
        from live.canary_lifecycle import CanaryLifecycleManager
        mgr = CanaryLifecycleManager()
        auth = mgr.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        auth = mgr.approve(auth.authorization_id, reviewer="approver")
        auth = mgr.cancel(auth.authorization_id)
        assert auth.state == "cancelled"

    def test_cannot_execute_without_arm(self):
        from live.canary_lifecycle import CanaryLifecycleManager, CanaryLifecycleError
        import asyncio
        mgr = CanaryLifecycleManager()
        auth = mgr.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        with pytest.raises(CanaryLifecycleError, match="Must be ARMED"):
            asyncio.run(mgr.execute(auth.authorization_id))

    def test_expiry_after_approval(self):
        from live.canary_lifecycle import CanaryLifecycleManager
        mgr = CanaryLifecycleManager()
        auth = mgr.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        auth = mgr.approve(auth.authorization_id, reviewer="approver")
        # Manually set expiry to the past
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        auth.expires_at = past
        # Check expiry
        mgr._check_expiry(auth)
        assert auth.state == "expired"

    def test_get_status(self):
        from live.canary_lifecycle import CanaryLifecycleManager
        mgr = CanaryLifecycleManager()
        status = mgr.get_status()
        assert "active_count" in status
        assert "total_count" in status

    def test_get_history(self):
        from live.canary_lifecycle import CanaryLifecycleManager
        mgr = CanaryLifecycleManager()
        mgr.request(reviewer="admin", reason="Test1", symbol="A", quantity=1)
        mgr.request(reviewer="admin", reason="Test2", symbol="B", quantity=1)
        history = mgr.get_history()
        assert len(history) >= 2

    def test_get_authorization(self):
        from live.canary_lifecycle import CanaryLifecycleManager
        mgr = CanaryLifecycleManager()
        auth = mgr.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        found = mgr.get_authorization(auth.authorization_id)
        assert found is not None
        assert found.authorization_id == auth.authorization_id

    def test_fail_transition(self):
        from live.canary_lifecycle import CanaryLifecycleManager
        mgr = CanaryLifecycleManager()
        auth = mgr.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        auth.state = "executing"
        auth = mgr.fail(auth.authorization_id, reason="Broker error")
        assert auth.state == "failed"
        assert "Broker error" in auth.failure_reason

    def test_approval_sets_expiry(self):
        from live.canary_lifecycle import CanaryLifecycleManager
        from live.canary_authorization import CANARY_MAX_DURATION_MINUTES
        mgr = CanaryLifecycleManager()
        auth = mgr.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        auth = mgr.approve(auth.authorization_id, reviewer="approver")
        assert auth.expires_at != ""
        expiry = datetime.fromisoformat(auth.expires_at)
        now = datetime.now(timezone.utc)
        # Should be roughly CANARY_MAX_DURATION_MINUTES in the future
        diff = (expiry - now).total_seconds() / 60
        assert 0 < diff <= CANARY_MAX_DURATION_MINUTES + 1

    def test_precheck_fails_without_lifecycle_deps(self):
        from live.canary_lifecycle import CanaryLifecycleManager, CanaryLifecycleError
        mgr = CanaryLifecycleManager()
        auth = mgr.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        auth = mgr.approve(auth.authorization_id, reviewer="approver")
        auth = mgr.arm(auth.authorization_id, reviewer="approver")
        with pytest.raises(CanaryLifecycleError, match="Precheck validator not configured"):
            mgr.precheck(auth.authorization_id)


# ═══════════════════════════════════════════════
# Safety & Regression Tests
# ═══════════════════════════════════════════════

class TestPhase47SafetyVerification:
    """Critical safety tests for Phase 47."""

    def test_phase_43_lock_still_true(self):
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        assert PHASE_43_LIVE_EXECUTION_LOCK is True

    def test_can_execute_live_still_false(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        assert mgr.can_execute_live() is False

    def test_canary_disarmed_by_default(self):
        from live.canary import CanaryExecutionManager
        mgr = CanaryExecutionManager()
        assert not mgr.is_armed()

    def test_zerodha_adapter_still_raises(self):
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.place_order("RELIANCE", "BUY", 1))

    def test_no_unrestricted_live_endpoint(self):
        """Phase 47 API must not have unrestricted endpoints."""
        import backend.api.canary as api_module
        routes = [r.path for r in api_module.router.routes]
        forbidden = ["enable", "unlimited", "auto-start", "start-trading"]
        for path in routes:
            for f in forbidden:
                assert f not in path, f"Route {path} contains '{f}'"

    def test_activation_gate_default_locked(self):
        from live.activation_gate import ControlledLiveActivationGate
        gate = ControlledLiveActivationGate()
        assert gate.get_state().value == "locked"

    def test_canary_max_trades_is_1(self):
        from live.canary_authorization import MAX_CANARY_TRADES
        assert MAX_CANARY_TRADES == 1

    def test_all_previous_tests_importable(self):
        import tests.live.test_phase44_pre_live  # noqa
        import tests.live.test_phase45_live_activation  # noqa
        import tests.live.test_phase46_execution  # noqa


# ═══════════════════════════════════════════════
# API Endpoint Tests
# ═══════════════════════════════════════════════

class TestCanaryAPI:
    """Canary API endpoint tests."""

    def test_endpoints_registered(self):
        from backend.api.canary import router
        paths = [r.path for r in router.routes]
        expected = [
            "/api/live/canary/status",
            "/api/live/canary/request",
            "/api/live/canary/history",
        ]
        for e in expected:
            assert e in paths, f"Missing expected endpoint: {e}"

    def test_set_lifecycle(self):
        from backend.api.canary import set_canary_lifecycle, _get_lifecycle
        from live.canary_lifecycle import CanaryLifecycleManager
        with pytest.raises(AssertionError):
            _get_lifecycle()
        mgr = CanaryLifecycleManager()
        set_canary_lifecycle(mgr)
        assert _get_lifecycle() is mgr
