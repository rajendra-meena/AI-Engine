"""
Institutional Risk Firewall — Position Sizing

Multiple position sizing methods:
- Fixed Quantity
- Fixed Amount
- Fixed Risk (percent)
- ATR-based
- Kelly Criterion
- Volatility Adjusted
- Portfolio Risk Based
- Dynamic Capital Allocation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SizingResult:
    quantity: int = 0
    capital_used: float = 0.0
    risk_amount: float = 0.0
    risk_percent: float = 0.0
    margin_required: float = 0.0
    method: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "quantity": self.quantity,
            "capital_used": round(self.capital_used, 2),
            "risk_amount": round(self.risk_amount, 2),
            "risk_percent": round(self.risk_percent, 2),
            "margin_required": round(self.margin_required, 2),
            "method": self.method,
            "detail": self.detail,
        }


class PositionSizer:
    """Provides multiple position sizing strategies."""

    @staticmethod
    def fixed_quantity(
        quantity: int,
        price: float,
        capital: float,
    ) -> SizingResult:
        """Fixed number of shares/lots."""
        cost = quantity * price
        risk_pct = (cost / capital * 100) if capital > 0 else 0
        return SizingResult(
            quantity=quantity,
            capital_used=cost,
            risk_amount=cost,
            risk_percent=risk_pct,
            margin_required=cost,
            method="fixed_quantity",
        )

    @staticmethod
    def fixed_amount(
        amount: float,
        price: float,
        capital: float,
        lot_size: int = 1,
    ) -> SizingResult:
        """Fixed capital amount per trade."""
        raw_qty = amount / price
        qty = int(raw_qty / lot_size) * lot_size
        cost = qty * price
        risk_pct = (cost / capital * 100) if capital > 0 else 0
        return SizingResult(
            quantity=max(qty, lot_size),
            capital_used=cost,
            risk_amount=cost,
            risk_percent=risk_pct,
            margin_required=cost,
            method="fixed_amount",
            detail={"target_amount": amount},
        )

    @staticmethod
    def fixed_risk(
        capital: float,
        risk_percent: float,
        entry_price: float,
        stop_loss: float,
        lot_size: int = 1,
    ) -> SizingResult:
        """Risk a fixed percentage of capital."""
        risk_amount = capital * (risk_percent / 100)
        price_risk = abs(entry_price - stop_loss)
        if price_risk <= 0:
            return SizingResult(method="fixed_risk", detail={"error": "Invalid stop loss"})

        raw_qty = risk_amount / price_risk
        qty = int(raw_qty / lot_size) * lot_size
        cost = qty * entry_price
        actual_risk = qty * price_risk
        actual_risk_pct = (actual_risk / capital * 100) if capital > 0 else 0

        return SizingResult(
            quantity=max(qty, lot_size),
            capital_used=cost,
            risk_amount=actual_risk,
            risk_percent=actual_risk_pct,
            margin_required=cost,
            method="fixed_risk",
            detail={"risk_percent_target": risk_percent, "price_risk": price_risk},
        )

    @staticmethod
    def atr_based(
        capital: float,
        entry_price: float,
        atr_value: float,
        risk_percent: float = 2.0,
        atr_multiplier: float = 2.0,
        lot_size: int = 1,
    ) -> SizingResult:
        """Position size based on ATR volatility."""
        risk_amount = capital * (risk_percent / 100)
        price_risk = atr_value * atr_multiplier
        if price_risk <= 0:
            return SizingResult(method="atr_based", detail={"error": "Invalid ATR"})

        raw_qty = risk_amount / price_risk
        qty = int(raw_qty / lot_size) * lot_size
        cost = qty * entry_price
        stop_loss = entry_price - price_risk  # for long

        return SizingResult(
            quantity=max(qty, lot_size),
            capital_used=cost,
            risk_amount=qty * price_risk,
            risk_percent=(qty * price_risk / capital * 100) if capital > 0 else 0,
            margin_required=cost,
            method="atr_based",
            detail={
                "atr": atr_value,
                "atr_multiplier": atr_multiplier,
                "implied_stop_loss": round(stop_loss, 2),
                "price_risk": price_risk,
            },
        )

    @staticmethod
    def kelly_criterion(
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        capital: float,
        price: float,
        lot_size: int = 1,
        kelly_fraction: float = 0.25,
    ) -> SizingResult:
        """Kelly Criterion position sizing with fractional scaling."""
        if avg_loss <= 0:
            return SizingResult(method="kelly", detail={"error": "Invalid avg loss"})

        r = avg_win / avg_loss if avg_loss > 0 else 0
        p = win_rate
        q = 1 - p

        if r <= 0:
            return SizingResult(method="kelly", detail={"error": "Invalid win/loss ratio"})

        kelly_pct = (p * r - q) / r
        kelly_pct = max(0, min(kelly_pct, 0.25))  # Cap at 25%
        fraction = kelly_pct * kelly_fraction

        amount = capital * fraction
        raw_qty = amount / price
        qty = int(raw_qty / lot_size) * lot_size

        return SizingResult(
            quantity=max(qty, 0),
            capital_used=qty * price,
            risk_amount=amount,
            risk_percent=fraction * 100,
            margin_required=qty * price,
            method="kelly_criterion",
            detail={
                "kelly_pct": round(kelly_pct * 100, 2),
                "fraction": kelly_fraction,
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
            },
        )

    @staticmethod
    def volatility_adjusted(
        capital: float,
        price: float,
        volatility_pct: float,
        target_risk_pct: float = 2.0,
        lot_size: int = 1,
    ) -> SizingResult:
        """Scale position by inverse of volatility."""
        if volatility_pct <= 0:
            return SizingResult(method="volatility_adjusted", detail={"error": "Invalid volatility"})

        risk_amount = capital * (target_risk_pct / 100)
        vol_adjust = 1 / (volatility_pct / 100)  # Lower vol = bigger position
        vol_factor = min(vol_adjust, 5.0)  # Cap at 5x

        amount = min(risk_amount * vol_factor, capital * 0.5)  # Max 50% of capital
        raw_qty = amount / price
        qty = int(raw_qty / lot_size) * lot_size

        return SizingResult(
            quantity=max(qty, 0),
            capital_used=qty * price,
            risk_amount=amount,
            risk_percent=(amount / capital * 100) if capital > 0 else 0,
            margin_required=qty * price,
            method="volatility_adjusted",
            detail={
                "volatility_pct": volatility_pct,
                "vol_factor": round(vol_factor, 2),
                "target_risk_pct": target_risk_pct,
            },
        )
