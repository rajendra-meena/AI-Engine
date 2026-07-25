"""Liquidity Context — evaluates liquidity zones, sweeps, session range."""

from typing import Any


class LiquidityContext:
    """Evaluates liquidity state from structure data."""

    @staticmethod
    def evaluate(structure_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not structure_snap:
            return {"state": "BALANCED", "sweeps": 0}

        sweeps = structure_snap.get("liquidity_sweeps", 0)
        equal_highs = structure_snap.get("equal_highs") or []
        equal_lows = structure_snap.get("equal_lows") or []
        impulse = structure_snap.get("impulse_active", False)
        pullback = structure_snap.get("pullback_active", False)

        if sweeps > 0:
            state = "LIQUIDITY_GRAB"
        elif len(equal_highs) >= 2 or len(equal_lows) >= 2:
            state = "LIQUIDITY_BUILDING"
        elif impulse:
            state = "EXPANSION"
        elif pullback:
            state = "PULLBACK"
        else:
            state = "BALANCED"

        return {
            "state": state,
            "sweeps": sweeps,
            "equal_highs": len(equal_highs),
            "equal_lows": len(equal_lows),
        }
