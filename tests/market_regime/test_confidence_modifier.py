"""Tests for RegimeConfidenceModifier — confidence adjustments per regime."""

from __future__ import annotations

from market_regime.confidence_modifier import RegimeConfidenceModifier, REGIME_CONFIDENCE_ADJUSTMENTS


class TestConfidenceModifier:
    def test_strong_bull_adjusts_up(self):
        result = RegimeConfidenceModifier.adjust(50, "STRONG_BULL_TREND", 100)
        assert result["adjusted_confidence"] > 50

    def test_fake_breakout_adjusts_down(self):
        result = RegimeConfidenceModifier.adjust(80, "FAKE_BREAKOUT", 100)
        assert result["adjusted_confidence"] < 80

    def test_illiquid_adjusts_down_significantly(self):
        result = RegimeConfidenceModifier.adjust(80, "ILLIQUID_MARKET", 100)
        assert result["adjusted_confidence"] <= 50

    def test_news_driven_adjusts_down_major(self):
        result = RegimeConfidenceModifier.adjust(80, "NEWS_DRIVEN", 100)
        assert result["adjusted_confidence"] <= 40

    def test_no_regime_returns_original(self):
        result = RegimeConfidenceModifier.adjust(65, None)
        assert result["adjusted_confidence"] == 65
        assert len(result["adjustments"]) == 0

    def test_never_goes_below_zero(self):
        result = RegimeConfidenceModifier.adjust(10, "NEWS_DRIVEN", 100)
        assert result["adjusted_confidence"] >= 0

    def test_never_goes_above_one_hundred(self):
        result = RegimeConfidenceModifier.adjust(95, "STRONG_BULL_TREND", 100)
        assert result["adjusted_confidence"] <= 100

    def test_scaling_by_regime_confidence(self):
        full = RegimeConfidenceModifier.adjust(50, "FAKE_BREAKOUT", 100)
        half = RegimeConfidenceModifier.adjust(50, "FAKE_BREAKOUT", 50)
        zero = RegimeConfidenceModifier.adjust(50, "FAKE_BREAKOUT", 0)
        assert full["total_adjustment"] < half["total_adjustment"]  # -20 vs -10
        assert zero["total_adjustment"] == 0

    def test_returns_adjustment_list(self):
        result = RegimeConfidenceModifier.adjust(50, "SIDEWAYS_RANGE", 100)
        assert len(result["adjustments"]) == 1
        adj = result["adjustments"][0]
        assert adj["factor"] == "regime"
        assert adj["regime"] == "SIDEWAYS_RANGE"
        assert "impact" in adj

    def test_all_regimes_have_adjustments(self):
        for regime, adjustment in REGIME_CONFIDENCE_ADJUSTMENTS.items():
            result = RegimeConfidenceModifier.adjust(50, regime, 100)
            assert result["total_adjustment"] == adjustment

    def test_low_confidence_regime_halves_impact(self):
        result = RegimeConfidenceModifier.adjust(80, "NEWS_DRIVEN", 50)
        # -50 * 0.5 = -25
        assert result["total_adjustment"] == -25
