"""Tests for WalkForwardEngine."""

from __future__ import annotations

from model_registry.walk_forward import WalkForwardEngine


class TestWalkForwardEngine:
    def test_generate_rolling_windows(self):
        windows = WalkForwardEngine.generate_windows(200, 60, 20, 20, "rolling")
        assert len(windows) >= 4
        for w in windows:
            assert w["train_end"] <= w["val_start"]
            assert w["val_end"] <= 200

    def test_generate_expanding_windows(self):
        windows = WalkForwardEngine.generate_windows(200, 60, 20, 20, "expanding")
        assert len(windows) >= 1

    def test_small_dataset(self):
        windows = WalkForwardEngine.generate_windows(50, 60, 20, 20)
        assert len(windows) == 0

    def test_empty_trades_metrics(self):
        metrics = WalkForwardEngine.compute_window_metrics([])
        assert metrics["total_trades"] == 0

    def test_winning_trade_metrics(self):
        trades = [{"actual_return": 100}] * 10
        metrics = WalkForwardEngine.compute_window_metrics(trades)
        assert metrics["win_rate"] == 100.0
        assert metrics["total_trades"] == 10

    def test_mixed_trade_metrics(self):
        trades = [{"actual_return": 100}] * 7 + [{"actual_return": -50}] * 3
        metrics = WalkForwardEngine.compute_window_metrics(trades)
        assert metrics["win_rate"] == 70.0
        assert metrics["profit_factor"] > 1.0

    def test_generalization_strong(self):
        is_metrics = {"win_rate": 70.0, "profit_factor": 2.0, "expectancy": 1.5, "sharpe_ratio": 1.0, "max_drawdown": 10.0}
        val_metrics = {"win_rate": 65.0, "profit_factor": 1.8, "expectancy": 1.2, "sharpe_ratio": 0.8, "max_drawdown": 12.0}
        gen = WalkForwardEngine.compute_generalization(is_metrics, val_metrics)
        assert gen["generalization_score"] >= 60

    def test_generalization_degradation_detected(self):
        """Significant val underperformance should produce a warning score."""
        result = WalkForwardEngine.compute_generalization(
            {"win_rate": 65.0, "profit_factor": 1.8, "expectancy": 1.2, "sharpe_ratio": 0.9, "max_drawdown": 12.0},
            {"win_rate": 30.0, "profit_factor": 0.5, "expectancy": 0.2, "sharpe_ratio": 0.1, "max_drawdown": 35.0},
        )
        # Should detect degradation (all metrics dropped)
        comparisons = result["comparisons"]
        assert comparisons["win_rate"]["ratio"] < 1.0
        assert comparisons["profit_factor"]["ratio"] < 1.0

    def test_generalization_all_metrics_present(self):
        is_metrics = {"win_rate": 60.0, "profit_factor": 1.5, "expectancy": 1.0, "sharpe_ratio": 0.7, "max_drawdown": 15.0}
        val_metrics = {"win_rate": 55.0, "profit_factor": 1.3, "expectancy": 0.8, "sharpe_ratio": 0.5, "max_drawdown": 18.0}
        gen = WalkForwardEngine.compute_generalization(is_metrics, val_metrics)
        assert len(gen["comparisons"]) >= 4
