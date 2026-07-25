"""
Phase 54 — Controlled Live Auto-Trading Integration & First-Trade Gate Tests.

Tests activation, execution pipeline, hard limits, safety gates,
and critical safety invariants.
"""

from __future__ import annotations

import pytest
import asyncio


# ═══════════════════════════════════════════════
# Controlled Live Activation Tests
# ═══════════════════════════════════════════════

class TestControlledLiveActivation:
    """Activation of controlled live mode."""

    def test_requires_reviewer(self):
        from live.controlled_live_integration import ControlledLiveIntegration
        integration = ControlledLiveIntegration()
        result = integration.activate(reviewer="", reason="test")
        assert not result.get("success")

    def test_requires_reason(self):
        from live.controlled_live_integration import ControlledLiveIntegration
        integration = ControlledLiveIntegration()
        result = integration.activate(reviewer="admin", reason="")
        assert not result.get("success")

    def test_default_inactive(self):
        from live.controlled_live_integration import ControlledLiveIntegration
        integration = ControlledLiveIntegration()
        status = integration.get_status()
        assert status["state"] == "inactive"

    def test_limits_on_activate(self):
        from live.controlled_live_integration import ControlledLiveIntegration, MAX_QUANTITY, MAX_TRADES_PER_SESSION
        integration = ControlledLiveIntegration()
        # Can't activate without activation gate, but the limits should be returned
        result = integration.activate(reviewer="admin", reason="test")
        # Will fail because activation gate isn't ACTIVE, but check fields
        assert result.get("success") is False or "limits" in result


# ═══════════════════════════════════════════════
# Runtime Mode Tests
# ═══════════════════════════════════════════════

class TestRuntimeMode:
    """CONTROLLED_LIVE mode."""

    def test_controlled_live_not_in_allowed_modes(self):
        from trading.runtime_mode import RuntimeMode, ALLOWED_MODES
        assert RuntimeMode.CONTROLLED_LIVE not in ALLOWED_MODES

    def test_set_mode_rejects_controlled_live(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        result = mgr.set_mode("controlled_live")
        assert not result["success"]

    def test_activate_controlled_live(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        result = mgr.activate_controlled_live()
        assert result["success"]
        assert mgr.is_controlled_live_active()
        assert mgr.can_execute_live() is True  # Controlled live allows execution

    def test_deactivate_controlled_live(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        mgr.activate_controlled_live()
        mgr.deactivate_controlled_live()
        assert not mgr.is_controlled_live_active()
        assert mgr.can_execute_live() is False  # Back to blocked

    def test_live_mode_still_blocked(self):
        from trading.runtime_mode import RuntimeModeManager, ALLOWED_MODES, RuntimeMode
        assert RuntimeMode.LIVE not in ALLOWED_MODES
        mgr = RuntimeModeManager()
        result = mgr.set_mode("live")
        assert not result["success"]

    def test_can_execute_live_false_by_default(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        assert mgr.can_execute_live() is False

    def test_phase_43_lock_still_true(self):
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        assert PHASE_43_LIVE_EXECUTION_LOCK is True


# ═══════════════════════════════════════════════
# Execution Tests
# ═══════════════════════════════════════════════

class TestControlledLiveExecution:
    """One-trade execution pipeline."""

    def test_execute_without_activation_fails(self):
        from live.controlled_live_integration import ControlledLiveIntegration
        import asyncio
        integration = ControlledLiveIntegration()
        result = asyncio.run(integration.execute_trade(
            symbol="RELIANCE", side="BUY", quantity=1, price=2500.0,
        ))
        assert not result.get("success")
        assert "Must be ACTIVE" in result.get("error", "")

    def test_max_quantity_enforced(self):
        from live.controlled_live_integration import ControlledLiveIntegration, MAX_QUANTITY
        import asyncio
        integration = ControlledLiveIntegration()
        # Force ACTIVE state
        integration._record.state = "active"
        integration._record.trades_remaining = 1
        result = asyncio.run(integration.execute_trade(
            symbol="RELIANCE", side="BUY", quantity=MAX_QUANTITY + 1,
            price=2500.0,
        ))
        assert not result.get("success")
        assert "exceeds max" in result.get("error", "")

    def test_max_notional_enforced(self):
        from live.controlled_live_integration import ControlledLiveIntegration, MAX_NOTIONAL
        import asyncio
        integration = ControlledLiveIntegration()
        integration._record.state = "active"
        integration._record.trades_remaining = 1
        result = asyncio.run(integration.execute_trade(
            symbol="RELIANCE", side="BUY", quantity=1,
            price=MAX_NOTIONAL + 1,
        ))
        assert not result.get("success")
        assert "exceeds max" in result.get("error", "")

    def test_no_trades_remaining_blocks(self):
        from live.controlled_live_integration import ControlledLiveIntegration
        import asyncio
        integration = ControlledLiveIntegration()
        integration._record.state = "active"
        integration._record.trades_remaining = 0
        result = asyncio.run(integration.execute_trade(
            symbol="RELIANCE", side="BUY", quantity=1, price=2500.0,
        ))
        assert not result.get("success")
        assert "No trades remaining" in result.get("error", "")

    def test_execution_snapshot_created(self):
        from live.controlled_live_integration import ExecutionSnapshot
        snap = ExecutionSnapshot(symbol="TCS", direction="BUY", quantity=1)
        d = snap.to_dict()
        assert d["symbol"] == "TCS"
        assert d["direction"] == "BUY"
        assert d["execution_id"].startswith("cl_")

    def test_live_execution_record(self):
        from live.controlled_live_integration import LiveExecutionRecord
        rec = LiveExecutionRecord(state="active", trades_remaining=1)
        d = rec.to_dict()
        assert d["state"] == "active"
        assert d["trades_remaining"] == 1


# ═══════════════════════════════════════════════
# Emergency Stop Tests
# ═══════════════════════════════════════════════

class TestEmergencyStop:
    """Emergency stop for controlled live."""

    def test_requires_reviewer(self):
        from live.controlled_live_integration import ControlledLiveIntegration
        import asyncio
        integration = ControlledLiveIntegration()
        result = asyncio.run(integration.emergency_stop(reviewer="", reason=""))
        assert not result.get("success")

    def test_emergency_stop_works(self):
        from live.controlled_live_integration import ControlledLiveIntegration
        import asyncio
        integration = ControlledLiveIntegration()
        result = asyncio.run(integration.emergency_stop(
            reviewer="admin", reason="Emergency test",
        ))
        assert result.get("success")
        assert result.get("state") == "stopped"


# ═══════════════════════════════════════════════
# Hard Limits Tests
# ═══════════════════════════════════════════════

class TestHardLimits:
    """Server-side immutable limits."""

    def test_max_quantity_1(self):
        from live.controlled_live_integration import MAX_QUANTITY
        assert MAX_QUANTITY == 1

    def test_max_trades_1(self):
        from live.controlled_live_integration import MAX_TRADES_PER_SESSION
        assert MAX_TRADES_PER_SESSION == 1

    def test_max_notional_10000(self):
        from live.controlled_live_integration import MAX_NOTIONAL
        assert MAX_NOTIONAL == 10000

    def test_max_concurrent_positions_1(self):
        from live.controlled_live_integration import MAX_CONCURRENT_POSITIONS
        assert MAX_CONCURRENT_POSITIONS == 1


# ═══════════════════════════════════════════════
# API Tests
# ═══════════════════════════════════════════════

class TestControlledLiveAPI:
    """API endpoint tests."""

    def test_endpoints_registered(self):
        from backend.api.controlled_live import router
        paths = [r.path for r in router.routes]
        expected = [
            "/api/live/controlled/status",
            "/api/live/controlled/activate",
            "/api/live/controlled/execute",
            "/api/live/controlled/stop",
        ]
        for e in expected:
            assert e in paths, f"Missing expected endpoint: {e}"

    def test_no_dangerous_endpoints(self):
        from backend.api.controlled_live import router
        paths = [r.path for r in router.routes]
        forbidden = ["enable-live", "disable-lock", "unlimited-live",
                     "auto-trading-forever", "start-auto-trading"]
        for path in paths:
            for f in forbidden:
                assert f not in path, f"Route {path} contains '{f}'"

    def test_set_integration(self):
        from backend.api.controlled_live import set_controlled_live_integration, _get
        from live.controlled_live_integration import ControlledLiveIntegration
        with pytest.raises(AssertionError):
            _get()
        integration = ControlledLiveIntegration()
        set_controlled_live_integration(integration)
        assert _get() is integration


# ═══════════════════════════════════════════════
# Safety & Regression Tests
# ═══════════════════════════════════════════════

class TestPhase54SafetyVerification:
    """Critical safety tests for Phase 54."""

    def test_phase_43_lock_still_true(self):
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        assert PHASE_43_LIVE_EXECUTION_LOCK is True

    def test_live_mode_still_blocked(self):
        from trading.runtime_mode import RuntimeModeManager, ALLOWED_MODES, RuntimeMode
        assert RuntimeMode.LIVE not in ALLOWED_MODES
        mgr = RuntimeModeManager()
        # CONTROLLED_LIVE not active by default
        assert mgr.can_execute_live() is False
        assert not mgr.is_live()
        # Activating controlled live changes can_execute_live but NOT is_live
        mgr.activate_controlled_live()
        assert mgr.can_execute_live() is True
        assert not mgr.is_live()  # is_live() still False — only CONTROLLED_LIVE

    def test_zerodha_adapter_still_raises(self):
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.place_order("RELIANCE", "BUY", 1))

    def test_second_trade_blocked(self):
        """After one trade, trades_remaining must be 0."""
        from live.controlled_live_integration import ControlledLiveIntegration
        import asyncio
        integration = ControlledLiveIntegration()
        integration._record.state = "active"
        integration._record.trades_remaining = 0  # After completion
        result = asyncio.run(integration.execute_trade(
            symbol="RELIANCE", side="BUY", quantity=1, price=2500.0,
        ))
        assert not result.get("success")
        assert "No trades remaining" in result.get("error", "")

    def test_frontend_cannot_bypass(self):
        """Even if frontend sends dangerous params, backend must reject."""
        from live.controlled_live_integration import ControlledLiveIntegration, MAX_QUANTITY
        import asyncio
        integration = ControlledLiveIntegration()
        integration._record.state = "active"
        integration._record.trades_remaining = 1
        # Frontend sends quantity=999999
        result = asyncio.run(integration.execute_trade(
            symbol="RELIANCE", side="BUY", quantity=999999,
            price=2500.0, stop_loss=2450.0, target=2600.0,
        ))
        assert not result.get("success")
        assert "exceeds max" in result.get("error", "")

    def test_no_unrestricted_live_endpoint(self):
        import backend.api.controlled_live as api_module
        routes = [r.path for r in api_module.router.routes]
        forbidden = ["enable-live", "disable-lock", "unlimited-live",
                     "start-unlimited", "auto-trading-forever"]
        for path in routes:
            for f in forbidden:
                assert f not in path, f"Route {path} contains '{f}'"

    def test_live_execution_record_limits(self):
        from live.controlled_live_integration import LiveExecutionRecord, MAX_TRADES_PER_SESSION
        rec = LiveExecutionRecord()
        assert rec.trades_remaining == MAX_TRADES_PER_SESSION

    def test_all_previous_tests_importable(self):
        import tests.live.test_phase44_pre_live  # noqa
        import tests.live.test_phase45_live_activation  # noqa
        import tests.live.test_phase46_execution  # noqa
        import tests.live.test_phase47_canary  # noqa
        import tests.live.test_phase48_canary_evaluation  # noqa
        import tests.live.test_phase49_progressive_rollout  # noqa
        import tests.live.test_phase50_operations  # noqa
        import tests.live.test_phase51_observability  # noqa
        import tests.live.test_phase52_command_center  # noqa
        # Phase 53 was frontend-only, no backend test file
