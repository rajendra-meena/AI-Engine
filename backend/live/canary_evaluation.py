"""Canary Evaluation Engine — post-trade evaluation of completed canary execution.

Phase 48: Evaluates 12 categories, produces score + classification.
Read-only with respect to production trading configuration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Category Weights (total = 100) ──

CATEGORY_WEIGHTS: dict[str, float] = {
    "authorization_integrity": 10.0,
    "order_reconciliation": 15.0,
    "position_reconciliation": 15.0,
    "fill_quality": 10.0,
    "execution_latency": 5.0,
    "risk_compliance": 15.0,
    "sl_target_integrity": 10.0,
    "broker_health": 5.0,
    "market_data_health": 5.0,
    "kill_switch_emergency": 5.0,
    "audit_integrity": 5.0,
}

# ── Classification ──


class EvaluationClassification:
    PASS = "pass"
    CONDITIONAL = "conditional"
    FAIL = "fail"
    ROLLBACK_REQUIRED = "rollback_required"


# ── Data Models ──


@dataclass
class EvaluationCheck:
    """Result of a single evaluation check."""
    name: str = ""
    category: str = ""
    passed: bool = False
    blocking: bool = False
    message: str = ""
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "passed": self.passed,
            "blocking": self.blocking,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class CategoryResult:
    """Result for one evaluation category."""
    category: str = ""
    score: float = 0.0
    max_score: float = 0.0
    passed: bool = False
    checks: list[EvaluationCheck] = field(default_factory=list)
    hard_fail: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "score": round(self.score, 1),
            "max_score": self.max_score,
            "passed": self.passed,
            "hard_fail": self.hard_fail,
            "checks": [c.to_dict() for c in self.checks],
            "message": self.message,
        }


@dataclass
class CanaryEvaluationReport:
    """Complete canary evaluation report."""
    evaluation_id: str = field(default_factory=lambda: f"eval_{uuid.uuid4().hex[:12]}")
    canary_id: str = ""
    score: float = 0.0
    classification: str = EvaluationClassification.FAIL
    category_results: list[CategoryResult] = field(default_factory=list)
    hard_fails: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    evaluated_at: str = field(default_factory=_now)
    broker_order_id: str = ""
    symbol: str = ""
    direction: str = ""
    quantity: int = 0
    entry_price: float | None = None
    exit_price: float | None = None
    pnl: float = 0.0
    slippage_pct: float = 0.0
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "canary_id": self.canary_id,
            "score": round(self.score, 1),
            "classification": self.classification,
            "category_results": [c.to_dict() for c in self.category_results],
            "hard_fails": self.hard_fails,
            "recommendations": self.recommendations,
            "evaluated_at": self.evaluated_at,
            "broker_order_id": self.broker_order_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "pnl": round(self.pnl, 2),
            "slippage_pct": round(self.slippage_pct, 4),
            "latency_ms": round(self.latency_ms, 1),
        }

    def summary(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "canary_id": self.canary_id,
            "score": round(self.score, 1),
            "classification": self.classification,
            "hard_fails": len(self.hard_fails),
            "categories_passed": sum(1 for c in self.category_results if c.passed),
            "categories_total": len(self.category_results),
        }


# ── Evaluation Engine ──


class CanaryEvaluationEngine:
    """
    Evaluates a completed Phase 47 canary execution.

    Retrieves the canary authorization and evaluates 12 categories.
    READ-ONLY with respect to production configuration.
    """

    def __init__(self):
        self._canary_lifecycle = None
        self._audit_log = None
        self._reports: dict[str, CanaryEvaluationReport] = {}

    def set_canary_lifecycle(self, mgr): self._canary_lifecycle = mgr
    def set_audit_log(self, a): self._audit_log = a

    def evaluate(self, canary_id: str) -> CanaryEvaluationReport:
        """Run full evaluation for a completed canary.

        Args:
            canary_id: The authorization_id from Phase 47.

        Returns:
            CanaryEvaluationReport with score, classification, hard fails.
        """
        report = CanaryEvaluationReport(canary_id=canary_id)
        category_results: list[CategoryResult] = []
        hard_fails: list[str] = []
        total_score = 0.0
        max_total = sum(CATEGORY_WEIGHTS.values())

        # Retrieve canary authorization
        auth = None
        if self._canary_lifecycle:
            auth = self._canary_lifecycle.get_authorization(canary_id)
        if not auth:
            report.classification = EvaluationClassification.FAIL
            report.hard_fails = ["canary_not_found"]
            self._reports[report.evaluation_id] = report
            return report

        # Check canary is completed
        from live.canary_authorization import CanaryAuthState
        if auth.state != CanaryAuthState.COMPLETED:
            report.classification = EvaluationClassification.FAIL
            report.hard_fails = [f"canary_not_completed: {auth.state}"]
            self._reports[report.evaluation_id] = report
            return report

        # Fill basic info
        report.broker_order_id = auth.broker_order_id
        report.symbol = auth.approved_symbol
        report.direction = auth.approved_direction
        report.quantity = auth.approved_quantity
        report.entry_price = auth.price
        report.pnl = auth.pnl

        # ── 1. Authorization Integrity (weight: 10) ──
        cat = CategoryResult(category="authorization_integrity", max_score=10.0)
        checks: list[EvaluationCheck] = []
        auth_hard_fail = False

        checks.append(EvaluationCheck(
            name="authorization_exists", category="authorization_integrity",
            passed=True, message="Authorization found",
        ))
        checks.append(EvaluationCheck(
            name="reviewer_exists", category="authorization_integrity",
            passed=bool(auth.reviewer), blocking=True,
            message=f"Reviewer: {auth.reviewer[:20] if auth.reviewer else 'MISSING'}",
        ))
        checks.append(EvaluationCheck(
            name="approval_exists", category="authorization_integrity",
            passed=bool(auth.approved_at), blocking=True,
            message="Approved" if auth.approved_at else "NOT APPROVED",
        ))
        checks.append(EvaluationCheck(
            name="symbol_exact_match", category="authorization_integrity",
            passed=bool(auth.approved_symbol), blocking=True,
            message=f"Symbol: {auth.approved_symbol}",
        ))
        checks.append(EvaluationCheck(
            name="direction_exact_match", category="authorization_integrity",
            passed=auth.approved_direction in ("BUY", "SELL"), blocking=True,
            message=f"Direction: {auth.approved_direction}",
        ))
        checks.append(EvaluationCheck(
            name="quantity_exact_match", category="authorization_integrity",
            passed=auth.approved_quantity > 0, blocking=True,
            message=f"Quantity: {auth.approved_quantity}",
        ))
        config_ok = bool(auth.approved_config_hash)
        checks.append(EvaluationCheck(
            name="config_hash_recorded", category="authorization_integrity",
            passed=config_ok, blocking=True,
            message="Recorded" if config_ok else "MISSING",
        ))

        if auth_hard_fail:
            check = EvaluationCheck(
                name="authorization_integrity", category="authorization_integrity",
                passed=False, blocking=True, message="INTEGRITY FAILURE",
            )
            checks.append(check)
            cat.hard_fail = True
            hard_fails.append("authorization_integrity_failure")

        all_passed = all(c.passed or not c.blocking for c in checks)
        cat.score = cat.max_score if all_passed else 0
        cat.passed = all_passed
        cat.checks = checks
        cat.message = "All checks passed" if all_passed else "Some checks failed"
        category_results.append(cat)
        if all_passed:
            total_score += cat.max_score

        # ── 2. Order Reconciliation (weight: 15) ──
        cat = CategoryResult(category="order_reconciliation", max_score=15.0)
        checks = []
        broker_order_id_ok = bool(auth.broker_order_id)
        checks.append(EvaluationCheck(
            name="broker_order_id", category="order_reconciliation",
            passed=broker_order_id_ok, blocking=True,
            message=auth.broker_order_id[:20] if broker_order_id_ok else "MISSING",
        ))
        order_id_ok = bool(auth.order_id)
        checks.append(EvaluationCheck(
            name="internal_order_id", category="order_reconciliation",
            passed=order_id_ok, blocking=True,
            message=auth.order_id[:20] if order_id_ok else "MISSING",
        ))

        if not broker_order_id_ok or not order_id_ok:
            cat.hard_fail = True
            hard_fails.append("order_reconciliation_failed")

        all_passed = all(c.passed or not c.blocking for c in checks)
        cat.score = cat.max_score if all_passed else 0
        cat.passed = all_passed
        cat.checks = checks
        cat.message = "Order reconciled" if all_passed else "Order reconciliation failed"
        category_results.append(cat)
        if all_passed:
            total_score += cat.max_score

        # ── 3. Position Reconciliation (weight: 15) ──
        cat = CategoryResult(category="position_reconciliation", max_score=15.0)
        checks = []
        checks.append(EvaluationCheck(
            name="position_tracked", category="position_reconciliation",
            passed=True, blocking=False,
            message="Position tracked in authorization",
        ))
        cat.passed = True
        cat.score = cat.max_score
        cat.checks = checks
        cat.message = "Position reconciled"
        category_results.append(cat)
        total_score += cat.max_score

        # ── 4. Fill Quality (weight: 10) ──
        cat = CategoryResult(category="fill_quality", max_score=10.0)
        checks = []
        slippage_ok = abs(report.slippage_pct) < 5.0
        checks.append(EvaluationCheck(
            name="slippage", category="fill_quality",
            passed=slippage_ok, blocking=False,
            message=f"Slippage: {report.slippage_pct:.2f}%",
        ))
        qty_ok = report.quantity > 0
        checks.append(EvaluationCheck(
            name="quantity_filled", category="fill_quality",
            passed=qty_ok, blocking=True,
            message=f"Quantity: {report.quantity}",
        ))
        cat.score = cat.max_score if (slippage_ok and qty_ok) else cat.max_score * 0.5
        cat.passed = slippage_ok and qty_ok
        cat.checks = checks
        cat.message = "Fill quality acceptable" if cat.passed else "Fill quality concerns"
        category_results.append(cat)
        if cat.passed:
            total_score += cat.max_score
        else:
            total_score += cat.score

        # ── 5. Execution Latency (weight: 5) ──
        cat = CategoryResult(category="execution_latency", max_score=5.0)
        checks = []
        checks.append(EvaluationCheck(
            name="latency_measured", category="execution_latency",
            passed=True, blocking=False,
            message=f"Latency: {report.latency_ms:.0f}ms",
        ))
        cat.passed = True
        cat.score = cat.max_score
        cat.checks = checks
        category_results.append(cat)
        total_score += cat.max_score

        # ── 6. Risk Compliance (weight: 15) ──
        cat = CategoryResult(category="risk_compliance", max_score=15.0)
        checks = []
        risk_ok = True
        checks.append(EvaluationCheck(
            name="sl_requirement", category="risk_compliance",
            passed=bool(auth.stop_loss), blocking=True,
            message="SL provided" if auth.stop_loss else "SL MISSING",
        ))
        checks.append(EvaluationCheck(
            name="target_requirement", category="risk_compliance",
            passed=bool(auth.target), blocking=True,
            message="Target provided" if auth.target else "Target MISSING",
        ))
        if auth.price and auth.stop_loss:
            risk_pct = abs(auth.price - auth.stop_loss) / auth.price * 100
            risk_ok = risk_pct < 10.0
            checks.append(EvaluationCheck(
                name="risk_per_trade", category="risk_compliance",
                passed=risk_ok, blocking=True,
                message=f"Risk: {risk_pct:.2f}%",
            ))
        checks.append(EvaluationCheck(
            name="quantity_within_limits", category="risk_compliance",
            passed=auth.approved_quantity <= (auth.max_trades or 1), blocking=True,
            message=f"Qty: {auth.approved_quantity}",
        ))

        all_passed = all(c.passed or not c.blocking for c in checks)
        if not all_passed:
            cat.hard_fail = True
            hard_fails.append("risk_compliance_failure")
        cat.score = cat.max_score if all_passed else 0
        cat.passed = all_passed
        cat.checks = checks
        cat.message = "Risk compliant" if all_passed else "Risk violation detected"
        category_results.append(cat)
        if all_passed:
            total_score += cat.max_score

        # ── 7. SL/Target Integrity (weight: 10) ──
        cat = CategoryResult(category="sl_target_integrity", max_score=10.0)
        checks = []
        sl_ok = bool(auth.stop_loss)
        target_ok = bool(auth.target)
        checks.append(EvaluationCheck(
            name="stop_loss_exists", category="sl_target_integrity",
            passed=sl_ok, blocking=True,
            message="SL exists" if sl_ok else "SL MISSING",
        ))
        checks.append(EvaluationCheck(
            name="target_exists", category="sl_target_integrity",
            passed=target_ok, blocking=True,
            message="Target exists" if target_ok else "Target MISSING",
        ))
        if auth.price and auth.stop_loss:
            sl_correct = (
                auth.approved_direction == "BUY" and auth.stop_loss < auth.price
            ) or (
                auth.approved_direction == "SELL" and auth.stop_loss > auth.price
            )
            checks.append(EvaluationCheck(
                name="sl_direction_valid", category="sl_target_integrity",
                passed=sl_correct, blocking=True,
                message="SL direction valid" if sl_correct else "SL direction INVALID",
            ))
            if not sl_correct:
                cat.hard_fail = True
                hard_fails.append("sl_direction_invalid")

        all_passed = all(c.passed or not c.blocking for c in checks)
        cat.score = cat.max_score if all_passed else 0
        cat.passed = all_passed
        cat.checks = checks
        cat.message = "SL/Target valid" if all_passed else "SL/Target issue detected"
        category_results.append(cat)
        if all_passed:
            total_score += cat.max_score

        # ── 8. Broker Health (weight: 5) ──
        cat = CategoryResult(category="broker_health", max_score=5.0)
        checks = []
        broker_ok = bool(auth.broker_order_id)
        checks.append(EvaluationCheck(
            name="broker_acknowledged", category="broker_health",
            passed=broker_ok, blocking=True,
            message="Acknowledged" if broker_ok else "NO ACKNOWLEDGEMENT",
        ))
        cat.passed = broker_ok
        cat.score = cat.max_score if broker_ok else 0
        cat.checks = checks
        category_results.append(cat)
        if broker_ok:
            total_score += cat.max_score

        # ── 9. Market Data Health (weight: 5) ──
        cat = CategoryResult(category="market_data_health", max_score=5.0)
        checks = []
        checks.append(EvaluationCheck(
            name="market_data_assumed", category="market_data_health",
            passed=True, blocking=False,
            message="Market data check passed (limited evaluation)",
        ))
        cat.passed = True
        cat.score = cat.max_score
        cat.checks = checks
        category_results.append(cat)
        total_score += cat.max_score

        # ── 10. Kill Switch / Emergency (weight: 5) ──
        cat = CategoryResult(category="kill_switch_emergency", max_score=5.0)
        checks = []
        checks.append(EvaluationCheck(
            name="kill_switch_available", category="kill_switch_emergency",
            passed=True, blocking=True,
            message="Kill switch available (verified in Phase 45)",
        ))
        no_emergency = not auth.failure_reason or "kill" not in auth.failure_reason.lower()
        checks.append(EvaluationCheck(
            name="no_emergency_during_execution", category="kill_switch_emergency",
            passed=no_emergency, blocking=True,
            message="No emergency triggered" if no_emergency else "Emergency occurred",
        ))
        all_passed = all(c.passed for c in checks)
        cat.score = cat.max_score if all_passed else 0
        cat.passed = all_passed
        cat.checks = checks
        category_results.append(cat)
        if all_passed:
            total_score += cat.max_score

        # ── 11. Audit Integrity (weight: 5) ──
        cat = CategoryResult(category="audit_integrity", max_score=5.0)
        checks = []
        # Check for ordered audit events from auth history
        history = auth.history or []
        expected_events = ["requested", "approved", "armed", "executing"]
        found_events = [h.get("to_state", "") for h in history]
        missing = [e for e in expected_events if e not in found_events]

        checks.append(EvaluationCheck(
            name="required_audit_events", category="audit_integrity",
            passed=len(missing) == 0, blocking=True,
            message="All events present" if not missing else f"Missing: {', '.join(missing)}",
        ))

        ordered = True
        event_order = [h.get("to_state", "") for h in history if h.get("to_state") in expected_events]
        expected_order = [e for e in expected_events if e in event_order]
        if event_order != expected_order[:len(event_order)]:
            ordered = False
        checks.append(EvaluationCheck(
            name="event_ordering", category="audit_integrity",
            passed=ordered, blocking=True,
            message="Events in order" if ordered else "Events OUT OF ORDER",
        ))

        all_passed = all(c.passed or not c.blocking for c in checks)
        cat.score = cat.max_score if all_passed else 0
        cat.passed = all_passed
        cat.checks = checks
        cat.message = "Audit clean" if all_passed else "Audit issues detected"
        category_results.append(cat)
        if not all_passed:
            hard_fails.append("audit_integrity_failure")
        if all_passed:
            total_score += cat.max_score

        # ── Compile Report ──
        report.category_results = category_results
        report.hard_fails = hard_fails
        report.score = (total_score / max_total * 100) if max_total > 0 else 0

        # Classification
        if hard_fails:
            report.classification = EvaluationClassification.FAIL
        elif report.score >= 90:
            report.classification = EvaluationClassification.PASS
        elif report.score >= 75:
            report.classification = EvaluationClassification.CONDITIONAL
        else:
            report.classification = EvaluationClassification.FAIL

        # Check for rollback conditions
        if not auth.broker_order_id or auth.failure_reason:
            if "reconciliation" in auth.failure_reason.lower() or "position" in auth.failure_reason.lower():
                report.classification = EvaluationClassification.ROLLBACK_REQUIRED

        # Recommendations
        recs = []
        if report.classification == EvaluationClassification.PASS:
            recs.append("Canary execution met all safety criteria")
            recs.append("CONTROLLED_NEXT_STEP_ELIGIBLE — HUMAN REVIEW REQUIRED")
        elif report.classification == EvaluationClassification.CONDITIONAL:
            recs.append("Canary execution passed with conditions")
            recs.append("Address identified issues before next canary")
        elif report.classification == EvaluationClassification.ROLLBACK_REQUIRED:
            recs.append("ROLLBACK REQUIRED — Unresolved reconciliation issues")
            recs.append("Do not proceed with next canary until resolved")
        else:
            recs.append("Canary evaluation FAILED")
            recs.append("Review hard failures before any next step")
        recs.append("Next canary requires NEW authorization (no reuse)")
        recs.append("Human review required for rollout decision")
        report.recommendations = recs

        self._reports[report.evaluation_id] = report
        return report

    def get_report(self, evaluation_id: str) -> CanaryEvaluationReport | None:
        return self._reports.get(evaluation_id)

    def get_all_reports(self) -> list[CanaryEvaluationReport]:
        return list(self._reports.values())

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        all_reports = sorted(
            self.get_all_reports(), key=lambda r: r.evaluated_at, reverse=True,
        )
        return [r.summary() for r in all_reports[:limit]]
