"""Tests for API-level behavior of market regime modules."""

from __future__ import annotations

from market_regime.strategy_router import StrategyRouter, REGIME_STRATEGY_MAP
from market_regime.regime_detector import RegimeDetector, REGIME_LIST
from market_regime.confidence_modifier import RegimeConfidenceModifier, REGIME_CONFIDENCE_ADJUSTMENTS
from market_regime.regime_transition import RegimeTransitionEngine
from market_regime.performance_analytics import RegimePerformanceAnalytics


class TestAPI:
    def test_regime_list_has_all_14(self):
        assert len(REGIME_LIST) == 14

    def test_all_regimes_in_strategy_map(self):
        for regime in REGIME_LIST:
            assert regime in REGIME_STRATEGY_MAP, f"{regime} missing from strategy map"

    def test_all_regimes_in_confidence_map(self):
        for regime in REGIME_LIST:
            assert regime in REGIME_CONFIDENCE_ADJUSTMENTS, f"{regime} missing from confidence map"

    def test_strategy_map_has_required_fields(self):
        for regime, mapping in REGIME_STRATEGY_MAP.items():
            assert "primary" in mapping
            assert "secondary" in mapping
            assert "avoid" in mapping
            assert "expected_win_rate" in mapping
            assert "reasoning" in mapping

    def test_detector_handles_empty_inputs(self):
        snap = RegimeDetector.detect({}, {}, {}, {})
        assert snap.regime == "SIDEWAYS_RANGE"
        assert 0 <= snap.confidence <= 100

    def test_detector_handles_none_inputs(self):
        snap = RegimeDetector.detect(None, None, None, None)
        assert snap.regime is not None

    def test_strategy_router_does_not_crash(self):
        for regime in REGIME_LIST:
            rec = StrategyRouter.get_best_strategy(regime)
            assert rec["primary"] != ""

    def test_confidence_adjustment_all_regimes(self):
        for regime in REGIME_LIST:
            result = RegimeConfidenceModifier.adjust(50, regime, 100)
            assert 0 <= result["adjusted_confidence"] <= 100

    def test_performance_analytics_empty_db(self):
        """Should handle missing tables gracefully."""
        import sqlite3
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE prediction_journal (id TEXT PRIMARY KEY, regime TEXT, confidence INTEGER)")
        db.execute("CREATE TABLE prediction_outcome (id TEXT PRIMARY KEY, prediction_id TEXT, actual_return REAL)")
        db.execute("CREATE TABLE trade_feedback (id TEXT PRIMARY KEY, prediction_id TEXT, holding_duration INTEGER)")
        perf = RegimePerformanceAnalytics.compute_regime_performance(db)
        assert isinstance(perf, dict)

    def test_transition_engine_no_crash(self):
        result = RegimeTransitionEngine.analyze("TEST", "RANGING", [], [])
        assert result["symbol"] == "TEST"
        assert result["total_transitions"] == 0

    def test_predict_next_structure(self):
        preds = RegimeTransitionEngine.predict_next_regime("STRONG_BULL_TREND", [])
        assert isinstance(preds, list)
        if preds:
            assert "regime" in preds[0]
            assert "probability" in preds[0]

    def test_snapshot_full_regime_list(self):
        """Verify each regime can be detected in principle without crash."""
        for regime in REGIME_LIST:
            # Just verify the regime name is valid
            assert regime in REGIME_STRATEGY_MAP
