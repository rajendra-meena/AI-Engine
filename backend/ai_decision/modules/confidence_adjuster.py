"""
Dynamic Confidence Adjustment — adjusts overall confidence based on market conditions.

Reduces confidence when market conditions degrade signal reliability.
"""

from __future__ import annotations

from typing import Any


class DynamicConfidenceAdjuster:
    """Adjusts confidence based on market conditions."""

    @staticmethod
    def adjust(
        context_snap: dict[str, Any] | None,
        indicator_snap: dict[str, Any] | None,
        market_snapshot: dict[str, Any] | None = None,
        base_confidence: int = 0,
    ) -> dict[str, Any]:
        """Apply dynamic adjustments and return adjusted confidence."""
        adjustments: list[dict[str, Any]] = []
        total_deduction = 0

        # 1. High VIX / Expanding volatility
        adj1 = DynamicConfidenceAdjuster._adj_high_vix(context_snap)
        adjustments.append(adj1)
        if adj1["applied"]:
            total_deduction += adj1["impact"]

        # 2. Holiday session
        adj2 = DynamicConfidenceAdjuster._adj_holiday(context_snap)
        adjustments.append(adj2)
        if adj2["applied"]:
            total_deduction += adj2["impact"]

        # 3. Lunch session (low volume period)
        adj3 = DynamicConfidenceAdjuster._adj_lunch_session(context_snap)
        adjustments.append(adj3)
        if adj3["applied"]:
            total_deduction += adj3["impact"]

        # 4. Low volume
        adj4 = DynamicConfidenceAdjuster._adj_low_volume(indicator_snap)
        adjustments.append(adj4)
        if adj4["applied"]:
            total_deduction += adj4["impact"]

        # 5. Gap day
        adj5 = DynamicConfidenceAdjuster._adj_gap_day(context_snap, indicator_snap)
        adjustments.append(adj5)
        if adj5["applied"]:
            total_deduction += adj5["impact"]

        # 6. Broker delay
        adj6 = DynamicConfidenceAdjuster._adj_broker_delay(market_snapshot)
        adjustments.append(adj6)
        if adj6["applied"]:
            total_deduction += adj6["impact"]

        # 7. Market data delay
        adj7 = DynamicConfidenceAdjuster._adj_market_data_delay(market_snapshot)
        adjustments.append(adj7)
        if adj7["applied"]:
            total_deduction += adj7["impact"]

        adjusted = max(0, base_confidence - total_deduction)

        return {
            "adjusted_confidence": adjusted,
            "original_confidence": base_confidence,
            "adjustments": adjustments,
            "total_deduction": total_deduction,
        }

    @staticmethod
    def _adj_high_vix(context_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not context_snap:
            return {"factor": "high_vix", "applied": False, "impact": 0, "reason": "No context data"}
        vol = context_snap.get("volatility_state", "NORMAL")
        if isinstance(vol, str) and vol.upper() == "EXPANDING":
            return {"factor": "high_vix", "applied": True, "impact": 10, "reason": "Expanding volatility — reducing confidence"}
        return {"factor": "high_vix", "applied": False, "impact": 0, "reason": "Volatility normal"}

    @staticmethod
    def _adj_holiday(context_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not context_snap:
            return {"factor": "holiday", "applied": False, "impact": 0, "reason": "No context data"}
        session = context_snap.get("session", "")
        if isinstance(session, str) and "holiday" in session.lower():
            return {"factor": "holiday", "applied": True, "impact": 15, "reason": "Holiday session — low participation"}
        return {"factor": "holiday", "applied": False, "impact": 0, "reason": "Regular session"}

    @staticmethod
    def _adj_lunch_session(context_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not context_snap:
            return {"factor": "lunch_session", "applied": False, "impact": 0, "reason": "No context data"}
        session = context_snap.get("session", "")
        if isinstance(session, str) and "lunch" in session.lower():
            return {"factor": "lunch_session", "applied": True, "impact": 10, "reason": "Lunch session — lower liquidity"}
        return {"factor": "lunch_session", "applied": False, "impact": 0, "reason": "Not lunch session"}

    @staticmethod
    def _adj_low_volume(indicator_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not indicator_snap:
            return {"factor": "low_volume", "applied": False, "impact": 0, "reason": "No indicator data"}
        volume = indicator_snap.get("candle_volume") or indicator_snap.get("volume", 0)
        avg_volume = indicator_snap.get("average_volume", 0)
        if isinstance(volume, (int, float)) and isinstance(avg_volume, (int, float)) and avg_volume > 0:
            ratio = volume / avg_volume
            if ratio < 0.6:
                return {"factor": "low_volume", "applied": True, "impact": 15, "reason": f"Volume {ratio:.0%} of average — reducing confidence"}
        return {"factor": "low_volume", "applied": False, "impact": 0, "reason": "Volume adequate"}

    @staticmethod
    def _adj_gap_day(context_snap: dict[str, Any] | None, indicator_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not indicator_snap:
            return {"factor": "gap_day", "applied": False, "impact": 0, "reason": "No indicator data"}
        close = indicator_snap.get("candle_close", 0)
        open_price = indicator_snap.get("candle_open", close)
        if isinstance(close, (int, float)) and isinstance(open_price, (int, float)) and open_price > 0:
            gap_pct = abs(close - open_price) / open_price * 100
            if gap_pct > 1.0:
                return {"factor": "gap_day", "applied": True, "impact": 20, "reason": f"Price gap {gap_pct:.1f}% — high uncertainty"}
        return {"factor": "gap_day", "applied": False, "impact": 0, "reason": "No significant gap"}

    @staticmethod
    def _adj_broker_delay(market_snapshot: dict[str, Any] | None) -> dict[str, Any]:
        if not market_snapshot:
            return {"factor": "broker_delay", "applied": False, "impact": 0, "reason": "No market snapshot"}
        freshness = market_snapshot.get("data_freshness", "live")
        if freshness not in ("live", "connected"):
            return {"factor": "broker_delay", "applied": True, "impact": 10, "reason": f"Data freshness: {freshness}"}
        return {"factor": "broker_delay", "applied": False, "impact": 0, "reason": "Broker data live"}

    @staticmethod
    def _adj_market_data_delay(market_snapshot: dict[str, Any] | None) -> dict[str, Any]:
        if not market_snapshot:
            return {"factor": "market_data_delay", "applied": False, "impact": 0, "reason": "No market snapshot"}
        stream = market_snapshot.get("stream_state", "connected")
        if stream not in ("connected", "live"):
            return {"factor": "market_data_delay", "applied": True, "impact": 20, "reason": f"Stream state: {stream} — data may be delayed"}
        return {"factor": "market_data_delay", "applied": False, "impact": 0, "reason": "Market data live"}
