"""
Regime Transition Engine — analyzes regime transitions, predicts next regime.
"""

from __future__ import annotations

from typing import Any

from market_regime.regime_detector import REGIME_CATEGORIES


TRANSITION_TYPES = [
    "Trend->Range", "Range->Breakout", "Breakout->Trend",
    "Trend->Reversal", "Volatility Expansion", "Volatility Compression",
]


class RegimeTransitionEngine:
    """Tracks and analyzes regime transitions."""

    @staticmethod
    def analyze(
        symbol: str,
        current_regime: str,
        transition_history: list[dict[str, Any]],
        regime_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute transition analytics from history."""
        total_transitions = len(transition_history)
        transitions_from_current = [
            t for t in transition_history if t.get("from_regime") == current_regime
        ]

        # Duration analysis
        durations: list[int] = []
        for t in transition_history:
            d = t.get("duration_bars", 0)
            if isinstance(d, (int, float)):
                durations.append(int(d))

        avg_duration = sum(durations) / len(durations) if durations else 0

        # Transition frequency
        regime_snapshots = len(regime_history)
        transition_rate = total_transitions / max(1, regime_snapshots)

        # Stability score
        stability = 1.0 - min(1.0, transition_rate * 5)

        # Confidence in transitions
        avg_confidence = 0.0
        for t in transition_history:
            c = t.get("confidence", 0)
            if isinstance(c, (int, float)):
                avg_confidence += c
        avg_confidence = avg_confidence / total_transitions if total_transitions > 0 else 0

        return {
            "symbol": symbol,
            "current_regime": current_regime,
            "total_transitions": total_transitions,
            "total_snapshots": regime_snapshots,
            "transition_rate": round(transition_rate, 3),
            "avg_duration_bars": round(avg_duration, 1),
            "avg_transition_confidence": round(avg_confidence, 1),
            "stability_score": round(stability, 2),
            "transitions_from_current": len(transitions_from_current),
        }

    @staticmethod
    def predict_next_regime(
        current_regime: str,
        transition_history: list[dict[str, Any]],
        context_snap: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Predict probability of next regime based on historical transitions."""
        current_cat = REGIME_CATEGORIES.get(current_regime, "")

        follow_counts: dict[str, int] = {}
        for t in transition_history:
            if t.get("from_regime") == current_regime:
                to_r = t.get("to_regime", "")
                follow_counts[to_r] = follow_counts.get(to_r, 0) + 1

        total = sum(follow_counts.values())

        if total == 0:
            # Default predictions based on category
            defaults = {
                "TREND": [("SIDEWAYS_RANGE", 0.35), ("WEAK_BULL_TREND", 0.25), ("HIGH_VOLATILITY", 0.20)],
                "RANGE": [("BREAKOUT", 0.30), ("STRONG_BULL_TREND", 0.20), ("STRONG_BEAR_TREND", 0.20)],
                "BREAKOUT": [("STRONG_BULL_TREND", 0.35), ("STRONG_BEAR_TREND", 0.25), ("FAKE_BREAKOUT", 0.20)],
                "VOLATILITY": [("SIDEWAYS_RANGE", 0.30), ("BREAKOUT", 0.25), ("STRONG_BULL_TREND", 0.15)],
                "SPECIAL": [("SIDEWAYS_RANGE", 0.30), ("STRONG_BULL_TREND", 0.20), ("HIGH_VOLATILITY", 0.20)],
            }
            predictions = defaults.get(current_cat, [("SIDEWAYS_RANGE", 0.50)])
            return [{"regime": r, "probability": round(p, 2)} for r, p in predictions]

        predictions = []
        for regime, count in follow_counts.items():
            predictions.append({
                "regime": regime,
                "probability": round(count / total, 2),
            })
        predictions.sort(key=lambda x: x["probability"], reverse=True)
        return predictions
