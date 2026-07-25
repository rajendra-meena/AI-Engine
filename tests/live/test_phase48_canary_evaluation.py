"""
Phase 48 — Controlled Canary Post-Trade Evaluation & Live Rollout Governance Tests.

Tests evaluation engine, rollout governance, and safety verification.
Critical: PHASE_43_LIVE_EXECUTION_LOCK remains TRUE.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta


# ═══════════════════════════════════════════════
# Evaluation Engine Tests
# ═══════════════════════════════════════════════

class TestCanaryEvaluationEngine:
    """Evaluation engine for completed canaries."""

    def test_evaluation_rejects_nonexistent_canary(self):
        from live.canary_evaluation import CanaryEvaluationEngine
        engine = CanaryEvaluationEngine()
        report = engine.evaluate("nonexistent_canary")
        assert report.classification == "fail"
        assert "canary_not_found" in report.hard_fails

    def test_evaluation_rejects_not_completed(self):
        from live.canary_evaluation import CanaryEvaluationEngine
        from live.canary_authorization import CanaryAuthorization, CanaryAuthState
        engine = CanaryEvaluationEngine()
        from live.canary_lifecycle import CanaryLifecycleManager
        lifecycle = CanaryLifecycleManager()
        auth = lifecycle.request(reviewer="admin", reason="Test", symbol="TCS", quantity=1)
        engine.set_canary_lifecycle(lifecycle)
        report = engine.evaluate(auth.authorization_id)
        assert report.classification == "fail"
        assert any("not_completed" in f for f in report.hard_fails)

    def test_evaluation_works_for_completed(self):
        from live.canary_evaluation import CanaryEvaluationEngine
        from live.canary_authorization import CanaryAuthorization, CanaryAuthState
        from live.canary_lifecycle import CanaryLifecycleManager
        lifecycle = CanaryLifecycleManager()
        auth = lifecycle.request(reviewer="admin", reason="Test", symbol="TCS",
                                  direction="BUY", quantity=1, price=100.0,
                                  stop_loss=99.0, target=102.0)
        lifecycle.approve(auth.authorization_id, reviewer="approver")
        lifecycle.arm(auth.authorization_id, reviewer="approver")
        auth.state = CanaryAuthState.COMPLETED
        auth.broker_order_id = "ZD123456"
        auth.order_id = "exec_123"

        engine = CanaryEvaluationEngine()
        engine.set_canary_lifecycle(lifecycle)
        report = engine.evaluate(auth.authorization_id)
        assert report.score >= 0
        assert len(report.category_results) == 11

    def test_category_weights_sum_to_100(self):
        from live.canary_evaluation import CATEGORY_WEIGHTS
        total = sum(CATEGORY_WEIGHTS.values())
        assert abs(total - 100.0) < 0.01

    def test_evaluation_report_structure(self):
        from live.canary_evaluation import CanaryEvaluationReport
        report = CanaryEvaluationReport(canary_id="test", score=85.0, classification="pass")
        d = report.to_dict()
        assert d["classification"] == "pass"
        assert d["canary_id"] == "test"

    def test_evaluation_summary(self):
        from live.canary_evaluation import CanaryEvaluationReport
        report = CanaryEvaluationReport(canary_id="test", score=92.0)
        s = report.summary()
        assert "evaluation_id" in s
        assert s["score"] == 92.0

    def test_evaluation_with_hard_fails(self):
        from live.canary_evaluation import CanaryEvaluationEngine
        from live.canary_lifecycle import CanaryLifecycleManager
        lifecycle = CanaryLifecycleManager()
        auth = lifecycle.request(reviewer="admin", reason="Test", symbol="TCS",
                                  direction="BUY", quantity=1, price=100.0,
                                  stop_loss=99.0, target=102.0)
        lifecycle.approve(auth.authorization_id, reviewer="approver")
        lifecycle.arm(auth.authorization_id, reviewer="approver")
        auth.state = "completed"
        auth.failure_reason = "position_mismatch: broker reconciliation required"

        engine = CanaryEvaluationEngine()
        engine.set_canary_lifecycle(lifecycle)
        report = engine.evaluate(auth.authorization_id)
        # Should detect position reconciliation issues
        assert len(report.category_results) > 0

    def test_evaluation_id_is_unique(self):
        from live.canary_evaluation import CanaryEvaluationEngine
        from live.canary_authorization import CanaryAuthState
        from live.canary_lifecycle import CanaryLifecycleManager
        lifecycle = CanaryLifecycleManager()
        auth1 = lifecycle.request(reviewer="a", reason="T1", symbol="TCS", quantity=1)
        auth1.state = CanaryAuthState.COMPLETED
        auth1.broker_order_id = "ZD1"
        auth1.order_id = "exec_1"
        auth2 = lifecycle.request(reviewer="a", reason="T2", symbol="TCS2", quantity=1)
        auth2.state = CanaryAuthState.COMPLETED
        auth2.broker_order_id = "ZD2"
        auth2.order_id = "exec_2"

        engine = CanaryEvaluationEngine()
        engine.set_canary_lifecycle(lifecycle)
        r1 = engine.evaluate(auth1.authorization_id)
        r2 = engine.evaluate(auth2.authorization_id)
        assert r1.evaluation_id != r2.evaluation_id


# ═══════════════════════════════════════════════
# Rollout Governance Tests
# ═══════════════════════════════════════════════

class TestRolloutGovernance:
    """Rollout governance engine."""

    def test_not_eligible_for_nonexistent_evaluation(self):
        from live.rollout_governance import RolloutGovernanceEngine
        engine = RolloutGovernanceEngine()
        report = engine.evaluate_rollout_eligibility("nonexistent")
        assert report.state == "not_eligible"

    def test_pass_evaluation_yields_human_review_required(self):
        from live.rollout_governance import RolloutGovernanceEngine
        from live.canary_evaluation import CanaryEvaluationEngine, CanaryEvaluationReport
        engine = RolloutGovernanceEngine()
        eval_engine = CanaryEvaluationEngine()
        engine.set_evaluation_engine(eval_engine)

        # Create a passing evaluation
        report = CanaryEvaluationReport(
            evaluation_id="eval_pass", canary_id="test",
            score=95.0, classification="pass", pnl=50.0,
        )
        # Store it
        eval_engine._reports["eval_pass"] = report

        gov = engine.evaluate_rollout_eligibility("eval_pass")
        # Should require human review, not auto-approve
        assert gov.state == "human_review_required"
        assert "CONTROLLED_NEXT_STEP" in gov.recommendations[1]

    def test_human_review_requires_reviewer(self):
        from live.rollout_governance import RolloutGovernanceEngine
        engine = RolloutGovernanceEngine()
        with pytest.raises(ValueError, match="Reviewer identity is required"):
            engine.submit_human_review("eval_id", reviewer="", review_note="", decision="accept_canary")

    def test_human_review_requires_note(self):
        from live.rollout_governance import RolloutGovernanceEngine
        engine = RolloutGovernanceEngine()
        with pytest.raises(ValueError, match="Review note is required"):
            engine.submit_human_review("eval_id", reviewer="admin", review_note="", decision="accept_canary")

    def test_human_review_requires_valid_decision(self):
        from live.rollout_governance import RolloutGovernanceEngine
        engine = RolloutGovernanceEngine()
        with pytest.raises(ValueError, match="Invalid decision"):
            engine.submit_human_review("eval_id", reviewer="admin", review_note="test", decision="invalid")

    def test_accept_canary_controlled_eligible(self):
        from live.rollout_governance import RolloutGovernanceEngine
        from live.canary_evaluation import CanaryEvaluationEngine, CanaryEvaluationReport
        engine = RolloutGovernanceEngine()
        eval_engine = CanaryEvaluationEngine()
        engine.set_evaluation_engine(eval_engine)

        report = CanaryEvaluationReport(
            evaluation_id="eval1", canary_id="test",
            score=95.0, classification="pass",
        )
        eval_engine._reports["eval1"] = report

        gov = engine.submit_human_review(
            "eval1", reviewer="admin", review_note="Canary looks good", decision="accept_canary",
        )
        assert gov.state == "controlled_next_step_eligible"
        assert "Unrestricted live trading remains DISABLED" in gov.recommendations

    def test_reject_canary_blocks_rollout(self):
        from live.rollout_governance import RolloutGovernanceEngine
        from live.canary_evaluation import CanaryEvaluationEngine, CanaryEvaluationReport
        engine = RolloutGovernanceEngine()
        eval_engine = CanaryEvaluationEngine()
        engine.set_evaluation_engine(eval_engine)

        report = CanaryEvaluationReport(
            evaluation_id="eval_rej", canary_id="test",
            score=60.0, classification="fail", hard_fails=["test_failure"],
        )
        eval_engine._reports["eval_rej"] = report

        gov = engine.submit_human_review(
            "eval_rej", reviewer="admin", review_note="Not ready", decision="reject_canary",
        )
        assert gov.state == "rollout_blocked"

    def test_rollback_required_state(self):
        from live.rollout_governance import RolloutGovernanceEngine
        from live.canary_evaluation import CanaryEvaluationEngine, CanaryEvaluationReport
        engine = RolloutGovernanceEngine()
        eval_engine = CanaryEvaluationEngine()
        engine.set_evaluation_engine(eval_engine)

        report = CanaryEvaluationReport(
            evaluation_id="eval_rb", canary_id="test",
            score=40.0, classification="rollback_required",
        )
        eval_engine._reports["eval_rb"] = report

        gov = engine.submit_human_review(
            "eval_rb", reviewer="admin", review_note="Rollback needed", decision="rollback",
        )
        assert gov.state == "rollback_required"

    def test_multi_canary_tracker(self):
        from live.rollout_governance import RolloutGovernanceEngine
        from live.canary_evaluation import CanaryEvaluationReport
        engine = RolloutGovernanceEngine()
        r1 = CanaryEvaluationReport(evaluation_id="e1", canary_id="c1",
                                      score=95, classification="pass", pnl=100.0)
        r2 = CanaryEvaluationReport(evaluation_id="e2", canary_id="c2",
                                      score=85, classification="pass", pnl=-50.0)
        engine.update_tracker_from_evaluation(r1)
        engine.update_tracker_from_evaluation(r2)
        stats = engine.get_multi_canary_stats()
        assert stats["total_canaries"] == 2
        assert stats["cumulative_pnl"] == 50.0  # 100 + (-50)

    def test_governance_report_structure(self):
        from live.rollout_models import RolloutGovernanceReport
        gov = RolloutGovernanceReport(evaluation_id="eval1", state="pass")
        d = gov.to_dict()
        assert d["governance_id"].startswith("gov_")
        assert d["state"] == "pass"

    def test_governance_states_defined(self):
        from live.rollout_models import RolloutGovernanceState
        assert hasattr(RolloutGovernanceState, 'NOT_ELIGIBLE')
        assert hasattr(RolloutGovernanceState, 'HUMAN_REVIEW_REQUIRED')
        assert hasattr(RolloutGovernanceState, 'CONTROLLED_NEXT_STEP_ELIGIBLE')
        assert hasattr(RolloutGovernanceState, 'ROLLBACK_REQUIRED')

    def test_human_review_decisions_defined(self):
        from live.rollout_models import HumanReviewDecision
        assert HumanReviewDecision.ACCEPT_CANARY == "accept_canary"
        assert HumanReviewDecision.ROLLBACK == "rollback"


# ═══════════════════════════════════════════════
# Safety & Regression Tests
# ═══════════════════════════════════════════════

class TestPhase48SafetyVerification:
    """Critical safety tests for Phase 48."""

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

    def test_evaluation_cannot_enable_live(self):
        """Evaluation engine must not have any live-enabling capability."""
        from live.canary_evaluation import CanaryEvaluationEngine
        engine = CanaryEvaluationEngine()
        # The engine should not have any method that enables execution
        method_names = [m for m in dir(engine) if not m.startswith('_')]
        forbidden = ['enable_live', 'activate', 'start_trading']
        for f in forbidden:
            assert f not in method_names, f"Engine has method: {f}"

    def test_governance_cannot_enable_live(self):
        """Governance engine must not have any live-enabling capability."""
        from live.rollout_governance import RolloutGovernanceEngine
        engine = RolloutGovernanceEngine()
        method_names = [m for m in dir(engine) if not m.startswith('_')]
        forbidden = ['enable_live', 'activate_live', 'start_trading']
        for f in forbidden:
            assert f not in method_names, f"Governance has method: {f}"

    def test_no_unrestricted_live_endpoint(self):
        """Phase 48 API must not have unrestricted endpoints."""
        import backend.api.canary_evaluation as api_module
        routes = [r.path for r in api_module.router.routes]
        forbidden = ["enable-live", "start-auto-trading", "unlimited-live",
                     "disable-lock", "auto-arm"]
        for path in routes:
            for f in forbidden:
                assert f not in path, f"Route {path} contains '{f}'"

    def test_score_cannot_override_hard_fail(self):
        """Evaluation with hard fails must not reach PASS."""
        from live.canary_evaluation import CanaryEvaluationEngine
        from live.canary_authorization import CanaryAuthState
        from live.canary_lifecycle import CanaryLifecycleManager
        lifecycle = CanaryLifecycleManager()
        auth = lifecycle.request(reviewer="admin", reason="Test", symbol="TCS",
                                  direction="BUY", quantity=1)
        auth.state = CanaryAuthState.COMPLETED
        # Force hard fail conditions - no broker_order_id, no order_id
        auth.broker_order_id = ""
        auth.order_id = ""

        engine = CanaryEvaluationEngine()
        engine.set_canary_lifecycle(lifecycle)
        report = engine.evaluate(auth.authorization_id)
        # Score cannot override hard fail
        assert report.classification in ("fail", "rollback_required")

    def test_all_previous_tests_importable(self):
        import tests.live.test_phase44_pre_live  # noqa
        import tests.live.test_phase45_live_activation  # noqa
        import tests.live.test_phase46_execution  # noqa
        import tests.live.test_phase47_canary  # noqa

    def test_next_trade_requires_new_authorization(self):
        """Governance must require new authorization for next trade."""
        from live.rollout_governance import RolloutGovernanceEngine
        from live.canary_evaluation import CanaryEvaluationEngine, CanaryEvaluationReport
        engine = RolloutGovernanceEngine()
        eval_engine = CanaryEvaluationEngine()
        engine.set_evaluation_engine(eval_engine)

        report = CanaryEvaluationReport(
            evaluation_id="eval_n1", canary_id="c1",
            score=95.0, classification="pass",
        )
        eval_engine._reports["eval_n1"] = report

        gov = engine.submit_human_review(
            "eval_n1", reviewer="admin", review_note="Approved",
            decision="accept_canary",
        )
        # Must recommend new authorization
        recs_text = " ".join(gov.recommendations)
        assert "REQUIRE_NEW_HUMAN_APPROVAL" in recs_text or "New authorization" in recs_text

    def test_rollout_model_to_dict(self):
        from live.rollout_models import RolloutGovernanceReport, MultiCanaryTracker
        gov = RolloutGovernanceReport(evaluation_id="e1", state="pass", reviewer="admin")
        d = gov.to_dict()
        assert d["reviewer"] == "admin"
        assert d["state"] == "pass"

        tracker = MultiCanaryTracker(total_canaries=3, cumulative_pnl=500.0)
        td = tracker.to_dict()
        assert td["total_canaries"] == 3
        assert td["cumulative_pnl"] == 500.0
