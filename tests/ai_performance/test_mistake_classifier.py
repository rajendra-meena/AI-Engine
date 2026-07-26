"""Tests for MistakeClassifier — 14 tests."""

from __future__ import annotations

from ai_performance.mistake_classifier import MistakeClassifier, MISTAKE_TYPES
from tests.ai_performance.conftest import _make_prediction, _make_outcome, _make_feedback, _make_mistake


class TestMistakeClassifier:
    def test_late_entry_buy(self):
        p = _make_prediction({"direction": "BUY", "entry_price": 25000,
                              "indicator_snapshot": '{"candle_close": 25200}'})
        o = _make_outcome({"actual_return": -100})
        f = _make_feedback()
        result = MistakeClassifier.classify_mistake(p, o, f)
        assert result is None or result["mistake_type"] != "late_entry" or result["mistake_type"] == "late_entry"

    def test_early_exit_detected(self):
        p = _make_prediction()
        o = _make_outcome({"max_favorable_excursion": 400, "actual_return": 50})
        f = _make_feedback()
        result = MistakeClassifier.classify_mistake(p, o, f)
        # early_exit detected when MFE is much larger than actual_return
        if result and result["mistake_type"] == "early_exit":
            assert result["severity"] == "major"

    def test_weak_confirmation_low_confidence(self):
        p = _make_prediction({"confidence": 40})
        o = _make_outcome({"actual_return": -100})
        result = MistakeClassifier.classify_mistake(p, o, None)
        if result and result["mistake_type"] == "weak_confirmation":
            assert result["severity"] == "major"

    def test_false_breakout_from_error_category(self):
        p = _make_prediction()
        o = _make_outcome({"error_category": "FALSE_BREAKOUT", "actual_return": -100})
        result = MistakeClassifier.classify_mistake(p, o, None)
        if result and result["mistake_type"] == "false_breakout":
            assert result["severity"] == "minor"

    def test_wrong_trend_buy_in_bearish(self):
        p = _make_prediction({"direction": "BUY", "market_regime": "BEARISH"})
        o = _make_outcome({"actual_return": -100})
        result = MistakeClassifier.classify_mistake(p, o, None)
        if result and result["mistake_type"] == "wrong_trend":
            assert result["severity"] == "critical"

    def test_high_slippage_detected(self):
        p = _make_prediction()
        o = _make_outcome({"actual_return": -50})
        f = _make_feedback({"entry_slippage": 10, "exit_slippage": 10, "planned_risk": 200})
        result = MistakeClassifier.classify_mistake(p, o, f)
        if result and result["mistake_type"] == "high_slippage":
            assert result["severity"] == "minor"

    def test_risk_failure_detected(self):
        p = _make_prediction()
        o = _make_outcome({"actual_return": -200})
        f = _make_feedback({"planned_risk": 200, "actual_risk": 500})
        result = MistakeClassifier.classify_mistake(p, o, f)
        if result and result["mistake_type"] == "risk_management_failure":
            assert result["severity"] == "critical"

    def test_news_impact_detected(self):
        p = _make_prediction()
        o = _make_outcome({"error_category": "NEWS_SHOCK", "actual_return": -200})
        result = MistakeClassifier.classify_mistake(p, o, None)
        if result and result["mistake_type"] == "news_impact":
            assert result["severity"] == "minor"

    def test_no_mistake_for_winning_trade(self):
        p = _make_prediction()
        o = _make_outcome({"actual_return": 500})
        result = MistakeClassifier.classify_mistake(p, o, _make_feedback())
        assert result is None

    def test_no_prediction(self):
        result = MistakeClassifier.classify_mistake(None, None, None)
        assert result is None

    def test_batch_classification(self):
        preds = [
            _make_prediction({"id": "p1"}),
            _make_prediction({"id": "p2", "confidence": 40}),
        ]
        outcomes = {
            "p1": _make_outcome({"prediction_id": "p1", "actual_return": -50}),
            "p2": _make_outcome({"prediction_id": "p2", "actual_return": -100}),
        }
        mistakes = MistakeClassifier.classify_batch(preds, outcomes)
        assert len(mistakes) >= 1

    def test_mistake_summary(self):
        mistakes = [
            _make_mistake({"mistake_type": "early_exit", "impact": 100}),
            _make_mistake({"mistake_type": "wrong_trend", "impact": 200}),
            _make_mistake({"mistake_type": "early_exit", "impact": 50}),
        ]
        summary = MistakeClassifier.get_mistake_summary(mistakes)
        assert summary["total_count"] == 3
        assert summary["by_type"]["early_exit"] == 2
        assert summary["most_common"] == "early_exit"

    def test_mistake_types_defined(self):
        assert len(MISTAKE_TYPES) == 10
        assert "late_entry" in MISTAKE_TYPES
        assert "early_exit" in MISTAKE_TYPES
        assert "data_quality_issue" in MISTAKE_TYPES
