"""
Strategy Rule Evaluation Engine.

Parses strategy rules into an execution graph and evaluates conditions
against market data to produce entry/exit signals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RuleOperator(str, Enum):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class ComparisonOperator(str, Enum):
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    NEQ = "!="
    CROSS_ABOVE = "cross_above"
    CROSS_BELOW = "cross_below"


@dataclass
class Condition:
    id: str
    type: str
    operator: ComparisonOperator
    value: float | str | bool
    field: Optional[str] = None
    params: dict[str, Any] = dc_field(default_factory=dict)
    label: Optional[str] = None


@dataclass
class Rule:
    id: str
    label: str
    operator: RuleOperator
    conditions: list[Condition] = dc_field(default_factory=list)
    priority: int = 1


@dataclass
class EvaluationResult:
    triggered: bool
    rule_id: str
    rule_label: str
    conditions_results: list[dict[str, Any]] = dc_field(default_factory=list)
    score: float = 0.0


class ConditionEngine:
    """Evaluates individual conditions against market data."""

    @staticmethod
    def evaluate(condition: Condition, data: dict[str, float]) -> bool:
        val = data.get(condition.field or condition.type)
        if val is None:
            return False

        target = (
            condition.value
            if isinstance(condition.value, (int, float))
            else float(condition.value)
        )

        try:
            if condition.operator == ComparisonOperator.GT:
                return val > target
            elif condition.operator == ComparisonOperator.GTE:
                return val >= target
            elif condition.operator == ComparisonOperator.LT:
                return val < target
            elif condition.operator == ComparisonOperator.LTE:
                return val <= target
            elif condition.operator == ComparisonOperator.EQ:
                return abs(val - target) < 0.001
            elif condition.operator == ComparisonOperator.NEQ:
                return abs(val - target) >= 0.001
            elif condition.operator == ComparisonOperator.CROSS_ABOVE:
                prev = data.get(f"prev_{condition.field or condition.type}", 0)
                return prev <= target and val > target
            elif condition.operator == ComparisonOperator.CROSS_BELOW:
                prev = data.get(f"prev_{condition.field or condition.type}", 0)
                return prev >= target and val < target
        except (TypeError, ValueError):
            return False
        return False


class RuleEngine:
    """Evaluates rule groups with AND/OR/NOT logic."""

    def __init__(self):
        self._condition_engine = ConditionEngine()

    def evaluate_rule(self, rule: Rule, data: dict[str, float]) -> EvaluationResult:
        """Evaluate a single rule (AND/OR/NOT across conditions)."""
        if not rule.conditions:
            return EvaluationResult(
                triggered=False, rule_id=rule.id, rule_label=rule.label
            )

        results = []
        for cond in rule.conditions:
            result = self._condition_engine.evaluate(cond, data)
            results.append(
                {"condition_id": cond.id, "type": cond.type, "result": result}
            )

        if rule.operator == RuleOperator.AND:
            triggered = all(r["result"] for r in results)
        elif rule.operator == RuleOperator.OR:
            triggered = any(r["result"] for r in results)
        elif rule.operator == RuleOperator.NOT:
            triggered = not all(r["result"] for r in results)
        else:
            triggered = False

        score = (
            sum(1 for r in results if r["result"]) / len(results) * 100
            if results
            else 0
        )

        return EvaluationResult(
            triggered=triggered,
            rule_id=rule.id,
            rule_label=rule.label,
            conditions_results=results,
            score=score,
        )

    def evaluate_rules(
        self, rules: list[Rule], data: dict[str, float]
    ) -> list[EvaluationResult]:
        """Evaluate all rules sorted by priority."""
        sorted_rules = sorted(rules, key=lambda r: r.priority)
        return [self.evaluate_rule(r, data) for r in sorted_rules]


class StrategyEvaluator:
    """
    Complete strategy evaluation engine.

    1. Evaluates entry rules
    2. Evaluates exit rules
    3. Computes overall signal score
    4. Returns entry/exit signals
    """

    def __init__(self):
        self._rule_engine = RuleEngine()

    def evaluate(
        self,
        entry_rules: list[dict],
        exit_rules: list[dict],
        market_data: dict[str, float],
    ) -> dict[str, Any]:
        """Evaluate a strategy against market data and return signals."""
        entry_results = self._rule_engine.evaluate_rules(
            [self._dict_to_rule(r) for r in entry_rules], market_data
        )
        exit_results = self._rule_engine.evaluate_rules(
            [self._dict_to_rule(r) for r in exit_rules], market_data
        )

        entry_signal = any(r.triggered for r in entry_results)
        exit_signal = any(r.triggered for r in exit_results)

        entry_score = (
            sum(r.score for r in entry_results) / len(entry_results)
            if entry_results
            else 0
        )
        exit_score = (
            sum(r.score for r in exit_results) / len(exit_results)
            if exit_results
            else 0
        )

        return {
            "entry_signal": entry_signal,
            "exit_signal": exit_signal,
            "entry_score": round(entry_score, 2),
            "exit_score": round(exit_score, 2),
            "entry_rules": [
                {"label": r.rule_label, "triggered": r.triggered, "score": r.score}
                for r in entry_results
            ],
            "exit_rules": [
                {"label": r.rule_label, "triggered": r.triggered, "score": r.score}
                for r in exit_results
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def validate_rules(rules: list[dict]) -> list[str]:
        """Validate strategy rules for correctness."""
        errors = []
        seen_ids = set()
        for i, rule in enumerate(rules):
            rid = rule.get("id", f"rule_{i}")
            if rid in seen_ids:
                errors.append(f"Duplicate rule id: {rid}")
            seen_ids.add(rid)

            if rule.get("operator") not in ("AND", "OR", "NOT"):
                errors.append(f"Rule {rid}: Invalid operator")

            conditions = rule.get("conditions", [])
            if not conditions:
                errors.append(f"Rule {rid}: No conditions")

            for j, cond in enumerate(conditions):
                if not cond.get("type"):
                    errors.append(f"Rule {rid}, condition {j}: No type")
                if cond.get("operator") not in (
                    ">",
                    ">=",
                    "<",
                    "<=",
                    "==",
                    "!=",
                    "cross_above",
                    "cross_below",
                ):
                    errors.append(f"Rule {rid}, condition {j}: Invalid operator")

        return errors

    @staticmethod
    def _dict_to_rule(d: dict) -> Rule:
        return Rule(
            id=d.get("id", ""),
            label=d.get("label", ""),
            operator=RuleOperator(d.get("operator", "AND")),
            conditions=[Condition(**c) for c in d.get("conditions", [])],
            priority=d.get("priority", 1),
        )
