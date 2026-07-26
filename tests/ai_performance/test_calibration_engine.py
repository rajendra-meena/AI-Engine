"""Tests for ConfidenceCalibrationEngine — 12 tests."""

from __future__ import annotations

from ai_performance.calibration_engine import ConfidenceCalibrationEngine
from tests.ai_performance.conftest import _make_prediction, _make_outcome


class TestCalibrationEngine:
    def test_reliability_curve_structure(self):
        preds = [_make_prediction({"id": "p1", "confidence": 75}), _make_prediction({"id": "p2", "confidence": 55})]
        outcomes = {"p1": _make_outcome({"prediction_id": "p1", "actual_return": 200}), "p2": _make_outcome({"prediction_id": "p2", "actual_return": -50})}
        curve = ConfidenceCalibrationEngine.compute_reliability_curve(preds, outcomes)
        assert len(curve) == 10
        assert curve[7]["count"] > 0  # 70-80% bucket
        assert curve[5]["count"] > 0  # 50-60% bucket

    def test_reliability_curve_bucket_assignment(self):
        preds = [_make_prediction({"id": "p1", "confidence": 85})]
        outcomes = {"p1": _make_outcome({"prediction_id": "p1", "actual_return": 200})}
        curve = ConfidenceCalibrationEngine.compute_reliability_curve(preds, outcomes)
        bucket = curve[8]  # 80-90%
        assert bucket["count"] == 1

    def test_calibration_error_computation(self):
        preds = [_make_prediction({"id": "p1", "confidence": 80})]
        outcomes = {"p1": _make_outcome({"prediction_id": "p1", "actual_return": 200})}
        result = ConfidenceCalibrationEngine.compute_calibration_error(preds, outcomes)
        assert "ece" in result
        assert "mce" in result
        assert result["sample_count"] >= 1

    def test_overconfident_detection(self):
        preds = [_make_prediction({"id": f"p{i}", "confidence": 90}) for i in range(10)]
        outcomes = {f"p{i}": _make_outcome({"prediction_id": f"p{i}", "actual_return": -50}) for i in range(10)}
        bias = ConfidenceCalibrationEngine.detect_bias(preds, outcomes)
        assert bias == "overconfident"

    def test_underconfident_detection(self):
        preds = [_make_prediction({"id": f"p{i}", "confidence": 30}) for i in range(10)]
        outcomes = {f"p{i}": _make_outcome({"prediction_id": f"p{i}", "actual_return": 200}) for i in range(10)}
        bias = ConfidenceCalibrationEngine.detect_bias(preds, outcomes)
        assert bias == "underconfident"

    def test_calibrated_detection(self):
        preds = [_make_prediction({"id": f"p{i}", "confidence": 80}) for i in range(10)]
        outcomes = {f"p{i}": _make_outcome({"prediction_id": f"p{i}", "actual_return": 200 if i < 8 else -50}) for i in range(10)}
        bias = ConfidenceCalibrationEngine.detect_bias(preds, outcomes)
        assert bias in ("calibrated", "overconfident", "underconfident")

    def test_confidence_accuracy_calculation(self):
        preds = [_make_prediction({"id": f"p{i}", "confidence": 70}) for i in range(10)]
        outcomes = {f"p{i}": _make_outcome({"prediction_id": f"p{i}", "actual_return": 200}) for i in range(7)}
        for i in range(7, 10):
            outcomes[f"p{i}"] = _make_outcome({"prediction_id": f"p{i}", "actual_return": -100})
        acc = ConfidenceCalibrationEngine.compute_confidence_accuracy(preds, outcomes)
        assert 0 <= acc <= 100

    def test_empty_predictions(self):
        result = ConfidenceCalibrationEngine.compute_calibration_error([])
        assert result["sample_count"] == 0
        assert result["ece"] == 0

    def test_bias_magnitude_calculation(self):
        preds = [_make_prediction({"id": f"p{i}", "confidence": 90}) for i in range(5)]
        outcomes = {f"p{i}": _make_outcome({"prediction_id": f"p{i}", "actual_return": -50}) for i in range(5)}
        result = ConfidenceCalibrationEngine.compute_calibration_error(preds, outcomes)
        assert result["bias_magnitude"] != 0

    def test_single_prediction_handling(self):
        preds = [_make_prediction({"id": "p1", "confidence": 65})]
        outcomes = {"p1": _make_outcome({"prediction_id": "p1", "actual_return": 100})}
        curve = ConfidenceCalibrationEngine.compute_reliability_curve(preds, outcomes)
        bucket = [b for b in curve if b["count"] > 0][0]
        assert bucket["min"] == 60

    def test_reliability_curve_includes_bucket_label(self):
        preds = [_make_prediction({"id": "p1", "confidence": 50})]
        curve = ConfidenceCalibrationEngine.compute_reliability_curve(preds)
        bucket = [b for b in curve if b["count"] > 0][0]
        assert "bucket_label" in bucket
