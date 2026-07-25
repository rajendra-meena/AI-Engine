"""Volatility Context — evaluates ATR, range, contraction/expansion."""

from typing import Any


class VolatilityContext:
    """Evaluates volatility state from indicators and breakouts."""

    @staticmethod
    def evaluate(
        indicator_snap: dict[str, Any] | None, pattern_snap: dict[str, Any] | None
    ) -> dict[str, Any]:
        if not indicator_snap or not pattern_snap:
            return {"state": "NORMAL", "atr": None}

        atr = indicator_snap.get("atr_14")
        close = indicator_snap.get("candle_close", 0)

        # Check for NR7 / volatility contraction
        bp = pattern_snap.get("breakout_patterns", [])
        has_nr7 = any(p.get("name") == "nr7" for p in bp)
        has_contraction = any(p.get("name") == "volatility_contraction" for p in bp)
        has_breakout = any("range_break" in p.get("name", "") for p in bp)

        if has_breakout:
            state = "EXPANDING"
        elif has_nr7 or has_contraction:
            state = "CONTRACTING"
        elif atr and close and atr / close > 0.02:
            state = "HIGH"
        else:
            state = "NORMAL"

        return {"state": state, "atr": atr}
