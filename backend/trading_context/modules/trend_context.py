"""Trend Context — evaluates EMA alignment, HH/HL, BOS/CHoCH, trend age."""

from typing import Any


class TrendContext:
    """Evaluates overall trend quality from indicators + structure."""

    @staticmethod
    def evaluate(indicator_snap: dict[str, Any] | None,
                 structure_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not indicator_snap:
            return {"bias": "NEUTRAL", "strength": "WEAK", "alignment": 0.0}

        bias_score = 0.0  # -1.0 to 1.0

        ema9 = indicator_snap.get("ema_9")
        ema20 = indicator_snap.get("ema_20")
        ema50 = indicator_snap.get("ema_50")
        close = indicator_snap.get("candle_close")

        # EMA alignment (max +-0.4)
        if close and ema9 and ema20:
            if close > ema9 > ema20:
                bias_score += 0.4
            elif close < ema9 < ema20:
                bias_score -= 0.4

        # Longer-term EMA alignment (max +-0.2)
        if ema20 and ema50:
            if ema20 > ema50:
                bias_score += 0.2
            elif ema20 < ema50:
                bias_score -= 0.2

        # Structure trend bias (max +-0.4)
        if structure_snap:
            trend = structure_snap.get("trend", "RANGING")
            if trend == "UPTREND":
                bias_score += 0.4
            elif trend == "DOWNTREND":
                bias_score -= 0.4

        # Clamp
        bias_score = max(-1.0, min(1.0, bias_score))

        if bias_score > 0.3:
            bias = "BULLISH"
        elif bias_score < -0.3:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        strength = "STRONG" if abs(bias_score) > 0.7 else "MODERATE" if abs(bias_score) > 0.3 else "WEAK"

        return {"bias": bias, "strength": strength, "alignment": round(bias_score, 2)}
