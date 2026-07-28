"""
Option Risk Engine — validates option-buying trades using premium-based calculations.

For a long option purchase:
  premium_cost = premium_entry × lot_size × lots
  risk_per_lot = (premium_entry - premium_sl) × lot_size
  total_trade_risk = risk_per_lot × lots
  maximum_allowed_risk = paper_capital × risk_percent
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from execution.options.models import OptionExecutionPlan
from api.auto_trade_settings import AutoTradeSettings


@dataclass
class OptionRiskResult:
    passed: bool = False
    execution_permitted: bool = False
    risk_score: float = 0.0
    risk_grade: str = "LOW"
    rejected_by: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "execution_permitted": self.execution_permitted,
            "risk_score": self.risk_score,
            "risk_grade": self.risk_grade,
            "rejected_by": self.rejected_by,
            "details": self.details,
        }


class OptionRiskEngine:
    """Validate an option buying plan against settings, capital and risk limits."""

    def __init__(self, capital: float = 100000.0, risk_percent: float = 2.0):
        self._capital = capital
        self._risk_percent = risk_percent
        self._daily_trades = 0
        self._open_positions = 0
        self._max_open_positions = 10
        self._settings = AutoTradeSettings()

    def set_daily_trades(self, count: int):
        self._daily_trades = count

    def set_open_positions(self, count: int):
        self._open_positions = count

    def set_max_open_positions(self, count: int):
        self._max_open_positions = count

    def set_settings(self, settings: AutoTradeSettings):
        self._settings = settings

    def validate(self, plan: OptionExecutionPlan) -> OptionRiskResult:
        """Validate an option buying plan against all checks."""
        rejected_by: list[str] = []
        details: dict[str, Any] = {}
        risk_score = 0.0

        quantity = plan.lot_size * plan.lots
        premium_cost = plan.premium * quantity
        risk_per_unit = plan.premium_entry - plan.premium_sl
        risk_per_lot = risk_per_unit * plan.lot_size
        total_trade_risk = risk_per_lot * plan.lots
        max_allowed_risk = self._capital * (self._risk_percent / 100)
        reward_per_unit = plan.premium_target - plan.premium_entry
        rr = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0

        details.update({
            "quantity": quantity,
            "premium_cost": round(premium_cost, 2),
            "risk_per_unit": risk_per_unit,
            "risk_per_lot": risk_per_lot,
            "total_trade_risk": round(total_trade_risk, 2),
            "max_allowed_risk": round(max_allowed_risk, 2),
            "capital": self._capital,
            "risk_reward": round(rr, 2),
        })

        # 1. Lots range
        if not (1 <= plan.lots <= 20):
            rejected_by.append(f"lots={plan.lots} not in 1-20")
            risk_score += 25

        # 2. Premium SL geometry
        if plan.premium_sl >= plan.premium_entry:
            rejected_by.append(f"premium_sl={plan.premium_sl} >= premium_entry={plan.premium_entry}")
            risk_score += 25

        # 3. Premium target geometry
        if plan.premium_target <= plan.premium_entry:
            rejected_by.append(f"premium_target={plan.premium_target} <= premium_entry={plan.premium_entry}")
            risk_score += 25

        # 4. Capital check: premium_cost <= available_cash
        if premium_cost > self._capital:
            rejected_by.append(f"premium_cost={premium_cost:.2f} > available_cash={self._capital:.2f}")
            risk_score += 25

        # 5. Risk check: total_trade_risk <= max_allowed_risk
        if total_trade_risk > max_allowed_risk:
            rejected_by.append(
                f"total_trade_risk={total_trade_risk:.2f} > max_allowed_risk={max_allowed_risk:.2f}"
            )
            risk_score += 25

        # 6. Risk/reward
        if rr < self._settings.min_risk_reward:
            rejected_by.append(f"risk_reward={rr:.2f} < min={self._settings.min_risk_reward}")
            risk_score += 10

        # 7. Daily trades
        if self._daily_trades >= self._settings.max_trades_per_day:
            rejected_by.append(f"daily_trades={self._daily_trades} >= max={self._settings.max_trades_per_day}")
            risk_score += 20

        # 8. Concurrent positions
        if self._open_positions >= self._max_open_positions:
            rejected_by.append(f"open_positions={self._open_positions} >= max={self._max_open_positions}")
            risk_score += 20

        # 9. Direction
        if plan.direction == "LONG" and not self._settings.allow_buy_trades:
            rejected_by.append("BUY_TRADES_DISABLED")
            risk_score += 25
        if plan.direction == "SHORT" and not self._settings.allow_sell_trades:
            rejected_by.append("SELL_TRADES_DISABLED")
            risk_score += 25

        # 10. Selected lots vs affordability
        max_affordable_lots = int(max_allowed_risk / risk_per_lot) if risk_per_lot > 0 else 0
        if plan.lots > max_affordable_lots and max_affordable_lots > 0:
            rejected_by.append(
                f"SELECTED_LOTS_EXCEED_RISK_CAPACITY: selected={plan.lots}, affordable={max_affordable_lots}"
            )
            risk_score += 15
            details["max_affordable_lots"] = max_affordable_lots

        details["max_affordable_lots"] = max_affordable_lots

        # Grade
        if risk_score >= 75:
            risk_grade = "CRITICAL"
        elif risk_score >= 50:
            risk_grade = "HIGH"
        elif risk_score >= 25:
            risk_grade = "MEDIUM"
        else:
            risk_grade = "LOW"

        passed = len(rejected_by) == 0
        return OptionRiskResult(
            passed=passed,
            execution_permitted=passed,
            risk_score=min(risk_score, 100),
            risk_grade=risk_grade,
            rejected_by=rejected_by,
            details=details,
        )