"""
Risk Engine — evaluates market risk and position risk context.

Inputs: Volatility (context), SR proximity, MTF permission, ATR
Output: risk_level, max_risk_percent, risk_reward_context, reasoning
"""

from __future__ import annotations

from typing import Any


class RiskEngine:
    """Evaluates risk context from volatility, SR distance, and MTF permission."""

    @staticmethod
    def evaluate(context_snap: dict[str, Any] | None,
                 mtf_snap: dict[str, Any] | None,
                 sr_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not context_snap:
            return {"risk_level": "EXTREME", "max_risk_percent": 0.0,
                    "risk_reward_context": "unknown", "reasoning": ["No context data"]}

        risk_score = 0.0
        reasoning = []
        max_risk = 1.0  # base: 1% risk per trade

        # Volatility risk
        vol = context_snap.get("volatility_state", "NORMAL")
        if vol == "EXPANDING":
            risk_score += 30
            max_risk = 0.5
            reasoning.append("High volatility: reduce position size")
        elif vol == "HIGH":
            risk_score += 20
            max_risk = 0.75
            reasoning.append("Elevated volatility")
        elif vol == "CONTRACTING":
            risk_score += 10
            reasoning.append("Contracting volatility: breakout imminent")

        # SR proximity risk
        if sr_snap:
            nearest_s = sr_snap.get("nearest_support")
            nearest_r = sr_snap.get("nearest_resistance")
            close = context_snap.get("indicator_snap", {}).get("candle_close")
            if nearest_s and nearest_r and close:
                range_size = nearest_r - nearest_s
                if range_size > 0 and close:
                    pos = (close - nearest_s) / range_size
                    if pos < 0.1 or pos > 0.9:
                        risk_score += 20
                        reasoning.append("Price near S/R boundary: higher risk")
                        max_risk = min(max_risk, 0.5)
                    elif pos < 0.2 or pos > 0.8:
                        risk_score += 10
                        max_risk = min(max_risk, 0.75)

        # MTF permission risk
        if mtf_snap:
            permission = mtf_snap.get("trading_permission", "WAIT")
            if permission == "NO_TRADE":
                risk_score += 50
                max_risk = 0.0
                reasoning.append("MTF says NO_TRADE")
            elif permission == "WAIT":
                risk_score += 20
                max_risk = min(max_risk, 0.25)
                reasoning.append("MTF says WAIT")

        # Warnings from context
        warnings = context_snap.get("warnings") or []
        if "Low confidence" in warnings:
            risk_score += 15
        if "Weak trend" in warnings:
            risk_score += 10

        # Determine level
        if risk_score >= 70:
            level = "EXTREME"
        elif risk_score >= 50:
            level = "HIGH"
        elif risk_score >= 30:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "risk_level": level,
            "risk_score": int(risk_score),
            "max_risk_percent": round(max_risk, 2),
            "reasoning": reasoning,
        }
