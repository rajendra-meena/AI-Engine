"""
Lot Sizer — calculates position size in lots from risk budget.
"""

from __future__ import annotations

from typing import Any


class LotSizer:
    """Calculate position size in lots based on risk budget."""

    @staticmethod
    def compute(
        capital: float,
        risk_percent: float,
        premium_entry: float,
        premium_sl: float,
        lot_size: int,
        min_lots: int = 1,
        max_lots: int = 10,
    ) -> dict[str, Any]:
        """
        Compute position size in lots.

        Formula:
          risk_amount = capital * (risk_percent / 100)
          premium_risk = abs(premium_entry - premium_sl)
          risk_per_lot = premium_risk * lot_size
          max_lots_by_risk = int(risk_amount / risk_per_lot) if risk_per_lot > 0 else 0
          lots = clamp(max_lots_by_risk, min_lots, max_lots)

        Returns dict with lots, total_cost, capital_required, risk_per_lot.
        """
        risk_amount = capital * (risk_percent / 100)
        premium_risk = abs(premium_entry - premium_sl) if premium_sl else premium_entry * 0.5
        risk_per_lot = premium_risk * lot_size if lot_size > 0 else 1

        if risk_per_lot > 0:
            raw_lots = int(risk_amount / risk_per_lot)
        else:
            raw_lots = 1

        lots = max(min_lots, min(raw_lots, max_lots))
        total_cost = premium_entry * lot_size * lots
        capital_required = total_cost

        return {
            "lots": lots,
            "total_cost": round(total_cost, 2),
            "capital_required": round(capital_required, 2),
            "risk_per_lot": round(risk_per_lot, 2),
            "risk_amount": round(risk_amount, 2),
            "premium_risk": round(premium_risk, 2),
        }