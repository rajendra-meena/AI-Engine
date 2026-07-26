"""Tests for MarketConditionAnalyzer — 12 tests."""

from __future__ import annotations

from ai_performance.market_condition import MarketConditionAnalyzer
from tests.ai_performance.conftest import _make_prediction, _make_outcome


class TestMarketCondition:
    def test_session_classification_opening(self):
        result = MarketConditionAnalyzer._classify_session("2026-07-26T09:20:00Z")
        assert result == "OPENING"

    def test_session_classification_mid(self):
        result = MarketConditionAnalyzer._classify_session("2026-07-26T12:00:00Z")
        assert result == "MID"

    def test_session_classification_closing(self):
        result = MarketConditionAnalyzer._classify_session("2026-07-26T15:00:00Z")
        assert result == "CLOSING"

    def test_session_classification_closed(self):
        result = MarketConditionAnalyzer._classify_session("2026-07-26T16:00:00Z")
        assert result == "CLOSED"

    def test_session_classification_empty(self):
        result = MarketConditionAnalyzer._classify_session("")
        assert result == "UNKNOWN"

    def test_value_classification_high(self):
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        result = MarketConditionAnalyzer._classify_value(85, values)
        assert result == "HIGH"

    def test_value_classification_low(self):
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        result = MarketConditionAnalyzer._classify_value(15, values)
        assert result == "LOW"

    def test_value_classification_normal(self):
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        result = MarketConditionAnalyzer._classify_value(50, values)
        assert result == "NORMAL"

    def test_condition_performance_basic(self):
        preds = [_make_prediction({"id": "p1", "market_regime": "TRENDING"})]
        outcomes = {"p1": _make_outcome({"prediction_id": "p1"})}
        results = MarketConditionAnalyzer.compute_condition_performance(preds, outcomes)
        assert len(results) >= 3  # volatility + session + trending
        trending = [r for r in results if r["condition_type"] == "trending"]
        assert len(trending) >= 1

    def test_condition_trending_classification(self):
        preds = [
            _make_prediction({"id": "p1", "market_regime": "TRENDING"}),
            _make_prediction({"id": "p2", "market_regime": "RANGING"}),
        ]
        outcomes = {
            "p1": _make_outcome({"prediction_id": "p1", "actual_return": 200}),
            "p2": _make_outcome({"prediction_id": "p2", "actual_return": -50}),
        }
        results = MarketConditionAnalyzer.compute_condition_performance(preds, outcomes)
        trending = [r for r in results if r["condition_type"] == "trending" and r["condition_value"] == "TRENDING"]
        assert len(trending) >= 1
        assert trending[0]["win_rate"] == 100.0

    def test_win_rate_calculation(self):
        preds = [
            _make_prediction({"id": f"p{i}", "created_at": "2026-07-26T12:00:00Z"})
            for i in range(4)
        ]
        outcomes = {}
        for i in range(4):
            outcomes[f"p{i}"] = _make_outcome({"prediction_id": f"p{i}", "actual_return": 100 if i < 3 else -100})
        results = MarketConditionAnalyzer.compute_condition_performance(preds, outcomes)
        session_mid = [r for r in results if r["condition_value"] == "MID"]
        assert len(session_mid) >= 1
        assert session_mid[0]["win_rate"] == 75.0

    def test_empty_predictions(self):
        results = MarketConditionAnalyzer.compute_condition_performance([])
        assert results == []

    def test_condition_types_present(self):
        preds = [_make_prediction({"id": "p1"})]
        results = MarketConditionAnalyzer.compute_condition_performance(preds)
        types = {r["condition_type"] for r in results}
        assert "volatility" in types
        assert "session" in types
        assert "trending" in types
