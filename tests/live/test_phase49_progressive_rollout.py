"""
Phase 49 — Controlled Multi-Canary & Progressive Live Rollout Tests.

Tests multi-canary sequencing, stage progression, eligibility,
rollback conditions, and safety verification.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta


# ═══════════════════════════════════════════════
# Multi-Canary Tracker Tests
# ═══════════════════════════════════════════════

class TestMultiCanaryTracker:
    """Multi-canary sequencing."""

    def test_empty_tracker(self):
        from live.multi_canary import MultiCanaryRolloutTracker
        tracker = MultiCanaryRolloutTracker()
        summary = tracker.get_summary()
        assert summary["total_canaries"] == 0
        assert tracker.can_proceed_to_next()  # First canary always allowed

    def test_record_canary(self):
        from live.multi_canary import MultiCanaryRolloutTracker, CanaryRecord
        tracker = MultiCanaryRolloutTracker()
        record = CanaryRecord(authorization_id="auth_1", symbol="TCS",
                               direction="BUY", quantity=1, pnl=50.0)
        tracker.record_canary(record)
        assert tracker.get_summary()["total_canaries"] == 1

    def test_canary_sequence_assigned(self):
        from live.multi_canary import MultiCanaryRolloutTracker, CanaryRecord
        tracker = MultiCanaryRolloutTracker()
        r1 = CanaryRecord(authorization_id="a1")
        r2 = CanaryRecord(authorization_id="a2")
        tracker.record_canary(r1)
        tracker.record_canary(r2)
        assert r1.sequence == 1
        assert r2.sequence == 2

    def test_can_proceed_to_next(self):
        from live.multi_canary import MultiCanaryRolloutTracker, CanaryRecord
        tracker = MultiCanaryRolloutTracker()
        assert tracker.can_proceed_to_next()
        r = CanaryRecord(authorization_id="a1", evaluation_classification="pass")
        tracker.record_canary(r)
        assert tracker.can_proceed_to_next()

    def test_cannot_exceed_max_sequence(self):
        from live.multi_canary import MultiCanaryRolloutTracker, CanaryRecord, MAX_CANARY_SEQUENCE
        tracker = MultiCanaryRolloutTracker()
        for i in range(MAX_CANARY_SEQUENCE):
            r = CanaryRecord(authorization_id=f"a{i+1}", evaluation_classification="pass")
            tracker.record_canary(r)
        assert not tracker.can_proceed_to_next()

    def test_cannot_proceed_without_evaluation(self):
        from live.multi_canary import MultiCanaryRolloutTracker, CanaryRecord
        tracker = MultiCanaryRolloutTracker()
        r = CanaryRecord(authorization_id="a1")  # No evaluation classification
        tracker.record_canary(r)
        assert not tracker.can_proceed_to_next()

    def test_failed_evaluation_blocks_next(self):
        from live.multi_canary import MultiCanaryRolloutTracker, CanaryRecord
        tracker = MultiCanaryRolloutTracker()
        r = CanaryRecord(authorization_id="a1", evaluation_classification="fail")
        tracker.record_canary(r)
        assert not tracker.can_proceed_to_next()

    def test_get_canary_by_sequence(self):
        from live.multi_canary import MultiCanaryRolloutTracker, CanaryRecord
        tracker = MultiCanaryRolloutTracker()
        r = CanaryRecord(authorization_id="a1")
        tracker.record_canary(r)
        found = tracker.get_canary(1)
        assert found is not None
        assert found.authorization_id == "a1"

    def test_canary_record_to_dict(self):
        from live.multi_canary import CanaryRecord
        r = CanaryRecord(authorization_id="a1", symbol="TCS", pnl=100.0)
        d = r.to_dict()
        assert d["symbol"] == "TCS"
        assert d["pnl"] == 100.0


# ═══════════════════════════════════════════════
# Rollout Stage Tests
# ═══════════════════════════════════════════════

class TestRolloutStages:
    """Rollout stage transitions."""

    def test_valid_transitions(self):
        from live.rollout_stages import validate_stage_transition, RolloutStage
        assert validate_stage_transition(RolloutStage.LOCKED, RolloutStage.CANARY_1)
        assert validate_stage_transition(RolloutStage.CANARY_1, RolloutStage.CANARY_2)
        assert validate_stage_transition(RolloutStage.CANARY_2, RolloutStage.CANARY_3)
        assert validate_stage_transition(RolloutStage.CANARY_3, RolloutStage.LIMITED_ROLLOUT)
        assert validate_stage_transition(RolloutStage.ROLLBACK, RolloutStage.LOCKED)

    def test_invalid_transitions(self):
        from live.rollout_stages import validate_stage_transition, RolloutStage
        assert not validate_stage_transition(RolloutStage.LOCKED, RolloutStage.CANARY_3)
        assert not validate_stage_transition(RolloutStage.CANARY_1, RolloutStage.CONTROLLED_ROLLOUT)
        assert not validate_stage_transition(RolloutStage.LIMITED_ROLLOUT, RolloutStage.CANARY_2)

    def test_stage_limits(self):
        from live.rollout_stages import get_stage_limits, RolloutStage
        limits = get_stage_limits(RolloutStage.CANARY_1)
        assert limits["max_trades"] == 1
        assert limits["max_quantity"] == 1

    def test_stage_limits_non_trading(self):
        from live.rollout_stages import get_stage_limits, RolloutStage
        limits = get_stage_limits(RolloutStage.LOCKED)
        assert limits["max_trades"] == 0

    def test_limits_no_100_percent(self):
        from live.rollout_stages import STAGE_RISK_LIMITS
        for stage, limits in STAGE_RISK_LIMITS.items():
            assert limits["risk_allocation_pct"] < 100

    def test_rollout_record_to_dict(self):
        from live.rollout_stages import RolloutRecord, RolloutStage
        record = RolloutRecord(current_stage=RolloutStage.CANARY_1, reviewer="admin")
        d = record.to_dict()
        assert d["current_stage"] == "canary_1"
        assert d["reviewer"] == "admin"


# ═══════════════════════════════════════════════
# Rollback Controller Tests
# ═══════════════════════════════════════════════

class TestRollbackController:
    """Rollback conditions and execution."""

    def test_no_rollback_needed_for_clean_data(self):
        from live.rollback_controller import RollbackController
        ctrl = RollbackController()
        result = ctrl.check_rollback_conditions({
            "consecutive_losses": 0, "max_drawdown_pct": 0,
            "avg_slippage_pct": 0, "avg_latency_ms": 0,
            "order_mismatches": 0, "position_mismatches": 0,
            "risk_violations": 0, "stale_data_events": 0,
        })
        assert not result.rollback_required

    def test_consecutive_losses_triggers_rollback(self):
        from live.rollback_controller import RollbackController
        ctrl = RollbackController()
        result = ctrl.check_rollback_conditions({
            "consecutive_losses": 5, "max_drawdown_pct": 0,
            "avg_slippage_pct": 0, "avg_latency_ms": 0,
            "order_mismatches": 0, "position_mismatches": 0,
            "risk_violations": 0, "stale_data_events": 0,
        })
        assert result.rollback_required
        assert any("consecutive_losses" in r for r in result.reasons)

    def test_drawdown_triggers_rollback(self):
        from live.rollback_controller import RollbackController
        ctrl = RollbackController()
        result = ctrl.check_rollback_conditions({
            "consecutive_losses": 0, "max_drawdown_pct": 10,
            "avg_slippage_pct": 0, "avg_latency_ms": 0,
            "order_mismatches": 0, "position_mismatches": 0,
            "risk_violations": 0, "stale_data_events": 0,
        })
        assert result.rollback_required

    def test_slippage_triggers_rollback(self):
        from live.rollback_controller import RollbackController
        ctrl = RollbackController()
        result = ctrl.check_rollback_conditions({
            "consecutive_losses": 0, "max_drawdown_pct": 0,
            "avg_slippage_pct": 1.0, "avg_latency_ms": 0,
            "order_mismatches": 0, "position_mismatches": 0,
            "risk_violations": 0, "stale_data_events": 0,
        })
        assert result.rollback_required

    def test_execute_rollback(self):
        from live.rollback_controller import RollbackController
        ctrl = RollbackController()
        result = ctrl.execute_rollback(reason="test")
        assert result.success
        assert result.entries_blocked
        assert result.positions_preserved

    def test_recover_requires_reviewer(self):
        from live.rollback_controller import RollbackController
        ctrl = RollbackController()
        result = ctrl.recover(reviewer="", reason="")
        assert not result["success"]

    def test_recover_with_reviewer(self):
        from live.rollback_controller import RollbackController
        ctrl = RollbackController()
        result = ctrl.recover(reviewer="admin", reason="Reviewed")
        assert result["success"]

    def test_thresholds_immutable(self):
        from live.rollback_controller import RollbackController
        ctrl = RollbackController()
        thresholds = ctrl.get_thresholds()
        assert thresholds["max_consecutive_losses"] == 3
        assert thresholds["max_drawdown_pct"] == 5.0


# ═══════════════════════════════════════════════
# Progressive Rollout Engine Tests
# ═══════════════════════════════════════════════

class TestProgressiveRollout:
    """Rollout engine orchestration."""

    def test_default_stage_locked(self):
        from live.progressive_rollout import ProgressiveRolloutEngine
        engine = ProgressiveRolloutEngine()
        status = engine.get_status()
        assert status["current_stage"] == "locked"

    def test_request_requires_reviewer(self):
        from live.progressive_rollout import ProgressiveRolloutEngine, ProgressiveRolloutError
        engine = ProgressiveRolloutEngine()
        with pytest.raises(ProgressiveRolloutError, match="Reviewer identity is required"):
            engine.request_progression(reviewer="", reason="test", target_stage="canary_1")

    def test_request_requires_target(self):
        from live.progressive_rollout import ProgressiveRolloutEngine, ProgressiveRolloutError
        engine = ProgressiveRolloutEngine()
        with pytest.raises(ProgressiveRolloutError, match="Target stage is required"):
            engine.request_progression(reviewer="admin", reason="test", target_stage="")

    def test_invalid_transition_blocked(self):
        from live.progressive_rollout import ProgressiveRolloutEngine, ProgressiveRolloutError
        engine = ProgressiveRolloutEngine()
        with pytest.raises(ProgressiveRolloutError, match="Cannot transition"):
            engine.request_progression(reviewer="admin", reason="test", target_stage="canary_3")

    def test_approve_requires_reviewer(self):
        from live.progressive_rollout import ProgressiveRolloutEngine, ProgressiveRolloutError
        engine = ProgressiveRolloutEngine()
        with pytest.raises(ProgressiveRolloutError, match="Reviewer identity is required"):
            engine.approve_progression(reviewer="", review_note="ok", target_stage="canary_1")

    def test_approve_requires_note(self):
        from live.progressive_rollout import ProgressiveRolloutEngine, ProgressiveRolloutError
        engine = ProgressiveRolloutEngine()
        with pytest.raises(ProgressiveRolloutError, match="Review note is required"):
            engine.approve_progression(reviewer="admin", review_note="", target_stage="canary_1")

    def test_request_then_approve(self):
        from live.progressive_rollout import ProgressiveRolloutEngine
        from live.rollout_stages import RolloutStage
        engine = ProgressiveRolloutEngine()
        engine.request_progression(reviewer="admin", reason="Starting",
                                    target_stage=RolloutStage.CANARY_1)
        engine.approve_progression(rollout_id="", reviewer="admin",
                                    review_note="Approved", target_stage=RolloutStage.CANARY_1)
        status = engine.get_status()
        assert status["current_stage"] == "canary_1"

    def test_reject_progression(self):
        from live.progressive_rollout import ProgressiveRolloutEngine
        engine = ProgressiveRolloutEngine()
        engine.request_progression(reviewer="admin", reason="Test", target_stage="canary_1")
        engine.reject_progression(rollout_id="", reviewer="admin", reason="Not ready")
        status = engine.get_status()
        assert status["current_stage"] == "locked"

    def test_rollback_execution(self):
        from live.progressive_rollout import ProgressiveRolloutEngine
        from live.rollout_stages import RolloutStage
        engine = ProgressiveRolloutEngine()
        # First advance to canary_1
        engine.request_progression(reviewer="admin", reason="Test",
                                    target_stage=RolloutStage.CANARY_1)
        engine.approve_progression(rollout_id="", reviewer="admin",
                                    review_note="ok", target_stage=RolloutStage.CANARY_1)
        # Then execute rollback
        engine.execute_rollback(reason="Test failure")
        status = engine.get_status()
        assert status["current_stage"] == "rollback"

    def test_get_effective_limits(self):
        from live.progressive_rollout import ProgressiveRolloutEngine
        engine = ProgressiveRolloutEngine()
        limits = engine.get_effective_limits()
        assert "stage" in limits
        assert "max_trades" in limits

    def test_check_rollback_conditions(self):
        from live.progressive_rollout import ProgressiveRolloutEngine
        engine = ProgressiveRolloutEngine()
        result = engine.check_rollback_conditions()
        assert not result.rollback_required


# ═══════════════════════════════════════════════
# Eligibility Engine Tests
# ═══════════════════════════════════════════════

class TestRolloutEligibility:
    """Eligibility checks."""

    def test_eligibility_fails_without_deps(self):
        from live.rollout_eligibility import RolloutEligibilityEngine
        engine = RolloutEligibilityEngine()
        result = engine.check_eligibility(target_stage="canary_1")
        assert not result.eligible
        assert len(result.hard_blocks) > 0

    def test_eligibility_result_structure(self):
        from live.rollout_eligibility import EligibilityResult
        result = EligibilityResult(eligible=True, stage="canary_1", score=95.0)
        d = result.to_dict()
        assert d["eligible"] is True
        assert d["stage"] == "canary_1"


# ═══════════════════════════════════════════════
# Safety Regression Tests
# ═══════════════════════════════════════════════

class TestPhase49SafetyVerification:
    """Critical safety tests for Phase 49."""

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
        """Phase 49 API must not have unrestricted endpoints."""
        import backend.api.progressive_rollout as api_module
        routes = [r.path for r in api_module.router.routes]
        forbidden = ["enable-live", "start-auto-trading", "unlimited-live",
                     "disable-lock", "auto-arm"]
        for path in routes:
            for f in forbidden:
                assert f not in path, f"Route {path} contains '{f}'"

    def test_rollout_engine_no_enable_live(self):
        from live.progressive_rollout import ProgressiveRolloutEngine
        engine = ProgressiveRolloutEngine()
        methods = [m for m in dir(engine) if not m.startswith('_')]
        assert "enable_live" not in methods
        assert "start_auto_trading" not in methods

    def test_max_canary_sequence_3(self):
        from live.multi_canary import MAX_CANARY_SEQUENCE
        assert MAX_CANARY_SEQUENCE == 3

    def test_no_stage_has_100_percent_allocation(self):
        from live.rollout_stages import STAGE_RISK_LIMITS
        for stage, limits in STAGE_RISK_LIMITS.items():
            assert limits["risk_allocation_pct"] < 100, f"{stage} has 100% allocation"

    def test_all_previous_tests_importable(self):
        import tests.live.test_phase44_pre_live  # noqa
        import tests.live.test_phase45_live_activation  # noqa
        import tests.live.test_phase46_execution  # noqa
        import tests.live.test_phase47_canary  # noqa
        import tests.live.test_phase48_canary_evaluation  # noqa
