"""Tests for RegimeExplanationEngine."""

from __future__ import annotations

from market_regime.explanation_engine import RegimeExplanationEngine, FACTOR_DESCRIPTIONS
from market_regime.snapshot import RegimeSnapshot


class TestRegimeExplanationEngine:
    def test_explain_basic(self):
        snap = RegimeSnapshot(
            regime="STRONG_BULL_TREND", confidence=85, stability_score=0.8,
            supporting_factors=("ema_bullish_alignment", "strong_volume", "adx_35"),
            regime_age_bars=15,
        )
        rec = {"primary": "trend_following", "secondary": "pullback",
               "avoid": ["reversal"], "confidence": 85}
        exp = RegimeExplanationEngine.explain(snap, rec)
        assert "Strong Bull Trend" in exp.primary_reason
        assert len(exp.supporting_evidence) >= 2
        assert exp.recommended_strategy == "trend_following"
        assert "reversal" in exp.avoid_strategies

    def test_explain_null_snapshot(self):
        exp = RegimeExplanationEngine.explain(None)
        assert exp.regime == "UNKNOWN"
        assert exp.primary_reason != ""

    def test_explain_without_recommendation(self):
        snap = RegimeSnapshot(regime="SIDEWAYS_RANGE", confidence=60, stability_score=0.5,
                              supporting_factors=("no_bos",), regime_age_bars=5)
        exp = RegimeExplanationEngine.explain(snap)
        assert "Sideways Range" in exp.primary_reason
        assert exp.recommended_strategy == "" or exp.recommended_strategy == "none"
        assert exp.strategy_reasoning == ""

    def test_factor_descriptions_cover_common_factors(self):
        # Check that common factors have descriptions
        common = ["ema_bullish_alignment", "vwap_support", "strong_volume",
                   "volatility_expanding", "opening_session"]
        for f in common:
            assert f in FACTOR_DESCRIPTIONS, f"Missing description for {f}"

    def test_explain_fake_breakout(self):
        snap = RegimeSnapshot(regime="FAKE_BREAKOUT", confidence=70, stability_score=0.3,
                              supporting_factors=("liquidity_sweep", "weak_mtf_alignment"),
                              regime_age_bars=3)
        rec = {"primary": "mean_reversion", "secondary": "reversal",
               "avoid": ["breakout", "momentum"], "confidence": 60}
        exp = RegimeExplanationEngine.explain(snap, rec)
        evidence_str = " ".join(exp.supporting_evidence).lower()
        assert "liquidity" in evidence_str or "sweep" in evidence_str
