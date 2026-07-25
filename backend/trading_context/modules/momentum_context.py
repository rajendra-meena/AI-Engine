"""Momentum Context — evaluates RSI, MACD, ADX for momentum quality."""

from typing import Any


class MomentumContext:
    """Evaluates momentum from RSI, MACD, ADX."""

    @staticmethod
    def evaluate(indicator_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not indicator_snap:
            return {"state": "WEAK", "strength": "WEAK", "bias": "NEUTRAL"}

        bias_score = 0.0

        rsi = indicator_snap.get("rsi_14")
        if rsi is not None:
            if rsi > 60:
                bias_score += 0.3
            elif rsi < 40:
                bias_score -= 0.3
            if rsi > 70:
                bias_score += 0.1  # strong bullish
            elif rsi < 30:
                bias_score -= 0.1

        macd_hist = indicator_snap.get("macd_histogram")
        if macd_hist is not None:
            if macd_hist > 0:
                bias_score += 0.3
            elif macd_hist < 0:
                bias_score -= 0.3

        adx = indicator_snap.get("adx_14")
        if adx is not None:
            if adx > 25:
                bias_score = bias_score * 1.2  # amplify when trending

        bias_score = max(-1.0, min(1.0, bias_score))

        if bias_score > 0.2:
            bias = "BULLISH"
        elif bias_score < -0.2:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        state = (
            "STRONG"
            if abs(bias_score) > 0.6
            else "MODERATE" if abs(bias_score) > 0.2 else "WEAK"
        )

        return {
            "state": state,
            "strength": state,
            "bias": bias,
            "score": round(bias_score, 2),
        }
