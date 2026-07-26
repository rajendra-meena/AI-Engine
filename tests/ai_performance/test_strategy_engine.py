"""Tests for StrategyPerformanceEngine — 12 tests."""

from __future__ import annotations

from ai_performance.strategy_engine import StrategyPerformanceEngine
from tests.ai_performance.conftest import _make_prediction, _make_outcome, _make_feedback


class TestStrategyEngine:
    def test_empty_strategy(self):
        result = StrategyPerformanceEngine.compute_strategy_metrics("test", [])
        assert result["total_trades"] == 0
        assert result["win_rate"] == 0

    def test_win_rate_all_wins(self):
        trades = [
            {**{"actual_return": 100}, **_make_prediction({"id": f"p{i}", "actual_return": 100})}
            for i in range(5)
        ]
        result = StrategyPerformanceEngine.compute_strategy_metrics("test", trades)
        assert result["win_rate"] == 100.0

    def test_win_rate_all_losses(self):
        trades = [
            {**{"actual_return": -50}, **_make_prediction({"id": f"p{i}", "actual_return": -50})}
            for i in range(5)
        ]
        result = StrategyPerformanceEngine.compute_strategy_metrics("test", trades)
        assert result["win_rate"] == 0.0

    def test_profit_factor_calculation(self):
        trades = [
            {**_make_prediction({"id": "p1", "actual_return": 300}), "actual_return": 300},
            {**_make_prediction({"id": "p2", "actual_return": -100}), "actual_return": -100},
        ]
        result = StrategyPerformanceEngine.compute_strategy_metrics("test", trades)
        assert result["profit_factor"] > 0

    def test_expectancy_positive(self):
        trades = [
            {**_make_prediction({"id": "p1", "actual_return": 500}), "actual_return": 500},
            {**_make_prediction({"id": "p2", "actual_return": 100}), "actual_return": 100},
        ]
        result = StrategyPerformanceEngine.compute_strategy_metrics("test", trades)
        assert result["expectancy"] > 0

    def test_max_drawdown_computed(self):
        trades = [
            {**_make_prediction({"id": "p1", "actual_return": 100}), "actual_return": 100},
            {**_make_prediction({"id": "p2", "actual_return": -200}), "actual_return": -200},
            {**_make_prediction({"id": "p3", "actual_return": 50}), "actual_return": 50},
        ]
        result = StrategyPerformanceEngine.compute_strategy_metrics("test", trades)
        assert result["max_drawdown"] >= 0

    def test_sharpe_ratio_returned(self):
        trades = [
            {**_make_prediction({"id": f"p{i}", "actual_return": 50 + i * 10}), "actual_return": 50 + i * 10}
            for i in range(10)
        ]
        result = StrategyPerformanceEngine.compute_strategy_metrics("test", trades)
        assert result["sharpe_ratio"] is not None

    def test_all_strategies_grouping(self):
        preds = [
            _make_prediction({"id": "p1", "strategy_id": "trend_following"}),
            _make_prediction({"id": "p2", "strategy_id": "breakout"}),
            _make_prediction({"id": "p3", "strategy_id": "trend_following"}),
            _make_prediction({"id": "p4", "strategy_id": "reversal"}),
        ]
        outcomes = {
            "p1": _make_outcome({"prediction_id": "p1", "actual_return": 200}),
            "p2": _make_outcome({"prediction_id": "p2", "actual_return": -50}),
            "p3": _make_outcome({"prediction_id": "p3", "actual_return": 100}),
            "p4": _make_outcome({"prediction_id": "p4", "actual_return": 50}),
        }
        strategies = StrategyPerformanceEngine.compute_all_strategies(preds, outcomes)
        assert len(strategies) == 3
        trend = [s for s in strategies if s["strategy_id"] == "trend_following"][0]
        assert trend["total_trades"] == 2

    def test_unknown_strategy_handled(self):
        preds = [_make_prediction({"id": "p1", "strategy_id": None})]
        strategies = StrategyPerformanceEngine.compute_all_strategies(preds)
        assert len(strategies) >= 1
        assert strategies[0]["strategy_name"] == "Unknown"

    def test_largest_win_loss(self):
        trades = [
            {**_make_prediction({"id": "p1", "actual_return": 500}), "actual_return": 500},
            {**_make_prediction({"id": "p2", "actual_return": -300}), "actual_return": -300},
        ]
        result = StrategyPerformanceEngine.compute_strategy_metrics("test", trades)
        assert result["largest_win"] == 500
        assert result["largest_loss"] == -300

    def test_consecutive_streaks(self):
        trades = [
            {**_make_prediction({"id": f"p{i}", "actual_return": 100}), "actual_return": 100}
            for i in range(3)
        ] + [
            {**_make_prediction({"id": f"p{i}", "actual_return": -50}), "actual_return": -50}
            for i in range(3, 5)
        ]
        result = StrategyPerformanceEngine.compute_strategy_metrics("test", trades)
        assert result["consecutive_wins"] >= 3
