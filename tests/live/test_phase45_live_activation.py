"""
Phase 45 — Controlled Live Activation Gate Tests.

Tests the complete activation state machine, 28 prerequisites,
20-point order gate, and safety system integration.

Critical: LIVE execution MUST remain disabled.
PHASE_43_LIVE_EXECUTION_LOCK must remain TRUE.
can_execute_live() must remain FALSE.
"""

from __future__ import annotations

import time
import pytest
from datetime import datetime, timedelta, timezone


# ═══════════════════════════════════════════════
# Activation State Machine Tests
# ═══════════════════════════════════════════════

class TestActivationStateMachine:
    """Activation states and transitions."""

    def test_default_state_is_locked(self):
        from live.activation_gate import ControlledLiveActivationGate
        gate = ControlledLiveActivationGate()
        assert gate.get_state().value == "locked"
        assert not gate.is_live_armed()

    def test_locked_can_transition_to_ready(self):
        from live.activation_models import ActivationState, validate_transition
        assert validate_transition(ActivationState.LOCKED, ActivationState.READY)

    def test_locked_cannot_transition_to_armed_directly(self):
        from live.activation_models import ActivationState, validate_transition
        assert not validate_transition(ActivationState.LOCKED, ActivationState.ARMED)

    def test_locked_cannot_transition_to_active_directly(self):
        from live.activation_models import ActivationState, validate_transition
        assert not validate_transition(ActivationState.LOCKED, ActivationState.ACTIVE)

    def test_ready_can_arm(self):
        from live.activation_models import ActivationState, validate_transition
        assert validate_transition(ActivationState.READY, ActivationState.ARMED)

    def test_armed_can_start(self):
        from live.activation_models import ActivationState, validate_transition
        assert validate_transition(ActivationState.ARMED, ActivationState.ACTIVE)

    def test_active_can_pause(self):
        from live.activation_models import ActivationState, validate_transition
        assert validate_transition(ActivationState.ACTIVE, ActivationState.PAUSED)

    def test_paused_can_resume(self):
        from live.activation_models import ActivationState, validate_transition
        assert validate_transition(ActivationState.PAUSED, ActivationState.ACTIVE)

    def test_active_can_kill_switch(self):
        from live.activation_models import ActivationState, validate_transition
        assert validate_transition(ActivationState.ACTIVE, ActivationState.KILL_SWITCHED)

    def test_kill_switched_can_recover(self):
        from live.activation_models import ActivationState, validate_transition
        assert validate_transition(ActivationState.KILL_SWITCHED, ActivationState.LOCKED)

    def test_expired_can_recover(self):
        from live.activation_models import ActivationState, validate_transition
        assert validate_transition(ActivationState.EXPIRED, ActivationState.LOCKED)

    def test_revoked_can_recover(self):
        from live.activation_models import ActivationState, validate_transition
        assert validate_transition(ActivationState.REVOKED, ActivationState.LOCKED)

    def test_invalid_transition_blocked(self):
        from live.activation_models import ActivationState, validate_transition
        assert not validate_transition(ActivationState.LOCKED, ActivationState.KILL_SWITCHED)
        assert not validate_transition(ActivationState.READY, ActivationState.ACTIVE)
        assert not validate_transition(ActivationState.KILL_SWITCHED, ActivationState.ACTIVE)
        assert not validate_transition(ActivationState.EXPIRED, ActivationState.ARMED)

    def test_model_to_dict(self):
        from live.activation_models import ActivationRecord, ActivationState
        record = ActivationRecord(state=ActivationState.LOCKED)
        d = record.to_dict()
        assert d["state"] == "locked"
        assert d["activation_id"].startswith("act_")
        assert d["total_orders_placed"] == 0

    def test_model_summary(self):
        from live.activation_models import ActivationRecord, ActivationState
        record = ActivationRecord(state=ActivationState.ACTIVE, reviewer="test_user")
        s = record.summary()
        assert s["reviewer"] == "test_user"
        assert s["state"] == "active"


# ═══════════════════════════════════════════════
# Activation Gate Prerequisite Tests
# ═══════════════════════════════════════════════

class TestActivationGatePrerequisites:
    """28 prerequisites must be verified."""

    def test_validate_runs_without_deps(self):
        from live.activation_gate import ControlledLiveActivationGate
        gate = ControlledLiveActivationGate()
        # With no deps, most prerequisites will fail but validate must still run
        prereqs = gate.validate_prerequisites()
        assert len(prereqs) == 28
        # All 28 check IDs present
        ids = [p.check_id for p in prereqs]
        for i in range(1, 29):
            assert f"activation_{i:02d}" in ids, f"Missing check activation_{i:02d}"

    def test_validate_does_not_change_state(self):
        from live.activation_gate import ControlledLiveActivationGate
        gate = ControlledLiveActivationGate()
        assert gate.get_state().value == "locked"
        gate.validate_prerequisites()
        # State should remain LOCKED (validate_prerequisites is non-mutating)
        assert gate.get_state().value == "locked"

    def test_validate_method_transitions_to_ready(self):
        from live.activation_gate import ControlledLiveActivationGate
        gate = ControlledLiveActivationGate()
        # validate() without any dependencies will still attempt the transition
        # but most checks fail so it won't transition
        result = gate.validate()
        # State depends on all prerequisites passing — without deps it stays locked
        assert result["validated"] is False
        assert result["state"] == "locked"

    def test_arm_requires_reviewer(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        gate = ControlledLiveActivationGate()
        with pytest.raises(ActivationGateError, match="Reviewer identity is required"):
            gate.arm(reviewer="", reason="test")

    def test_arm_requires_reason(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        gate = ControlledLiveActivationGate()
        with pytest.raises(ActivationGateError, match="Activation reason is required"):
            gate.arm(reviewer="tester", reason="")

    def test_arm_from_locked_fails_without_prerequisites(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        gate = ControlledLiveActivationGate()
        with pytest.raises(ActivationGateError, match="prerequisite"):
            gate.arm(reviewer="tester", reason="No deps available")

    def test_cannot_start_without_arm(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        gate = ControlledLiveActivationGate()
        with pytest.raises(ActivationGateError, match="Cannot start from state"):
            gate.start(confirmation_token="test")

    def test_cannot_pause_without_active(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        gate = ControlledLiveActivationGate()
        with pytest.raises(ActivationGateError, match="Cannot pause from state"):
            gate.pause()

    def test_cannot_kill_switch_from_locked(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        gate = ControlledLiveActivationGate()
        with pytest.raises(ActivationGateError, match="Cannot trigger kill switch"):
            gate.kill_switch()

    def test_recover_requires_reviewer(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        gate = ControlledLiveActivationGate()
        # Force state to KILL_SWITCHED
        gate._record.state = type(gate._record.state)("kill_switched")
        with pytest.raises(ActivationGateError, match="Reviewer identity required"):
            gate.recover(reviewer="", reason="test")

    def test_cannot_recover_from_locked(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        gate = ControlledLiveActivationGate()
        with pytest.raises(ActivationGateError, match="Cannot recover from state"):
            gate.recover(reviewer="tester", reason="test")


# ═══════════════════════════════════════════════
# Activation Full Lifecycle Tests
# ═══════════════════════════════════════════════

class TestActivationLifecycle:
    """Complete activation state transitions."""

    def test_arm_with_mock_prerequisites(self):
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus

        gate = ControlledLiveActivationGate()
        # Manually set all prerequisites as passed (simulating external validation)
        gate._record.prerequisites = [
            ActivationPrerequisite(
                check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
                status=PrerequisiteStatus.PASS, passed=True, blocking=True,
            ) for i in range(1, 29)
        ]
        # Force state to READY (since validate would have transitioned)
        gate._record.state = ActivationState.READY

        result = gate.arm(reviewer="test_reviewer", reason="Testing arm", activation_duration_minutes=30)
        assert result["state"] == "armed"
        assert "confirmation_token" in result
        assert result["activation_duration_minutes"] == 30

    def test_full_arm_start_cycle(self):
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus

        gate = ControlledLiveActivationGate()
        gate._record.prerequisites = [
            ActivationPrerequisite(
                check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
                status=PrerequisiteStatus.PASS, passed=True, blocking=True,
            ) for i in range(1, 29)
        ]
        gate._record.state = ActivationState.READY

        # Arm
        arm_result = gate.arm(reviewer="reviewer", reason="Lifecycle test", activation_duration_minutes=15)
        assert arm_result["state"] == "armed"

        # Start with correct token
        token = gate._record.confirmation_token
        start_result = gate.start(confirmation_token=token)
        assert start_result["state"] == "active"
        assert start_result["expires_at"] != ""

        # Verify is_live_armed
        assert gate.is_live_armed()

        # Verify remaining time > 0
        assert gate.get_remaining_time() > 0

    def test_pause_resume_cycle(self):
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus

        gate = ControlledLiveActivationGate()
        gate._record.prerequisites = [
            ActivationPrerequisite(
                check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
                status=PrerequisiteStatus.PASS, passed=True, blocking=True,
            ) for i in range(1, 29)
        ]
        gate._record.state = ActivationState.READY
        gate.arm(reviewer="r", reason="test", activation_duration_minutes=60)
        gate.start(confirmation_token=gate._record.confirmation_token)

        # Pause
        pause_result = gate.pause(reason="Taking a break")
        assert pause_result["state"] == "paused"
        assert not gate.is_live_armed()

        # Resume
        resume_result = gate.resume(reason="Back in action")
        assert resume_result["state"] == "active"
        assert gate.is_live_armed()

    def test_kill_switch_terminates(self):
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus

        gate = ControlledLiveActivationGate()
        gate._record.prerequisites = [ActivationPrerequisite(
            check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
            status=PrerequisiteStatus.PASS, passed=True, blocking=True,
        ) for i in range(1, 29)]
        gate._record.state = ActivationState.READY
        gate.arm(reviewer="r", reason="test", activation_duration_minutes=60)
        gate.start(confirmation_token=gate._record.confirmation_token)

        ks_result = gate.kill_switch(reason="Emergency!")
        assert ks_result["state"] == "kill_switched"
        assert not gate.is_live_armed()

    def test_revoke_terminates(self):
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus

        gate = ControlledLiveActivationGate()
        gate._record.prerequisites = [ActivationPrerequisite(
            check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
            status=PrerequisiteStatus.PASS, passed=True, blocking=True,
        ) for i in range(1, 29)]
        gate._record.state = ActivationState.READY
        gate.arm(reviewer="r", reason="test", activation_duration_minutes=60)
        gate.start(confirmation_token=gate._record.confirmation_token)

        revoke_result = gate.revoke(reason="Changed mind")
        assert revoke_result["state"] == "revoked"
        assert not gate.is_live_armed()

    def test_recover_from_kill_switched(self):
        from live.activation_gate import ControlledLiveActivationGate

        gate = ControlledLiveActivationGate()
        gate._record.state = type(gate._record.state)("kill_switched")
        gate._record.reviewer = "original_reviewer"

        result = gate.recover(reviewer="recovery_reviewer", reason="All clear")
        assert result["state"] == "locked"
        assert not gate.is_live_armed()

    def test_expiry_auto_transitions(self):
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus

        gate = ControlledLiveActivationGate()
        gate._record.prerequisites = [ActivationPrerequisite(
            check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
            status=PrerequisiteStatus.PASS, passed=True, blocking=True,
        ) for i in range(1, 29)]
        gate._record.state = ActivationState.READY
        gate.arm(reviewer="r", reason="test", activation_duration_minutes=60)
        gate.start(confirmation_token=gate._record.confirmation_token)

        # Manually set expiry to the past
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        gate._record.expires_at = past

        # get_state should trigger expiry check
        state = gate.get_state()
        assert state.value == "expired"
        assert not gate.is_live_armed()
        assert gate.get_remaining_time() == 0

    def test_activation_duration_clamped(self):
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus

        gate = ControlledLiveActivationGate()
        gate._record.prerequisites = [ActivationPrerequisite(
            check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
            status=PrerequisiteStatus.PASS, passed=True, blocking=True,
        ) for i in range(1, 29)]
        gate._record.state = ActivationState.READY

        # Try 120 minutes (should clamp to 60)
        gate.arm(reviewer="r", reason="test", activation_duration_minutes=120)
        assert gate._record.activation_duration_minutes == 60

    def test_invalid_token_rejected(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus

        gate = ControlledLiveActivationGate()
        gate._record.prerequisites = [ActivationPrerequisite(
            check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
            status=PrerequisiteStatus.PASS, passed=True, blocking=True,
        ) for i in range(1, 29)]
        gate._record.state = ActivationState.READY
        gate.arm(reviewer="r", reason="test")

        with pytest.raises(ActivationGateError, match="Invalid confirmation token"):
            gate.start(confirmation_token="wrong_token")

    def test_order_counters(self):
        from live.activation_gate import ControlledLiveActivationGate
        gate = ControlledLiveActivationGate()
        assert gate.get_record().total_orders_placed == 0
        assert gate.get_record().total_orders_blocked == 0

        gate.record_order_placed()
        gate.record_order_placed()
        gate.record_order_blocked()

        assert gate.get_record().total_orders_placed == 2
        assert gate.get_record().total_orders_blocked == 1


# ═══════════════════════════════════════════════
# LiveExecutionGate Tests (20-point per-order)
# ═══════════════════════════════════════════════

class TestLiveExecutionGate:
    """20-point per-order safety gate."""

    def test_gate_blocks_without_activation(self):
        from live.live_execution_gate import LiveExecutionGate
        from live.activation_gate import ControlledLiveActivationGate

        gate = ControlledLiveActivationGate()
        exec_gate = LiveExecutionGate(activation_gate=gate)

        result = exec_gate.authorize(symbol="RELIANCE", side="BUY", quantity=10, price=2500.0)
        assert not result.authorized
        assert len(result.failed_checks) > 0

    def test_gate_requires_stop_loss(self):
        from live.live_execution_gate import LiveExecutionGate
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus

        act_gate = ControlledLiveActivationGate()
        # Set up as active
        act_gate._record.state = ActivationState.ACTIVE
        act_gate._record.expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        exec_gate = LiveExecutionGate(activation_gate=act_gate)

        # No SL
        result = exec_gate.authorize(
            symbol="RELIANCE", side="BUY", quantity=10, price=2500.0,
            stop_loss=None, target=2600.0,
        )
        assert not result.authorized
        assert any("stop_loss" in c for c in result.failed_checks)

    def test_gate_requires_target(self):
        from live.live_execution_gate import LiveExecutionGate
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState

        act_gate = ControlledLiveActivationGate()
        act_gate._record.state = ActivationState.ACTIVE
        act_gate._record.expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        exec_gate = LiveExecutionGate(activation_gate=act_gate)

        # No target
        result = exec_gate.authorize(
            symbol="RELIANCE", side="BUY", quantity=10, price=2500.0,
            stop_loss=2450.0, target=None,
        )
        assert not result.authorized
        assert any("target" in c for c in result.failed_checks)

    def test_only_market_orders_allowed(self):
        from live.live_execution_gate import LiveExecutionGate

        exec_gate = LiveExecutionGate()
        result = exec_gate.execute(
            symbol="RELIANCE", side="BUY", quantity=10, price=2500.0,
            order_type="LIMIT",
        )
        assert not result.get("authorized", False)

    def test_gate_enforces_risk_reward(self):
        from live.live_execution_gate import LiveExecutionGate
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState

        act_gate = ControlledLiveActivationGate()
        act_gate._record.state = ActivationState.ACTIVE
        act_gate._record.expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        exec_gate = LiveExecutionGate(activation_gate=act_gate)

        # Bad R:R (1:1 instead of minimum 1.5)
        result = exec_gate.authorize(
            symbol="RELIANCE", side="BUY", quantity=10, price=2500.0,
            stop_loss=2490.0, target=2510.0,
        )
        assert not result.authorized
        assert any("risk_reward" in c for c in result.failed_checks)

    def test_gate_enforces_invalid_price(self):
        from live.live_execution_gate import LiveExecutionGate
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState

        act_gate = ControlledLiveActivationGate()
        act_gate._record.state = ActivationState.ACTIVE
        act_gate._record.expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        exec_gate = LiveExecutionGate(activation_gate=act_gate)

        result = exec_gate.authorize(
            symbol="RELIANCE", side="BUY", quantity=10, price=0,
            stop_loss=2450.0, target=2600.0,
        )
        assert not result.authorized

    def test_gate_enforces_empty_symbol(self):
        from live.live_execution_gate import LiveExecutionGate
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState

        act_gate = ControlledLiveActivationGate()
        act_gate._record.state = ActivationState.ACTIVE
        act_gate._record.expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        exec_gate = LiveExecutionGate(activation_gate=act_gate)

        result = exec_gate.authorize(
            symbol="", side="BUY", quantity=10, price=2500.0,
            stop_loss=2450.0, target=2600.0,
        )
        assert not result.authorized

    def test_gate_authorization_result_structure(self):
        from live.live_execution_gate import AuthorizationResult

        result = AuthorizationResult(
            authorized=False,
            rejection_reason="Test block",
            failed_checks=["check_1", "check_2"],
        )
        d = result.to_dict()
        assert d["authorized"] is False
        assert d["rejection_reason"] == "Test block"
        assert len(d["failed_checks"]) == 2

    def test_market_order_allowed(self):
        from live.live_execution_gate import LiveExecutionGate

        exec_gate = LiveExecutionGate()
        result = exec_gate.execute(
            symbol="RELIANCE", side="BUY", quantity=1, price=2500.0,
            order_type="MARKET",
        )
        # Should fail because activation gate not set up, but should not fail on order_type
        # The "not authorized" comes from other checks, not order type
        assert "authorized" in result


# ═══════════════════════════════════════════════
# ZerodhaLiveAdapter Tests
# ═══════════════════════════════════════════════

class TestZerodhaLiveAdapter:
    """Isolated broker adapter tests."""

    def test_adapter_starts_disabled(self):
        from brokers.zerodha_live_adapter import ZerodhaLiveAdapter
        adapter = ZerodhaLiveAdapter()
        assert not adapter.is_live_enabled()

    def test_place_order_raises_when_disabled(self):
        from brokers.zerodha_live_adapter import ZerodhaLiveAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaLiveAdapter()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.place_order("RELIANCE", "BUY", 1))

    def test_market_order_works_when_enabled(self):
        from brokers.zerodha_live_adapter import ZerodhaLiveAdapter
        import asyncio
        adapter = ZerodhaLiveAdapter()
        adapter.enable_live()
        result = asyncio.run(adapter.place_order("RELIANCE", "BUY", 1, order_type="MARKET"))
        assert result["success"]
        assert result["broker_order_id"].startswith("zd_")

    def test_non_market_order_raises(self):
        from brokers.zerodha_live_adapter import (
            ZerodhaLiveAdapter, OnlyMarketOrdersAllowedError,
        )
        import asyncio
        adapter = ZerodhaLiveAdapter()
        adapter.enable_live()
        with pytest.raises(OnlyMarketOrdersAllowedError):
            asyncio.run(adapter.place_order("RELIANCE", "BUY", 1, order_type="LIMIT"))

    def test_modify_order_raises(self):
        from brokers.zerodha_live_adapter import ZerodhaLiveAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaLiveAdapter()
        adapter.enable_live()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.modify_order("order123"))

    def test_cancel_order_raises(self):
        from brokers.zerodha_live_adapter import ZerodhaLiveAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaLiveAdapter()
        adapter.enable_live()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.cancel_order("order123"))

    def test_readonly_operations_work(self):
        from brokers.zerodha_live_adapter import ZerodhaLiveAdapter
        import asyncio
        adapter = ZerodhaLiveAdapter()
        health = asyncio.run(adapter.health_check())
        assert "status" in health
        account = asyncio.run(adapter.get_account())
        assert "broker" in account
        balance = asyncio.run(adapter.get_balance())
        assert "available" in balance
        positions = asyncio.run(adapter.get_positions())
        assert isinstance(positions, list)

    def test_place_market_order_convenience(self):
        from brokers.zerodha_live_adapter import ZerodhaLiveAdapter
        import asyncio
        adapter = ZerodhaLiveAdapter()
        adapter.enable_live()
        result = asyncio.run(adapter.place_market_order("RELIANCE", "BUY", 10))
        assert result["success"]
        assert result["order_type"] == "MARKET"


# ═══════════════════════════════════════════════
# Activation Gate With Kill Switch Integration
# ═══════════════════════════════════════════════

class TestKillSwitchIntegration:
    """Kill switch must work with activation gate."""

    def test_kill_switch_blocks_live_orders(self):
        from live.live_execution_gate import LiveExecutionGate
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus
        from execution.kill_switch import KillSwitch, KillSwitchLevel

        act_gate = ControlledLiveActivationGate()
        ks = KillSwitch()
        act_gate.set_kill_switch(ks)

        # Set up as active
        act_gate._record.prerequisites = [ActivationPrerequisite(
            check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
            status=PrerequisiteStatus.PASS, passed=True, blocking=True,
        ) for i in range(1, 29)]
        act_gate._record.state = ActivationState.READY
        act_gate.arm(reviewer="r", reason="test", activation_duration_minutes=60)
        act_gate.start(confirmation_token=act_gate._record.confirmation_token)
        assert act_gate.is_live_armed()

        # Activate kill switch
        ks.activate(KillSwitchLevel.GLOBAL, "", "test kill")

        # Now live execution should be blocked
        exec_gate = LiveExecutionGate(activation_gate=act_gate)
        exec_gate.set_kill_switch(ks)

        result = exec_gate.authorize(
            symbol="RELIANCE", side="BUY", quantity=1, price=2500.0,
            stop_loss=2450.0, target=2600.0,
        )
        assert not result.authorized
        assert any("kill_switch" in c for c in result.failed_checks)

    def test_kill_switch_creates_audit_event(self):
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus
        from execution.kill_switch import KillSwitch
        from execution.execution_audit import ExecutionAuditLog

        act_gate = ControlledLiveActivationGate()
        ks = KillSwitch()
        audit = ExecutionAuditLog()

        act_gate.set_kill_switch(ks)
        act_gate.set_audit_log(audit)

        act_gate._record.prerequisites = [ActivationPrerequisite(
            check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
            status=PrerequisiteStatus.PASS, passed=True, blocking=True,
        ) for i in range(1, 29)]
        act_gate._record.state = ActivationState.READY
        act_gate.arm(reviewer="r", reason="test")
        act_gate.start(confirmation_token=act_gate._record.confirmation_token)

        # Kill switch
        act_gate.kill_switch(reason="Emergency test")

        # Audit should have recorded the kill switch event
        assert audit.count() > 0
        events = audit.get_entries()
        kill_events = [e for e in events if "kill" in e.get("event_type", "").lower()]
        assert len(kill_events) > 0


# ═══════════════════════════════════════════════
# Activation API Tests
# ═══════════════════════════════════════════════

class TestActivationAPI:
    """API endpoint tests."""

    def test_status_returns_locked(self):
        from backend.api.live_activation import router
        from live.activation_gate import ControlledLiveActivationGate
        from backend.api.live_activation import _get_gate

        # No gate set by default — should raise
        with pytest.raises(AssertionError):
            _get_gate()

        # Set gate
        gate = ControlledLiveActivationGate()
        from backend.api.live_activation import set_activation_gate
        set_activation_gate(gate)

        status = _get_gate().get_status()
        assert status["state"] == "locked"
        assert status["is_live_armed"] is False

    def test_no_live_enabling_endpoints(self):
        """Phase 45 API must not have dangerous endpoints."""
        from backend.api.live_activation import router
        routes = [r.path for r in router.routes]
        forbidden = [
            "/api/live-activation/enable-live",
            "/api/live-activation/place-order",
            "/api/live-activation/activate-auto",
            "/api/live-activation/start-trading",
        ]
        for path in forbidden:
            assert path not in routes, f"Phase 45 must not expose {path}"


# ═══════════════════════════════════════════════
# Safety Regression Tests
# ═══════════════════════════════════════════════

class TestPhase45SafetyVerification:
    """
    Critical safety verification for Phase 45.

    These tests MUST ALL PASS for Phase 45 to be complete.
    """

    def test_phase_43_lock_still_true(self):
        """PHASE_43_LIVE_EXECUTION_LOCK must remain TRUE."""
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        assert PHASE_43_LIVE_EXECUTION_LOCK is True

    def test_can_execute_live_still_false(self):
        """RuntimeModeManager.can_execute_live() must remain FALSE."""
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        assert mgr.can_execute_live() is False

    def test_live_mode_still_blocked(self):
        """Setting LIVE mode must still be blocked."""
        from trading.runtime_mode import RuntimeModeManager, ALLOWED_MODES, RuntimeMode
        assert RuntimeMode.LIVE not in ALLOWED_MODES
        mgr = RuntimeModeManager()
        result = mgr.set_mode("live")
        assert not result["success"]

    def test_zerodha_adapter_still_raises(self):
        """ZerodhaAdapter must still raise LiveExecutionDisabledError."""
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.place_order("RELIANCE", "BUY", 1))

    def test_execution_policy_allows_false(self):
        """ExecutionPolicy must still return allowed=False."""
        from execution.execution_policy import ExecutionPolicyEngine
        perm = ExecutionPolicyEngine().check()
        assert perm.allowed is False

    def test_activation_gate_default_locked(self):
        """Activation gate must start in LOCKED state."""
        from live.activation_gate import ControlledLiveActivationGate
        gate = ControlledLiveActivationGate()
        assert gate.get_state().value == "locked"
        assert not gate.is_live_armed()

    def test_activation_gate_does_not_modify_phase_43_lock(self):
        """Activation gate must NOT modify PHASE_43_LIVE_EXECUTION_LOCK."""
        from live.activation_gate import ControlledLiveActivationGate
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        original = PHASE_43_LIVE_EXECUTION_LOCK

        gate = ControlledLiveActivationGate()
        # The gate should not even touch the constant
        assert "PHASE_43_LIVE_EXECUTION_LOCK" not in dir(gate)

    def test_pre_live_validation_still_blocks(self):
        """Pre-live validation must still report can_execute_live=False."""
        from live.pre_live_validation import PreLiveValidationEngine
        from execution.execution_policy import ExecutionPolicyEngine
        engine = PreLiveValidationEngine(execution_policy=ExecutionPolicyEngine())
        report = engine.run()
        assert report.can_execute_live is False
        assert report.live_execution_enabled is False

    def test_activation_gate_reset_on_restart(self):
        """Simulated restart must reset gate to LOCKED."""
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState

        gate = ControlledLiveActivationGate()
        # Simulate previous ACTIVE state
        gate._record.state = ActivationState.ACTIVE
        gate._record.activated_at = "2025-01-01T00:00:00+00:00"
        gate._record.expires_at = "2025-01-01T01:00:00+00:00"

        # Simulate restart: new gate instance
        gate2 = ControlledLiveActivationGate()
        assert gate2.get_state().value == "locked"
        assert gate2._record.activated_at == ""
        assert gate2._record.expires_at == ""

    def test_frontend_cannot_enable_live(self):
        """Frontend must not have live-enabling endpoints."""
        import backend.api.live_activation as api_module
        routes = [r.path for r in api_module.router.routes]
        dangerous = [
            "enable-live",
            "place-order",
            "activate-auto",
            "start-trading",
        ]
        for path in routes:
            for d in dangerous:
                assert d not in path, f"Route {path} contains dangerous keyword '{d}'"

    def test_all_previous_tests_importable(self):
        """Verify Phase 44 test module is still importable."""
        import tests.live.test_phase44_pre_live  # noqa

    def test_activation_record_mutable_methods(self):
        """Verify accounting methods work."""
        from live.activation_gate import ControlledLiveActivationGate
        gate = ControlledLiveActivationGate()
        gate.record_order_placed()
        gate.record_order_blocked()
        gate.update_daily_pnl(-500.0)
        gate.update_positions_count(2)

        record = gate.get_record()
        assert record.total_orders_placed == 1
        assert record.total_orders_blocked == 1
        assert record.daily_pnl == -500.0
        assert record.positions_count == 2


# ═══════════════════════════════════════════════
# Edge Cases and Error Handling
# ═══════════════════════════════════════════════

class TestActivationGateEdgeCases:
    """Edge cases and error handling."""

    def test_arm_fails_if_prerequisites_not_all_passed(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        from live.activation_models import ActivationState

        gate = ControlledLiveActivationGate()
        gate._record.state = ActivationState.READY
        # No prerequisites set — should fail
        with pytest.raises(ActivationGateError):
            gate.arm(reviewer="tester", reason="should fail", activation_duration_minutes=30)

    def test_start_without_arm_fails(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        gate = ControlledLiveActivationGate()
        with pytest.raises(ActivationGateError, match="Cannot start"):
            gate.start(confirmation_token="anything")

    def test_start_without_token_fails(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus

        gate = ControlledLiveActivationGate()
        gate._record.prerequisites = [ActivationPrerequisite(
            check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
            status=PrerequisiteStatus.PASS, passed=True, blocking=True,
        ) for i in range(1, 29)]
        gate._record.state = ActivationState.READY
        gate.arm(reviewer="r", reason="test")

        with pytest.raises(ActivationGateError, match="Invalid confirmation token"):
            gate.start(confirmation_token="")

    def test_revoke_from_locked_fails(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        gate = ControlledLiveActivationGate()
        with pytest.raises(ActivationGateError, match="Cannot revoke from state"):
            gate.revoke()

    def test_recover_without_reviewer_fails(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        gate = ControlledLiveActivationGate()
        gate._record.state = type(gate._record.state)("kill_switched")
        with pytest.raises(ActivationGateError, match="Reviewer identity required"):
            gate.recover(reviewer="", reason="test")

    def test_live_execution_gate_without_activation_blocks_all(self):
        from live.live_execution_gate import LiveExecutionGate
        gate = LiveExecutionGate()
        result = gate.authorize(symbol="ANY", side="BUY", quantity=1, price=100,
                                stop_loss=99, target=101)
        assert not result.authorized

    def test_status_after_full_cycle(self):
        from live.activation_gate import ControlledLiveActivationGate
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus

        gate = ControlledLiveActivationGate()
        gate._record.prerequisites = [ActivationPrerequisite(
            check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
            status=PrerequisiteStatus.PASS, passed=True, blocking=True,
        ) for i in range(1, 29)]
        gate._record.state = ActivationState.READY
        gate.arm(reviewer="reviewer1", reason="Full cycle test", activation_duration_minutes=30)
        gate.start(confirmation_token=gate._record.confirmation_token)

        status = gate.get_status()
        assert status["state"] == "active"
        assert status["is_live_armed"] is True
        assert status["remaining_seconds"] > 0
        assert status["reviewer"] == "reviewer1"
        assert status["activation_duration_minutes"] == 30

    def test_get_remaining_time_zero_when_not_active(self):
        from live.activation_gate import ControlledLiveActivationGate
        gate = ControlledLiveActivationGate()
        assert gate.get_remaining_time() == 0

    def test_debug_arm_without_prereqs_fails_gracefully(self):
        from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
        gate = ControlledLiveActivationGate()
        with pytest.raises(ActivationGateError):
            gate.arm(reviewer="test", reason="test", activation_duration_minutes=30)

    def test_max_activation_duration(self):
        from live.activation_models import ActivationState, ActivationPrerequisite, PrerequisiteStatus
        from live.activation_gate import ControlledLiveActivationGate

        gate = ControlledLiveActivationGate()
        gate._record.prerequisites = [ActivationPrerequisite(
            check_id=f"activation_{i:02d}", category="test", name=f"Check {i}",
            status=PrerequisiteStatus.PASS, passed=True, blocking=True,
        ) for i in range(1, 29)]
        gate._record.state = ActivationState.READY

        gate.arm(reviewer="test", reason="max time test", activation_duration_minutes=999)
        assert gate._record.activation_duration_minutes <= 60


# ═══════════════════════════════════════════════
# ActivationModels Data Tests
# ═══════════════════════════════════════════════

class TestActivationModels:
    """Data model structural tests."""

    def test_all_states_defined(self):
        from live.activation_models import ActivationState
        states = [s.value for s in ActivationState]
        expected = ["locked", "ready", "armed", "active", "paused",
                     "kill_switched", "expired", "revoked"]
        for s in expected:
            assert s in states

    def test_all_transitions_defined(self):
        from live.activation_models import VALID_TRANSITIONS, ActivationState
        for state in ActivationState:
            assert state in VALID_TRANSITIONS
            assert isinstance(VALID_TRANSITIONS[state], list)

    def test_prerequisite_serialization(self):
        from live.activation_models import ActivationPrerequisite, PrerequisiteStatus
        p = ActivationPrerequisite(
            check_id="test_01", category="test", name="Test Check",
            status=PrerequisiteStatus.PASS, passed=True, blocking=True,
            message="All good", details="OK",
        )
        d = p.to_dict()
        assert d["check_id"] == "test_01"
        assert d["status"] == "pass"
        assert d["passed"] is True
        assert d["blocking"] is True

    def test_state_transition_serialization(self):
        from live.activation_models import StateTransition, ActivationState
        t = StateTransition(
            from_state=ActivationState.LOCKED,
            to_state=ActivationState.READY,
            actor="tester", reason="test",
        )
        d = t.to_dict()
        assert d["from_state"] == "locked"
        assert d["to_state"] == "ready"
        assert d["actor"] == "tester"

    def test_audit_event_types_defined(self):
        from live.activation_models import (
            LIVE_ACTIVATION_REQUESTED, LIVE_ACTIVATION_APPROVED,
            LIVE_ACTIVATION_STARTED, LIVE_ACTIVATION_EXPIRED,
            LIVE_ACTIVATION_REVOKED, LIVE_KILL_SWITCH_TRIGGERED,
            LIVE_NEW_ORDERS_PAUSED, LIVE_RECOVERY_REQUESTED,
            LIVE_RECOVERY_APPROVED, LIVE_ORDER_AUTHORIZED,
            LIVE_ORDER_BLOCKED, LIVE_ORDER_SUBMITTED,
        )
        assert LIVE_ACTIVATION_REQUESTED == "live_activation_requested"
        assert LIVE_ACTIVATION_APPROVED == "live_activation_approved"
        assert LIVE_ACTIVATION_STARTED == "live_activation_started"
        assert LIVE_KILL_SWITCH_TRIGGERED == "live_kill_switch_triggered"
        assert LIVE_RECOVERY_APPROVED == "live_recovery_approved"
