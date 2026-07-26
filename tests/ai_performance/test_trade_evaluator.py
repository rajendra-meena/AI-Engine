"""Tests for TradeEvaluator — 14 tests."""

from __future__ import annotations

from ai_performance.trade_evaluator import TradeEvaluator
from tests.ai_performance.conftest import _make_prediction, _make_outcome, _make_feedback


class TestTradeEvaluator:
    def test_entry_accuracy_winning_trade(self):
        p = _make_prediction()
        o = _make_outcome({"actual_return": 500})
        result = TradeEvaluator.evaluate_single(p, o, _make_feedback())
        assert result["entry_accuracy"] >= 80
        assert 0 <= result["overall_score"] <= 100

    def test_entry_accuracy_losing_trade(self):
        p = _make_prediction()
        o = _make_outcome({"actual_return": -200})
        result = TradeEvaluator.evaluate_single(p, o, _make_feedback())
        assert result["entry_accuracy"] < 80

    def test_exit_quality_with_mfe(self):
        p = _make_prediction()
        o = _make_outcome({"max_favorable_excursion": 400, "actual_return": 300})
        result = TradeEvaluator.evaluate_single(p, o, _make_feedback())
        assert result["exit_quality"] >= 70

    def test_exit_quality_low_capture(self):
        p = _make_prediction()
        o = _make_outcome({"max_favorable_excursion": 400, "actual_return": 50})
        result = TradeEvaluator.evaluate_single(p, o, _make_feedback())
        assert result["exit_quality"] < 50

    def test_sl_quality_within_range(self):
        p = _make_prediction()
        o = _make_outcome({"max_adverse_excursion": -50, "stop_loss_hit": 0})
        result = TradeEvaluator.evaluate_single(p, o, _make_feedback())
        assert result["sl_quality"] >= 70

    def test_sl_quality_hit(self):
        p = _make_prediction()
        o = _make_outcome({"stop_loss_hit": 1, "max_adverse_excursion": -300})
        result = TradeEvaluator.evaluate_single(p, o, _make_feedback())
        assert result["sl_quality"] < 50

    def test_target_quality_hit(self):
        p = _make_prediction()
        o = _make_outcome({"target_hit": 1})
        result = TradeEvaluator.evaluate_single(p, o, _make_feedback())
        assert result["target_quality"] == 100

    def test_mfe_mae_ratio_favorable(self):
        p = _make_prediction()
        o = _make_outcome({"max_favorable_excursion": 400, "max_adverse_excursion": -50})
        result = TradeEvaluator.evaluate_single(p, o, _make_feedback())
        assert result["mfe_mae_ratio"] >= 80

    def test_slippage_impact_calculation(self):
        f = _make_feedback({"entry_slippage": 5, "exit_slippage": 5, "planned_risk": 200})
        p = _make_prediction()
        o = _make_outcome()
        result = TradeEvaluator.evaluate_single(p, o, f)
        assert result["slippage_impact"] > 0

    def test_overall_score_winning_trade(self):
        p = _make_prediction()
        o = _make_outcome({"actual_return": 500, "max_favorable_excursion": 600, "max_adverse_excursion": -30})
        f = _make_feedback({"entry_slippage": 1, "exit_slippage": 1})
        result = TradeEvaluator.evaluate_single(p, o, f)
        assert result["overall_score"] >= 65
        assert result["outcome_class"] in ("Excellent", "Good")

    def test_overall_score_losing_trade(self):
        p = _make_prediction({"entry_price": 25000, "stop_loss": 24900, "target": 25300})
        o = _make_outcome({"actual_return": -300, "max_favorable_excursion": 10, "max_adverse_excursion": -400, "stop_loss_hit": 1})
        result = TradeEvaluator.evaluate_single(p, o, _make_feedback({"gross_pnl": -300, "net_pnl": -302}))
        assert result["overall_score"] < 60
        assert result["outcome_class"] in ("Average", "Poor", "Failed")

    def test_classify_excellent(self):
        assert TradeEvaluator.classify_outcome(90) == "Excellent"
        assert TradeEvaluator.classify_outcome(85) == "Excellent"

    def test_classify_failed(self):
        assert TradeEvaluator.classify_outcome(10) == "Failed"
        assert TradeEvaluator.classify_outcome(24) == "Failed"

    def test_evaluate_batch(self):
        preds = [_make_prediction({"id": "p1"}), _make_prediction({"id": "p2"})]
        outcomes = {"p1": _make_outcome({"prediction_id": "p1"}), "p2": _make_outcome({"prediction_id": "p2", "actual_return": -100})}
        feedbacks = {"p1": _make_feedback({"prediction_id": "p1"}), "p2": _make_feedback({"prediction_id": "p2"})}
        results = TradeEvaluator.evaluate_batch(preds, outcomes, feedbacks)
        assert len(results) == 2
        assert all("overall_score" in r for r in results)
        assert all("outcome_class" in r for r in results)

    def test_no_prediction(self):
        result = TradeEvaluator.evaluate_single(None, None, None)
        assert result["overall_score"] == 0
        assert result["outcome_class"] == "Failed"
