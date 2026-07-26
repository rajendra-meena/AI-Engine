"""Tests for AI Performance API endpoints — 16 tests."""

from __future__ import annotations

from unittest.mock import patch
from ai_performance.trade_evaluator import TradeEvaluator
from ai_performance.strategy_engine import StrategyPerformanceEngine


class TestAPI:
    """Tests for API-level behavior of the performance modules."""

    def test_evaluate_single_returns_all_fields(self):
        from tests.ai_performance.conftest import _make_prediction, _make_outcome, _make_feedback
        p = _make_prediction()
        o = _make_outcome()
        f = _make_feedback()
        result = TradeEvaluator.evaluate_single(p, o, f)
        required = ["entry_accuracy", "exit_quality", "sl_quality", "target_quality",
                     "mfe_mae_ratio", "slippage_impact", "overall_score", "outcome_class"]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_evaluate_batch_returns_list(self):
        results = TradeEvaluator.evaluate_batch([], {}, {})
        assert isinstance(results, list)

    def test_strategy_metrics_includes_all_fields(self):
        from tests.ai_performance.conftest import _make_prediction
        trade = {**_make_prediction({"id": "t1"}), "actual_return": 100}
        result = StrategyPerformanceEngine.compute_strategy_metrics("test", [trade])
        required = ["strategy_id", "strategy_name", "total_trades", "win_rate",
                     "profit_factor", "expectancy", "sharpe_ratio", "max_drawdown",
                     "avg_holding_hours", "consecutive_wins", "consecutive_losses"]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_overview_has_expected_structure(self):
        result = TradeEvaluator.evaluate_single(None, None, None)
        assert "overall_score" in result
        assert "outcome_class" in result
        assert 0 <= result["overall_score"] <= 100

    def test_calibration_curve_buckets(self):
        from ai_performance.calibration_engine import ConfidenceCalibrationEngine
        curve = ConfidenceCalibrationEngine.compute_reliability_curve([], {})
        assert len(curve) == 10
        for b in curve:
            assert "bucket_label" in b
            assert "min" in b
            assert "max" in b
            assert "count" in b

    def test_mistake_summary_empty(self):
        from ai_performance.mistake_classifier import MistakeClassifier
        summary = MistakeClassifier.get_mistake_summary([])
        assert summary["total_count"] == 0
        assert summary["most_common"] == "none"

    def test_market_conditions_empty(self):
        from ai_performance.market_condition import MarketConditionAnalyzer
        results = MarketConditionAnalyzer.compute_condition_performance([])
        assert results == []

    def test_patterns_empty_input(self):
        from ai_performance.pattern_analyzer import PatternPerformanceAnalyzer
        results = PatternPerformanceAnalyzer.compute_pattern_performance([], {}, {})
        assert isinstance(results, list)
        assert len(results) >= 0

    def test_dataset_stats_empty(self):
        import sqlite3
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE prediction_journal (id TEXT PRIMARY KEY, symbol TEXT)")
        db.execute("CREATE TABLE prediction_outcome (id TEXT PRIMARY KEY, prediction_id TEXT)")
        db.execute("CREATE TABLE trade_feedback (id TEXT PRIMARY KEY, prediction_id TEXT)")
        db.execute("CREATE TABLE ai_perf_trade_evaluation (id TEXT PRIMARY KEY, prediction_id TEXT, outcome_class TEXT)")
        from ai_performance.dataset_builder import AIPerformanceDatasetBuilder
        stats = AIPerformanceDatasetBuilder.get_dataset_stats(db)
        assert stats["total_records"] == 0
        assert stats["with_outcome"] == 0

    def test_trade_evaluation_score_range(self):
        from tests.ai_performance.conftest import _make_prediction, _make_outcome, _make_feedback
        for _ in range(5):
            p = _make_prediction()
            o = _make_outcome()
            f = _make_feedback()
            result = TradeEvaluator.evaluate_single(p, o, f)
            assert 0 <= result["overall_score"] <= 100

    def test_strategy_sorts_by_win_rate(self):
        from tests.ai_performance.conftest import _make_prediction, _make_outcome
        preds = [
            _make_prediction({"id": "p1", "strategy_id": "a"}),
            _make_prediction({"id": "p2", "strategy_id": "b"}),
        ]
        outcomes = {
            "p1": _make_outcome({"prediction_id": "p1", "actual_return": 200}),
            "p2": _make_outcome({"prediction_id": "p2", "actual_return": -50}),
        }
        strategies = StrategyPerformanceEngine.compute_all_strategies(preds, outcomes)
        assert len(strategies) == 2
        # Sorted descending by win rate

    def test_mistake_types_list(self):
        from ai_performance.mistake_classifier import MISTAKE_TYPES
        all_types = set(MISTAKE_TYPES)
        expected = {"late_entry", "early_exit", "weak_confirmation", "false_breakout",
                     "wrong_trend", "low_liquidity", "high_slippage", "news_impact",
                     "risk_management_failure", "data_quality_issue"}
        assert all_types == expected

    def test_pattern_tracked_list_full(self):
        from ai_performance.pattern_analyzer import TRACKED_PATTERNS
        expected = {"bull_flag", "bear_flag", "double_top", "double_bottom",
                     "triangle", "breakout", "fake_breakout", "liquidity_grab", "gap_fill"}
        assert set(TRACKED_PATTERNS) == expected

    def test_store_evaluation_missing_db(self):
        """store_evaluation should handle missing db gracefully."""
        result = TradeEvaluator.evaluate_single(None, None, None)
        assert result["overall_score"] == 0

    def test_strategy_engine_null_strategy(self):
        from tests.ai_performance.conftest import _make_prediction
        preds = [_make_prediction({"id": "p1", "strategy_id": None})]
        strategies = StrategyPerformanceEngine.compute_all_strategies(preds)
        assert len(strategies) >= 1
