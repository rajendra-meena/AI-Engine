"""Tests for StrategyRouter — strategy mapping and recommendations."""

from __future__ import annotations

from market_regime.strategy_router import StrategyRouter, REGIME_STRATEGY_MAP
from market_regime.regime_detector import REGIME_LIST


class TestStrategyRouter:
    def test_all_regimes_have_mapping(self):
        for regime in REGIME_LIST:
            rec = StrategyRouter.get_best_strategy(regime)
            assert rec["primary"] != "", f"{regime} missing primary strategy"
            assert isinstance(rec["avoid"], list)
            assert 0 <= rec["expected_win_rate"] <= 1

    def test_unknown_regime_falls_back(self):
        rec = StrategyRouter.get_best_strategy("UNKNOWN_REGIME")
        assert rec["primary"] == "range"

    def test_returns_all_fields(self):
        rec = StrategyRouter.get_best_strategy("STRONG_BULL_TREND")
        assert "regime" in rec
        assert "primary" in rec
        assert "secondary" in rec
        assert "avoid" in rec
        assert "expected_win_rate" in rec
        assert "confidence" in rec
        assert "reasoning" in rec

    def test_includes_historical_override(self):
        perf = {"STRONG_BULL_TREND": {"win_rate": 80}}
        rec = StrategyRouter.get_best_strategy("STRONG_BULL_TREND", perf)
        assert rec["historical_success"] == 0.80

    def test_confidence_without_performance(self):
        rec = StrategyRouter.get_best_strategy("SIDEWAYS_RANGE")
        assert rec["confidence"] == int(rec["expected_win_rate"] * 100)

    def test_list_all_recommendations(self):
        all_recs = StrategyRouter.list_all_recommendations()
        assert len(all_recs) == len(REGIME_STRATEGY_MAP)
        for r in all_recs:
            assert r["regime"] in REGIME_STRATEGY_MAP

    def test_strong_trend_avoids_reversal(self):
        for regime in ("STRONG_BULL_TREND", "STRONG_BEAR_TREND"):
            rec = StrategyRouter.get_best_strategy(regime)
            assert "reversal" in rec["avoid"]

    def test_sideways_avoids_trend_following(self):
        rec = StrategyRouter.get_best_strategy("SIDEWAYS_RANGE")
        assert "trend_following" in rec["avoid"]

    def test_news_driven_avoids_all(self):
        rec = StrategyRouter.get_best_strategy("NEWS_DRIVEN")
        assert rec["primary"] == "no_trade"
        assert len(rec["avoid"]) >= 5

    def test_win_rates_in_valid_range(self):
        for regime in REGIME_LIST:
            rec = StrategyRouter.get_best_strategy(regime)
            assert 0 <= rec["expected_win_rate"] <= 1, f"{regime} has invalid win rate"

    def test_illiquid_avoids_all_directional(self):
        rec = StrategyRouter.get_best_strategy("ILLIQUID_MARKET")
        assert len(rec["avoid"]) >= 5
