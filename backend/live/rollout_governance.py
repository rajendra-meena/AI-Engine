"""Rollout Governance Engine — evaluation-driven rollout decision framework.

Phase 48: Determines controlled next-step eligibility after canary evaluation.
Never enables unrestricted live trading.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from live.rollout_models import (
    RolloutGovernanceReport, RolloutGovernanceState,
    HumanReviewDecision, MultiCanaryTracker,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RolloutGovernanceEngine:
    """
    Evaluates rollout eligibility after a canary evaluation.

    Rules:
    - PASS does NOT enable live trading
    - Next trade requires NEW authorization (no reuse)
    - Human review required for every canary
    - Reviewer + note required for every decision
    - Profitability alone never unlocks live execution
    """

    def __init__(self):
        self._evaluation_engine = None
        self._reports: dict[str, RolloutGovernanceReport] = {}
        self._tracker = MultiCanaryTracker()

    def set_evaluation_engine(self, engine):
        self._evaluation_engine = engine

    def evaluate_rollout_eligibility(
        self, evaluation_id: str,
    ) -> RolloutGovernanceReport:
        """Evaluate rollout eligibility from a canary evaluation.

        Args:
            evaluation_id: The ID from CanaryEvaluationReport.

        Returns:
            RolloutGovernanceReport with state and recommendations.
        """
        gov = RolloutGovernanceReport(evaluation_id=evaluation_id)

        # Retrieve evaluation
        evaluation = None
        if self._evaluation_engine:
            evaluation = self._evaluation_engine.get_report(evaluation_id)

        if not evaluation:
            gov.state = RolloutGovernanceState.NOT_ELIGIBLE
            gov.recommendations = ["Evaluation not found — cannot determine eligibility"]
            self._reports[gov.governance_id] = gov
            return gov

        gov.canary_id = evaluation.canary_id
        classification = evaluation.classification
        hard_fails = evaluation.hard_fails or []
        score = evaluation.score

        # Determine state from classification
        if classification == "rollback_required":
            gov.state = RolloutGovernanceState.ROLLBACK_REQUIRED
            gov.recommendations = [
                "ROLLBACK REQUIRED — unresolved reconciliation or emergency issues",
                "Do not proceed with next canary until resolved",
                "Human intervention required",
            ]
        elif classification == "fail":
            gov.state = RolloutGovernanceState.NOT_ELIGIBLE
            gov.recommendations = [
                "Canary evaluation FAILED",
                f"Hard failures: {len(hard_fails)}",
                "Review all hard failures before any next step",
                "New authorization required for next canary",
            ]
        elif classification == "conditional":
            gov.state = RolloutGovernanceState.HUMAN_REVIEW_REQUIRED
            gov.recommendations = [
                "Canary passed with conditions (score: {:.1f})".format(score),
                "Address identified issues before next canary",
                "Human review required for rollout decision",
                "New authorization required for next canary",
            ]
        elif classification == "pass":
            gov.state = RolloutGovernanceState.HUMAN_REVIEW_REQUIRED
            gov.recommendations = [
                "Canary execution met all safety criteria (score: {:.1f})".format(score),
                "CONTROLLED_NEXT_STEP_ELIGIBLE pending human review",
                "Next canary requires NEW authorization",
                "New human approval required",
                "Fresh preflight required",
                "Current champion and config hash required",
                "Reconciliation step required",
            ]
        else:
            gov.state = RolloutGovernanceState.NOT_ELIGIBLE
            gov.recommendations = ["Unknown classification — cannot determine eligibility"]

        self._reports[gov.governance_id] = gov
        return gov

    def submit_human_review(
        self, evaluation_id: str, reviewer: str = "",
        review_note: str = "", decision: str = "",
    ) -> RolloutGovernanceReport:
        """Submit human review for a rollout governance report.

        Args:
            evaluation_id: The evaluation ID
            reviewer: Human identity
            review_note: Human review note
            decision: One of accept_canary, reject_canary, request_more_data, rollback

        Returns:
            Updated RolloutGovernanceReport
        """
        if not reviewer:
            raise ValueError("Reviewer identity is required")
        if not review_note:
            raise ValueError("Review note is required")
        if decision not in (HumanReviewDecision.ACCEPT_CANARY,
                            HumanReviewDecision.REJECT_CANARY,
                            HumanReviewDecision.REQUEST_MORE_DATA,
                            HumanReviewDecision.ROLLBACK):
            raise ValueError(f"Invalid decision: {decision}")

        # Find the governance report for this evaluation
        gov = None
        for g in self._reports.values():
            if g.evaluation_id == evaluation_id:
                gov = g
                break

        if not gov:
            # Create one if it doesn't exist
            evaluation = None
            if self._evaluation_engine:
                evaluation = self._evaluation_engine.get_report(evaluation_id)
            gov = RolloutGovernanceReport(evaluation_id=evaluation_id)
            if evaluation:
                gov.canary_id = evaluation.canary_id
            self._reports[gov.governance_id] = gov

        gov.reviewer = reviewer
        gov.review_note = review_note
        gov.decision = decision
        gov.reviewed_at = _now()

        # Update state based on decision
        if decision == HumanReviewDecision.ACCEPT_CANARY:
            gov.state = RolloutGovernanceState.CONTROLLED_NEXT_STEP_ELIGIBLE
            gov.recommendations = [
                "HUMAN REVIEW: Canary accepted",
                "CONTROLLED_NEXT_STEP_ELIGIBLE",
                "MAX_NEXT_CANARY_TRADES = 1",
                "REQUIRE_NEW_HUMAN_APPROVAL = true",
                "REQUIRE_FRESH_PREFLIGHT = true",
                "REQUIRE_CURRENT_CHAMPION = true",
                "REQUIRE_CURRENT_CONFIG_HASH = true",
                "REQUIRE_RECONCILIATION = true",
                "Unrestricted live trading remains DISABLED",
            ]
        elif decision == HumanReviewDecision.REJECT_CANARY:
            gov.state = RolloutGovernanceState.ROLLOUT_BLOCKED
            gov.recommendations = [
                "HUMAN REVIEW: Canary rejected",
                "Review rejection reasons before next attempt",
                "New authorization required for next canary",
            ]
        elif decision == HumanReviewDecision.REQUEST_MORE_DATA:
            gov.state = RolloutGovernanceState.HUMAN_REVIEW_REQUIRED
            gov.recommendations = [
                "HUMAN REVIEW: More data requested",
                "Additional evaluation or monitoring needed",
            ]
        elif decision == HumanReviewDecision.ROLLBACK:
            gov.state = RolloutGovernanceState.ROLLBACK_REQUIRED
            gov.recommendations = [
                "HUMAN REVIEW: Rollback requested",
                "Immediate reconciliation required",
                "Do not proceed with next canary",
            ]

        return gov

    def get_status(self, evaluation_id: str) -> dict[str, Any]:
        for gov in self._reports.values():
            if gov.evaluation_id == evaluation_id:
                return gov.to_dict()
        return {"state": "not_found", "evaluation_id": evaluation_id}

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        all_reports = sorted(
            self._reports.values(),
            key=lambda r: r.created_at, reverse=True,
        )
        return [r.summary() for r in all_reports[:limit]]

    def update_tracker_from_evaluation(self, evaluation: Any) -> None:
        """Update multi-canary tracker from an evaluation report."""
        self._tracker.total_canaries += 1
        if evaluation.classification == "pass":
            self._tracker.completed_canaries += 1
            if evaluation.pnl > 0:
                self._tracker.wins += 1
            else:
                self._tracker.losses += 1
        elif evaluation.classification == "fail":
            self._tracker.failed_canaries += 1

        self._tracker.cumulative_pnl += evaluation.pnl
        prev_slippage = self._tracker.avg_slippage_pct * (self._tracker.total_canaries - 1)
        self._tracker.avg_slippage_pct = (
            prev_slippage + abs(evaluation.slippage_pct)
        ) / self._tracker.total_canaries
        prev_latency = self._tracker.avg_latency_ms * (self._tracker.total_canaries - 1)
        self._tracker.avg_latency_ms = (
            prev_latency + evaluation.latency_ms
        ) / self._tracker.total_canaries

    def get_multi_canary_stats(self) -> dict[str, Any]:
        return self._tracker.to_dict()
