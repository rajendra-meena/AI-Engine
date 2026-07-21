"""
Trade Planner — structures an institutional trade plan from analysis.

Inputs: Score, confidence, risk, SR levels, trend
Output: trade_plan with direction, entry zone, SL zone, targets, reasoning
"""

from __future__ import annotations

from typing import Any


class TradePlanner:
    """Constructs a structured trade plan from all available data."""

    @staticmethod
    def evaluate(score_result: dict[str, Any],
                 confidence_result: dict[str, Any],
                 risk_result: dict[str, Any],
                 context_snap: dict[str, Any] | None,
                 mtf_snap: dict[str, Any] | None,
                 sr_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not context_snap:
            return {"direction": "NONE", "plan_valid": False, "reasoning": ["No context data"]}

        direction = "NONE"
        reasoning = []
        plan_valid = False

        bias = context_snap.get("overall_bias", "NEUTRAL")
        score = score_result.get("score", 0)
        confidence = confidence_result.get("confidence", 0)
        risk_level = risk_result.get("risk_level", "EXTREME")

        # Determine direction
        if bias == "BULLISH" and score >= 50 and risk_level in ("LOW", "MEDIUM"):
            direction = "LONG"
            plan_valid = True
            reasoning.append(f"Bullish bias with score {score}")
        elif bias == "BEARISH" and score >= 50 and risk_level in ("LOW", "MEDIUM"):
            direction = "SHORT"
            plan_valid = True
            reasoning.append(f"Bearish bias with score {score}")
        else:
            reasoning.append(f"No trade: bias={bias}, score={score}, risk={risk_level}")
            return {"direction": "NONE", "plan_valid": False, "reasoning": reasoning}

        # Entry zone from SR levels
        entry_zone = None
        sl_zone = None
        target_zones = []

        if sr_snap and direction != "NONE":
            nearest_s = sr_snap.get("nearest_support")
            nearest_r = sr_snap.get("nearest_resistance")
            close = context_snap.get("indicator_snap", {}).get("candle_close") or \
                   context_snap.get("timestamp", "")

            if direction == "LONG":
                entry_zone = {"type": "market", "price": "current", "zone": f"Above {nearest_s}"}
                if nearest_s:
                    sl_zone = {"type": "stop_loss", "price": nearest_s, "zone": f"Below {nearest_s}"}
                if nearest_r:
                    target_zones = [{"type": "target_1", "price": nearest_r, "zone": f"Near {nearest_r}"}]
            elif direction == "SHORT":
                entry_zone = {"type": "market", "price": "current", "zone": f"Below {nearest_r}"}
                if nearest_r:
                    sl_zone = {"type": "stop_loss", "price": nearest_r, "zone": f"Above {nearest_r}"}
                if nearest_s:
                    target_zones = [{"type": "target_1", "price": nearest_s, "zone": f"Near {nearest_s}"}]

        # Risk-reward context
        rr_context = risk_result.get("risk_level", "MEDIUM")

        return {
            "direction": direction,
            "plan_valid": plan_valid,
            "entry_zone": entry_zone,
            "sl_zone": sl_zone,
            "target_zones": target_zones,
            "risk_reward_context": rr_context,
            "max_risk_percent": risk_result.get("max_risk_percent", 0.5),
            "reasoning": reasoning,
        }
