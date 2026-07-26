"""Tests for RegimeTransitionEngine."""

from __future__ import annotations

from market_regime.regime_transition import RegimeTransitionEngine, TRANSITION_TYPES


class TestRegimeTransitionEngine:
    def test_analyze_basic(self):
        result = RegimeTransitionEngine.analyze(
            symbol="TEST",
            current_regime="STRONG_BULL_TREND",
            transition_history=[
                {"from_regime": "SIDEWAYS_RANGE", "to_regime": "STRONG_BULL_TREND",
                 "confidence": 0.85, "duration_bars": 20},
            ],
            regime_history=[{"regime": "SIDEWAYS_RANGE"}, {"regime": "STRONG_BULL_TREND"}],
        )
        assert result["symbol"] == "TEST"
        assert result["total_transitions"] == 1
        assert 0 <= result["stability_score"] <= 1

    def test_empty_history(self):
        result = RegimeTransitionEngine.analyze("TEST", "RANGING", [], [])
        assert result["total_transitions"] == 0
        assert result["avg_duration_bars"] == 0

    def test_predict_next_with_history(self):
        predictions = RegimeTransitionEngine.predict_next_regime(
            current_regime="STRONG_BULL_TREND",
            transition_history=[
                {"from_regime": "STRONG_BULL_TREND", "to_regime": "SIDEWAYS_RANGE"},
                {"from_regime": "STRONG_BULL_TREND", "to_regime": "SIDEWAYS_RANGE"},
                {"from_regime": "STRONG_BULL_TREND", "to_regime": "HIGH_VOLATILITY"},
            ],
        )
        assert len(predictions) >= 2
        assert predictions[0]["regime"] == "SIDEWAYS_RANGE"
        assert predictions[0]["probability"] > 0

    def test_predict_no_history(self):
        predictions = RegimeTransitionEngine.predict_next_regime(
            current_regime="STRONG_BULL_TREND",
            transition_history=[],
        )
        assert len(predictions) >= 1
        assert all("regime" in p for p in predictions)

    def test_duration_calculation(self):
        result = RegimeTransitionEngine.analyze(
            "TEST", "RANGING",
            [{"from_regime": "TREND", "to_regime": "RANGE", "duration_bars": 15}],
            [{} for _ in range(10)],
        )
        assert result["avg_duration_bars"] == 15.0

    def test_transition_types_defined(self):
        assert len(TRANSITION_TYPES) == 6
        assert "Trend->Range" in TRANSITION_TYPES
        assert "Volatility Compression" in TRANSITION_TYPES
