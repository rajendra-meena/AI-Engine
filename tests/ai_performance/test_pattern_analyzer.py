"""Tests for PatternPerformanceAnalyzer — 12 tests."""

from __future__ import annotations

from ai_performance.pattern_analyzer import PatternPerformanceAnalyzer
from tests.ai_performance.conftest import _make_prediction, _make_outcome


class TestPatternAnalyzer:
    def test_pattern_extraction_from_json(self):
        snapshot = '{"strongest_pattern": "bull_flag", "chart_patterns": [{"name": "bull_flag"}]}'
        patterns = PatternPerformanceAnalyzer.extract_patterns_from_snapshot(snapshot)
        assert "bull_flag" in patterns

    def test_pattern_extraction_multiple(self):
        snapshot = '{"candlestick_patterns": [{"name": "doji"}, {"name": "hammer"}], "chart_patterns": [{"name": "double_top"}]}'
        patterns = PatternPerformanceAnalyzer.extract_patterns_from_snapshot(snapshot)
        assert len(patterns) >= 2

    def test_pattern_extraction_empty(self):
        patterns = PatternPerformanceAnalyzer.extract_patterns_from_snapshot(None)
        assert patterns == []

    def test_pattern_extraction_invalid_json(self):
        patterns = PatternPerformanceAnalyzer.extract_patterns_from_snapshot("not json")
        assert patterns == []

    def test_pattern_performance_basic(self):
        preds = [_make_prediction({"id": "p1", "pattern_snapshot": '{"strongest_pattern": "bull_flag"}'})]
        outcomes = {"p1": _make_outcome({"prediction_id": "p1"})}
        results = PatternPerformanceAnalyzer.compute_pattern_performance(preds, outcomes)
        bull = [r for r in results if r["pattern_name"] == "bull_flag"]
        assert len(bull) >= 1
        assert bull[0]["total_occurrences"] >= 1

    def test_pattern_win_rate(self):
        preds = [
            _make_prediction({"id": "p1", "pattern_snapshot": '{"chart_patterns": [{"name": "bull_flag"}]}'}),
            _make_prediction({"id": "p2", "pattern_snapshot": '{"chart_patterns": [{"name": "bull_flag"}]}'}),
        ]
        outcomes = {
            "p1": _make_outcome({"prediction_id": "p1", "actual_return": 200}),
            "p2": _make_outcome({"prediction_id": "p2", "actual_return": -50}),
        }
        results = PatternPerformanceAnalyzer.compute_pattern_performance(preds, outcomes)
        bull = [r for r in results if r["pattern_name"] == "bull_flag"][0]
        assert bull["win_rate"] == 50.0

    def test_pattern_tracked_list(self):
        from ai_performance.pattern_analyzer import TRACKED_PATTERNS
        assert "bull_flag" in TRACKED_PATTERNS
        assert "fake_breakout" in TRACKED_PATTERNS
        assert "liquidity_grab" in TRACKED_PATTERNS

    def test_no_patterns(self):
        preds = [_make_prediction({"id": "p1", "pattern_snapshot": None})]
        results = PatternPerformanceAnalyzer.compute_pattern_performance(preds)
        other = [r for r in results if r["pattern_name"] == "other"]
        assert len(other) >= 1

    def test_failure_rate_calculation(self):
        preds = [
            _make_prediction({"id": f"p{i}", "pattern_snapshot": '{"strongest_pattern": "double_top"}'})
            for i in range(4)
        ]
        outcomes = {}
        for i in range(4):
            outcomes[f"p{i}"] = _make_outcome({"prediction_id": f"p{i}", "actual_return": -50 if i < 3 else 200})
        results = PatternPerformanceAnalyzer.compute_pattern_performance(preds, outcomes)
        dt = [r for r in results if r["pattern_name"] == "double_top"][0]
        assert dt["failure_rate"] == 75.0

    def test_avg_duration_calculation(self):
        preds = [_make_prediction({"id": "p1", "pattern_snapshot": '{"strongest_pattern": "triangle"}'})]
        outcomes = {"p1": _make_outcome({"prediction_id": "p1"})}
        results = PatternPerformanceAnalyzer.compute_pattern_performance(preds, outcomes)
        tri = [r for r in results if r["pattern_name"] == "triangle"][0]
        assert tri["avg_duration_hours"] >= 0

    def test_pattern_extraction_from_list(self):
        snapshot = '[{"name": "hammer"}, {"name": "shooting_star"}]'
        patterns = PatternPerformanceAnalyzer.extract_patterns_from_snapshot(snapshot)
        assert "hammer" in patterns

    def test_pattern_deduplication(self):
        snapshot = '{"strongest_pattern": "bull_flag", "chart_patterns": [{"name": "bull_flag"}]}'
        patterns = PatternPerformanceAnalyzer.extract_patterns_from_snapshot(snapshot)
        assert len(patterns) == len(set(patterns))
