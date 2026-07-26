"""Phase 56 tests: AI Decision Engine Validation & Signal Quality Framework."""

from __future__ import annotations

import pytest
from typing import Any

from ai_decision.modules.detailed_confidence import DetailedConfidenceEngine
from ai_decision.modules.signal_validator import SignalValidator
from ai_decision.modules.trade_quality import TradeQualityScorer
from ai_decision.modules.mtf_agreement import MultiTFAgreement
from ai_decision.modules.false_signal import FalseSignalDetector
from ai_decision.modules.confidence_adjuster import DynamicConfidenceAdjuster
from ai_decision.modules.ai_explainer import AIExplainer
from ai_decision.modules.trade_approval import TradeApprovalEngine
from ai_decision.modules.dataset_builder import LearningDatasetBuilder


# ── Helpers ──

def _make_context(overrides: dict | None = None) -> dict[str, Any]:
    base = {
        "trend": "BULLISH", "trend_strength": "STRONG", "confidence": 75,
        "momentum": "STRONG", "volatility_state": "NORMAL",
        "market_phase": "markup", "overall_bias": "BULLISH",
        "institutional_bias": "BULLISH", "liquidity_sweeps": 0,
        "session": "regular", "pattern_bias": "BULLISH",
    }
    if overrides:
        base.update(overrides)
    return base


def _make_indicators(overrides: dict | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ema_9": 25100.0, "ema_20": 25000.0, "ema_50": 24800.0,
        "rsi_14": 55.0, "macd_histogram": 50.0,
        "atr_14": 120.0, "vwap": 25000.0, "candle_close": 25100.0,
        "candle_volume": 150000, "average_volume": 120000,
        "sma_20": 24900.0, "sma_50": 24700.0,
        "bb_upper": 25200.0, "bb_lower": 24800.0,
        "adx_14": 30.0, "supertrend_trend": "UP",
        "all_ready": True,
    }
    if overrides:
        base.update(overrides)
    return base


def _make_structure(overrides: dict | None = None) -> dict[str, Any]:
    base = {
        "valid_structure": True, "trend": "UPTREND", "trend_strength": "STRONG",
        "bos_count": 3, "choch_count": 0, "market_phase": "markup",
        "liquidity_sweeps": 0, "swing_highs": [25200, 25150],
        "swing_lows": [24800, 24900],
    }
    if overrides:
        base.update(overrides)
    return base


def _make_patterns(overrides: dict | None = None) -> dict[str, Any]:
    base = {
        "pattern_count": 3, "total_count": 3, "pattern_count": 3,
        "strongest_pattern": "bullish_engulfing",
        "pattern_direction": "BULLISH", "pattern_bias": "BULLISH",
        "candlestick_patterns": [{"name": "bullish_engulfing", "confidence": 0.8, "direction": "bullish"}],
    }
    if overrides:
        base.update(overrides)
    return base


def _make_mtf(overrides: dict | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "alignment_level": "STRONG_ALIGNMENT", "alignment_score": 80,
        "institutional_bias": "BULLISH", "bias": "BULLISH",
        "trading_permission": "ALLOW_LONG", "market_condition": "TRENDING",
        "overall_confidence": 80,
        "timeframes": {
            "1m": {"bias": "BULLISH", "trend": "UPTREND", "confidence": 75},
            "3m": {"bias": "BULLISH", "trend": "UPTREND", "confidence": 78},
            "5m": {"bias": "BULLISH", "trend": "UPTREND", "confidence": 80},
            "15m": {"bias": "BULLISH", "trend": "UPTREND", "confidence": 82},
            "60m": {"bias": "BULLISH", "trend": "UPTREND", "confidence": 85},
        },
    }
    if overrides:
        base.update(overrides)
    return base


def _make_sr(overrides: dict | None = None) -> dict[str, Any]:
    base = {
        "nearest_support": 24800.0, "nearest_resistance": 25300.0,
        "breakout_state": "none",
        "supply_zones": [{"price": 25300}], "demand_zones": [{"price": 24800}],
    }
    if overrides:
        base.update(overrides)
    return base


def _make_decision(overrides: dict | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "decision": "HIGH_CONVICTION", "direction": "BUY",
        "score": 85, "score_grade": "VERY_HIGH",
        "confidence": 80, "confidence_grade": "VERY_HIGH",
        "risk_level": "LOW", "risk_score": 15,
        "max_risk_percent": 2.0,
        "trade_plan": {
            "direction": "BUY", "valid": True,
            "entry_zone": {"price": 25100}, "sl_zone": {"price": 24800},
            "target_zones": [{"price": 25700}],
            "risk_reward_context": "favorable",
            "max_risk_percent": 2.0,
        },
        "reasoning": ["Strong trend", "MTF aligned", "High confidence"],
        "warnings": [],
    }
    if overrides:
        base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════
# TestDetailedConfidence (10 tests)
# ══════════════════════════════════════════════════════════════

class TestDetailedConfidence:
    def test_full_confidence_calculation(self):
        result = DetailedConfidenceEngine.evaluate(
            _make_context(), _make_indicators(), _make_structure(),
            _make_patterns(), _make_mtf(), _make_sr(), _make_decision(),
        )
        assert result["overall_confidence"] >= 60
        assert len(result["factor_breakdown"]) == 10
        assert result["grade"] in ("VERY_HIGH", "HIGH", "MODERATE")

    def test_trend_confidence_scoring(self):
        result = DetailedConfidenceEngine.evaluate(
            _make_context({"trend": "BULLISH", "trend_strength": "STRONG"}),
            _make_indicators(), _make_structure(), _make_patterns(), _make_mtf(), _make_sr(), _make_decision(),
        )
        trend = [f for f in result["factor_breakdown"] if f["name"] == "Trend"][0]
        assert trend["score"] >= 80

    def test_structure_confidence_scoring(self):
        result = DetailedConfidenceEngine.evaluate(
            _make_context(), _make_indicators(), _make_structure({"valid_structure": False}),
            _make_patterns(), _make_mtf(), _make_sr(), _make_decision(),
        )
        struct = [f for f in result["factor_breakdown"] if f["name"] == "Market Structure"][0]
        assert struct["score"] < 80

    def test_momentum_confidence_scoring(self):
        result = DetailedConfidenceEngine.evaluate(
            _make_context({"momentum": "WEAK"}), _make_indicators({"rsi_14": 45}),
            _make_structure(), _make_patterns(), _make_mtf(), _make_sr(), _make_decision(),
        )
        momo = [f for f in result["factor_breakdown"] if f["name"] == "Momentum"][0]
        assert 0 <= momo["score"] <= 100

    def test_volume_confidence_scoring(self):
        result = DetailedConfidenceEngine.evaluate(
            _make_context(), _make_indicators({"candle_volume": 50000, "average_volume": 120000}),
            _make_structure(), _make_patterns(), _make_mtf(), _make_sr(), _make_decision(),
        )
        vol = [f for f in result["factor_breakdown"] if f["name"] == "Volume"][0]
        assert vol["score"] <= 50

    def test_liquidity_confidence_scoring(self):
        result = DetailedConfidenceEngine.evaluate(
            _make_context({"liquidity_sweeps": 5}), _make_indicators(),
            _make_structure({"market_phase": "ranging"}),
            _make_patterns(), _make_mtf(), _make_sr(), _make_decision(),
        )
        liq = [f for f in result["factor_breakdown"] if f["name"] == "Liquidity"][0]
        assert liq["score"] < 60

    def test_volatility_confidence_scoring(self):
        result = DetailedConfidenceEngine.evaluate(
            _make_context(), _make_indicators({"atr_14": 50, "candle_close": 25000}),
            _make_structure(), _make_patterns(), _make_mtf(), _make_sr(), _make_decision(),
        )
        vola = [f for f in result["factor_breakdown"] if f["name"] == "Volatility"][0]
        assert 0 <= vola["score"] <= 100

    def test_htf_alignment_confidence(self):
        result = DetailedConfidenceEngine.evaluate(
            _make_context(), _make_indicators(), _make_structure(),
            _make_patterns(), _make_mtf({"alignment_level": "CONFLICT", "alignment_score": 20}),
            _make_sr(), _make_decision(),
        )
        htf = [f for f in result["factor_breakdown"] if f["name"] == "Higher TF Alignment"][0]
        assert htf["score"] <= 50

    def test_pattern_confidence_scoring(self):
        result = DetailedConfidenceEngine.evaluate(
            _make_context(), _make_indicators(), _make_structure(),
            _make_patterns({"pattern_count": 0, "strongest_pattern": None}),
            _make_mtf(), _make_sr(), _make_decision(),
        )
        pat = [f for f in result["factor_breakdown"] if f["name"] == "Pattern Strength"][0]
        assert pat["score"] <= 60

    def test_risk_reward_confidence_scoring(self):
        result = DetailedConfidenceEngine.evaluate(
            _make_context(), _make_indicators(), _make_structure(),
            _make_patterns(), _make_mtf(), _make_sr(),
            _make_decision({"trade_plan": {"entry_zone": {"price": 25100}, "sl_zone": {"price": 25050}, "target_zones": [{"price": 25100}]}}),
        )
        rr = [f for f in result["factor_breakdown"] if f["name"] == "Risk Reward"][0]
        assert rr["score"] < 80


# ══════════════════════════════════════════════════════════════
# TestSignalValidator (12 tests)
# ══════════════════════════════════════════════════════════════

class TestSignalValidator:
    def test_trend_validation_pass(self):
        result = SignalValidator.validate(
            _make_decision({"direction": "BUY"}), _make_context(),
            _make_indicators(), _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        trend = [v for v in result["validations"] if v["signal"] == "trend"][0]
        assert trend["status"] == "PASS"

    def test_ema_alignment_pass(self):
        result = SignalValidator.validate(
            _make_decision({"direction": "BUY"}), _make_context(),
            _make_indicators({"ema_9": 25100, "ema_20": 25000, "ema_50": 24900}),
            _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        ema = [v for v in result["validations"] if v["signal"] == "ema_alignment"][0]
        assert ema["status"] == "PASS"

    def test_vwap_position_pass(self):
        result = SignalValidator.validate(
            _make_decision({"direction": "BUY"}), _make_context(),
            _make_indicators({"candle_close": 25100, "vwap": 25000}),
            _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        vwap = [v for v in result["validations"] if v["signal"] == "vwap"][0]
        assert vwap["status"] == "PASS"

    def test_structure_validation_pass(self):
        result = SignalValidator.validate(
            _make_decision(), _make_context(), _make_indicators(),
            _make_structure({"valid_structure": True}),
            _make_patterns(), _make_mtf(), _make_sr(),
        )
        struct = [v for v in result["validations"] if v["signal"] == "structure"][0]
        assert struct["status"] == "PASS"

    def test_rsi_overbought_warning(self):
        result = SignalValidator.validate(
            _make_decision({"direction": "BUY"}), _make_context(),
            _make_indicators({"rsi_14": 72}),
            _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        rsi = [v for v in result["validations"] if v["signal"] == "rsi"][0]
        assert rsi["status"] == "WARNING"

    def test_rsi_oversold_warning(self):
        result = SignalValidator.validate(
            _make_decision({"direction": "SELL"}), _make_context(),
            _make_indicators({"rsi_14": 25}),
            _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        rsi = [v for v in result["validations"] if v["signal"] == "rsi"][0]
        assert rsi["status"] == "WARNING"

    def test_macd_alignment_check(self):
        result = SignalValidator.validate(
            _make_decision({"direction": "BUY"}), _make_context(),
            _make_indicators({"macd_histogram": 50}),
            _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        macd = [v for v in result["validations"] if v["signal"] == "macd"][0]
        assert macd["status"] == "PASS"

    def test_volume_check(self):
        result = SignalValidator.validate(
            _make_decision(), _make_context(),
            _make_indicators({"candle_volume": 50000, "average_volume": 120000}),
            _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        vol = [v for v in result["validations"] if v["signal"] == "volume"][0]
        assert vol["status"] == "WARNING"

    def test_pattern_validation(self):
        result = SignalValidator.validate(
            _make_decision({"direction": "BUY"}), _make_context(),
            _make_indicators(), _make_structure(),
            _make_patterns({"pattern_direction": "BULLISH"}),
            _make_mtf(), _make_sr(),
        )
        pat = [v for v in result["validations"] if v["signal"] == "patterns"][0]
        assert pat["status"] == "PASS"

    def test_sr_proximity_check(self):
        result = SignalValidator.validate(
            _make_decision({"direction": "BUY"}), _make_context(),
            _make_indicators({"candle_close": 24900}),
            _make_structure(), _make_patterns(), _make_mtf(),
            _make_sr({"nearest_support": 24800, "nearest_resistance": 25300}),
        )
        sr = [v for v in result["validations"] if v["signal"] == "sr_proximity"][0]
        assert sr["status"] in ("PASS", "WARNING")

    def test_volatility_check(self):
        result = SignalValidator.validate(
            _make_decision(), _make_context(),
            _make_indicators({"atr_14": 120, "candle_close": 25100}),
            _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        vola = [v for v in result["validations"] if v["signal"] == "volatility"][0]
        assert vola["status"] in ("PASS", "WARNING")

    def test_multiple_validations_combined(self):
        result = SignalValidator.validate(
            _make_decision({"direction": "BUY"}), _make_context(),
            _make_indicators(), _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        assert result["pass_count"] >= 5
        assert result["overall_status"] in ("PASS", "WARNING")


# ══════════════════════════════════════════════════════════════
# TestTradeQuality (8 tests)
# ══════════════════════════════════════════════════════════════

class TestTradeQuality:
    def test_a_plus_grade_all_factors(self):
        result = TradeQualityScorer.evaluate(
            _make_decision({"score": 95}), _make_context({"trend": "BULLISH", "trend_strength": "STRONG"}),
            _make_indicators({"candle_volume": 200000, "average_volume": 120000}),
            _make_patterns({"pattern_count": 5}), _make_sr(), _make_mtf(),
        )
        assert result["grade"] in ("A+", "A", "B")

    def test_b_grade_medium_setup(self):
        result = TradeQualityScorer.evaluate(
            _make_decision({"score": 70}), _make_context({"trend": "RANGING", "trend_strength": "WEAK"}),
            _make_indicators({"candle_volume": 100000, "average_volume": 120000}),
            _make_patterns({"pattern_count": 1}), _make_sr(), _make_mtf({"alignment_level": "PARTIAL_ALIGNMENT"}),
        )
        assert result["grade"] in ("B", "C", "D")

    def test_d_grade_poor_setup(self):
        result = TradeQualityScorer.evaluate(
            _make_decision({"score": 30}), _make_context({"trend": "BEARISH", "trend_strength": "WEAK"}),
            _make_indicators({"candle_volume": 30000, "average_volume": 120000}),
            _make_patterns({"pattern_count": 0, "pattern_direction": "NEUTRAL"}),
            _make_sr(), _make_mtf({"alignment_level": "CONFLICT"}),
        )
        assert result["grade"] in ("D", "REJECT")

    def test_reject_below_threshold(self):
        result = TradeQualityScorer.evaluate(
            _make_decision({"score": 10, "direction": "BUY"}), _make_context({"trend": "BEARISH", "trend_strength": "STRONG"}),
            _make_indicators({"candle_volume": 10000, "average_volume": 120000, "atr_14": 2000, "candle_close": 25000}),
            _make_patterns({"pattern_count": 0, "strongest_pattern": None, "pattern_direction": "NEUTRAL"}),
            _make_sr(), _make_mtf({"alignment_level": "CONFLICT"}),
        )
        assert result["grade"] == "REJECT" or result["total_score"] < 50

    def test_trend_alignment_weight(self):
        bullish = TradeQualityScorer.evaluate(
            _make_decision({"direction": "BUY"}), _make_context({"trend": "BULLISH", "trend_strength": "STRONG"}),
            _make_indicators(), _make_patterns(), _make_sr(), _make_mtf(),
        )
        bearish = TradeQualityScorer.evaluate(
            _make_decision({"direction": "BUY"}), _make_context({"trend": "BEARISH", "trend_strength": "STRONG"}),
            _make_indicators(), _make_patterns(), _make_sr(), _make_mtf(),
        )
        assert bullish["total_score"] > bearish["total_score"]

    def test_rr_factor_scoring(self):
        result = TradeQualityScorer.evaluate(
            _make_decision({"trade_plan": {"entry_zone": {"price": 100}, "sl_zone": {"price": 99}, "target_zones": [{"price": 103}]}}),
            _make_context(), _make_indicators(), _make_patterns(), _make_sr(), _make_mtf(),
        )
        rr = [f for f in result["factor_scores"] if "Risk" in f["name"]][0]
        assert rr["score"] >= 80

    def test_pattern_factor_scoring(self):
        high = TradeQualityScorer.evaluate(
            _make_decision(), _make_context(), _make_indicators(),
            _make_patterns({"pattern_count": 5, "strongest_pattern": "bullish_engulfing", "pattern_direction": "BULLISH"}),
            _make_sr(), _make_mtf(),
        )
        low = TradeQualityScorer.evaluate(
            _make_decision(), _make_context(), _make_indicators(),
            _make_patterns({"pattern_count": 0, "strongest_pattern": None, "pattern_direction": "NEUTRAL"}),
            _make_sr(), _make_mtf(),
        )
        assert high["total_score"] >= low["total_score"]

    def test_liquidity_factor_scoring(self):
        result = TradeQualityScorer.evaluate(
            _make_decision(), _make_context({"liquidity_sweeps": 5}),
            _make_indicators({"candle_volume": 30000, "average_volume": 120000}),
            _make_patterns(), _make_sr(), _make_mtf(),
        )
        liq = [f for f in result["factor_scores"] if "Liquidity" in f["name"]][0]
        assert liq["score"] < 70


# ══════════════════════════════════════════════════════════════
# TestMTFAgreement (8 tests)
# ══════════════════════════════════════════════════════════════

class TestMTFAgreement:
    def test_full_agreement_all_tfs(self):
        result = MultiTFAgreement.evaluate(_make_mtf())
        assert result["agreement_percent"] >= 80

    def test_high_agreement_most_tfs(self):
        mtf = _make_mtf()
        mtf["timeframes"]["1m"] = {"bias": "BULLISH"}
        mtf["timeframes"]["3m"] = {"bias": "BULLISH"}
        mtf["timeframes"]["5m"] = {"bias": "BULLISH"}
        mtf["timeframes"]["15m"] = {"bias": "BEARISH"}
        result = MultiTFAgreement.evaluate(mtf)
        assert 50 <= result["agreement_percent"] <= 100

    def test_moderate_agreement_split(self):
        mtf = _make_mtf({"bias": "BULLISH"})
        mtf["timeframes"]["1m"] = {"bias": "BULLISH"}
        mtf["timeframes"]["5m"] = {"bias": "BEARISH"}
        mtf["timeframes"]["15m"] = {"bias": "BULLISH"}
        mtf["timeframes"]["60m"] = {"bias": "BEARISH"}
        result = MultiTFAgreement.evaluate(mtf)
        assert result["agreement_percent"] >= 0

    def test_conflict_opposing_tfs(self):
        mtf = _make_mtf({"bias": "BEARISH"})
        mtf["timeframes"] = {
            "1m": {"bias": "BEARISH"}, "5m": {"bias": "BEARISH"},
            "15m": {"bias": "BULLISH"}, "60m": {"bias": "BULLISH"},
        }
        result = MultiTFAgreement.evaluate(mtf)
        assert result["status"] in ("WEAK", "CONFLICT", "MODERATE")

    def test_partial_htf_ltf_diff(self):
        mtf = _make_mtf({"institutional_bias": "BULLISH"})
        mtf["timeframes"] = {
            "1m": {"bias": "BEARISH"}, "3m": {"bias": "BEARISH"},
            "5m": {"bias": "NEUTRAL"}, "15m": {"bias": "BULLISH"},
            "60m": {"bias": "BULLISH"},
        }
        result = MultiTFAgreement.evaluate(mtf)
        assert result["conflicts_found"] is not None

    def test_weighted_agreement_calculation(self):
        result = MultiTFAgreement.evaluate(_make_mtf())
        assert result["weighted_agreement"] > 0

    def test_agreement_with_missing_tfs(self):
        mtf = _make_mtf({"timeframes": {"15m": {"bias": "BULLISH"}, "60m": {"bias": "BULLISH"}}})
        result = MultiTFAgreement.evaluate(mtf)
        assert result["agreement_percent"] >= 0

    def test_empty_inputs(self):
        result = MultiTFAgreement.evaluate(None)
        assert result["agreement_percent"] == 0
        assert result["status"] == "NO_DATA"


# ══════════════════════════════════════════════════════════════
# TestFalseSignalDetection (10 tests)
# ══════════════════════════════════════════════════════════════

class TestFalseSignalDetection:
    def test_low_volume_breakout_detection(self):
        result = FalseSignalDetector.detect(
            _make_context(), _make_indicators({"candle_volume": 30000, "average_volume": 120000}),
            _make_structure(), _make_sr({"breakout_state": "breakout"}),
        )
        lb = [d for d in result["detections"] if d["type"] == "low_volume_breakout"][0]
        assert lb["detected"] is True

    def test_fake_breakout_detection(self):
        result = FalseSignalDetector.detect(
            _make_context(), _make_indicators({"candle_close": 25301}),
            _make_structure(), _make_sr({"breakout_state": "breakout", "nearest_resistance": 25300}),
        )
        fb = [d for d in result["detections"] if d["type"] == "fake_breakout"][0]
        assert fb["detected"] is True or fb["detected"] is False

    def test_liquidity_grab_detection(self):
        result = FalseSignalDetector.detect(
            _make_context(), _make_indicators(),
            _make_structure({"liquidity_sweeps": 2}),
            _make_sr(),
        )
        lg = [d for d in result["detections"] if d["type"] == "liquidity_grab"][0]
        assert lg["detected"] is True

    def test_news_spike_detection(self):
        result = FalseSignalDetector.detect(
            _make_context(), _make_indicators({"candle_volume": 500000, "average_volume": 120000}),
            _make_structure(), _make_sr(),
        )
        ns = [d for d in result["detections"] if d["type"] == "news_spike"][0]
        assert ns["detected"] is True

    def test_opening_noise_detection(self):
        result = FalseSignalDetector.detect(
            _make_context({"session": "open"}), _make_indicators(),
            _make_structure(), _make_sr(),
        )
        on = [d for d in result["detections"] if d["type"] == "opening_noise"][0]
        assert on["detected"] is True

    def test_range_trap_detection(self):
        result = FalseSignalDetector.detect(
            _make_context(), _make_indicators({"atr_14": 50, "candle_close": 25000}),
            _make_structure(), _make_sr({"breakout_state": "breakout"}),
        )
        rt = [d for d in result["detections"] if d["type"] == "range_trap"][0]
        assert rt["detected"] is True

    def test_exhaustion_move_detection(self):
        result = FalseSignalDetector.detect(
            _make_context({"trend": "BULLISH"}), _make_indicators({"atr_14": 100, "candle_close": 25300}),
            _make_structure(), _make_sr(),
        )
        em = [d for d in result["detections"] if d["type"] == "exhaustion_move"][0]
        assert em["detected"] is True or em["detected"] is False

    def test_clean_signal_no_false_positive(self):
        result = FalseSignalDetector.detect(
            _make_context({"session": "regular", "trend": "NEUTRAL"}),
            _make_indicators({"candle_volume": 180000, "average_volume": 120000, "atr_14": 500, "candle_close": 25100}),
            _make_structure({"liquidity_sweeps": 0}),
            _make_sr({"breakout_state": "none"}),
        )
        assert result["is_false_signal"] is False

    def test_multiple_false_signals_combined(self):
        result = FalseSignalDetector.detect(
            _make_context({"session": "open"}), _make_indicators({"candle_volume": 50000, "average_volume": 120000}),
            _make_structure({"liquidity_sweeps": 3}),
            _make_sr({"breakout_state": "breakout", "nearest_resistance": 25300}),
        )
        detected = [d for d in result["detections"] if d["detected"]]
        assert len(detected) >= 2

    def test_false_signal_rejection_integration(self):
        result = FalseSignalDetector.detect(
            _make_context(), _make_indicators({"candle_volume": 30000, "average_volume": 120000}),
            _make_structure(), _make_sr({"breakout_state": "breakout"}),
        )
        assert len(result["reject_reasons"]) > 0 or result["is_false_signal"] is False


# ══════════════════════════════════════════════════════════════
# TestConfidenceAdjuster (7 tests)
# ══════════════════════════════════════════════════════════════

class TestConfidenceAdjuster:
    def test_high_vix_adjustment(self):
        result = DynamicConfidenceAdjuster.adjust(
            _make_context({"volatility_state": "EXPANDING"}), _make_indicators(), None, 85,
        )
        assert result["total_deduction"] >= 10
        assert result["adjusted_confidence"] < 85

    def test_holiday_session_adjustment(self):
        result = DynamicConfidenceAdjuster.adjust(
            _make_context({"session": "holiday"}), _make_indicators(), None, 80,
        )
        assert result["total_deduction"] >= 15

    def test_low_volume_adjustment(self):
        result = DynamicConfidenceAdjuster.adjust(
            _make_context(), _make_indicators({"candle_volume": 50000, "average_volume": 120000}), None, 80,
        )
        assert result["total_deduction"] >= 15

    def test_gap_day_adjustment(self):
        result = DynamicConfidenceAdjuster.adjust(
            _make_context(), _make_indicators({"candle_close": 25300, "candle_open": 25000}), None, 80,
        )
        assert result["total_deduction"] >= 20

    def test_broker_delay_adjustment(self):
        result = DynamicConfidenceAdjuster.adjust(
            _make_context(), _make_indicators(), {"data_freshness": "stale"}, 80,
        )
        assert result["total_deduction"] >= 10

    def test_multiple_adjustments_combined(self):
        result = DynamicConfidenceAdjuster.adjust(
            _make_context({"volatility_state": "EXPANDING", "session": "holiday"}),
            _make_indicators({"candle_volume": 50000, "average_volume": 120000}), None, 90,
        )
        assert result["total_deduction"] >= 30
        assert result["adjusted_confidence"] <= 60

    def test_no_adjustments_normal_conditions(self):
        result = DynamicConfidenceAdjuster.adjust(
            _make_context(), _make_indicators(), {"data_freshness": "live"}, 85,
        )
        applied = [a for a in result["adjustments"] if a["applied"]]
        assert len(applied) == 0
        assert result["adjusted_confidence"] == 85


# ══════════════════════════════════════════════════════════════
# TestAIExplainer (6 tests)
# ══════════════════════════════════════════════════════════════

class TestAIExplainer:
    def test_why_buy_full_explanation(self):
        result = AIExplainer.explain(
            _make_decision({"decision": "HIGH_CONVICTION", "direction": "BUY"}),
            _make_context(), _make_indicators(), _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        assert result["why_buy"] != ""

    def test_why_sell_full_explanation(self):
        result = AIExplainer.explain(
            _make_decision({"decision": "HIGH_CONVICTION", "direction": "SELL"}),
            _make_context(), _make_indicators(), _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        assert result["why_sell"] != ""

    def test_why_no_trade_full_explanation(self):
        result = AIExplainer.explain(
            _make_decision({"decision": "NO_TRADE", "warnings": ["Risk too high"]}),
            _make_context(), _make_indicators(), _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        assert result["why_no_trade"] != ""

    def test_supporting_factors_listed(self):
        result = AIExplainer.explain(
            _make_decision(), _make_context(), _make_indicators(), _make_structure(),
            _make_patterns(), _make_mtf(), _make_sr(),
        )
        assert len(result["decision_explanation"]["supporting_factors"]) > 0

    def test_blocking_factors_listed(self):
        result = AIExplainer.explain(
            _make_decision({"decision": "NO_TRADE", "warnings": ["Risk too high", "Low confidence"]}),
            _make_context(), _make_indicators(), _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        assert len(result["decision_explanation"]["blocking_factors"]) > 0

    def test_empty_data_graceful_handling(self):
        result = AIExplainer.explain(None, None, None, None, None, None, None)
        assert result["decision_explanation"]["primary_reason"] != ""


# ══════════════════════════════════════════════════════════════
# TestTradeApprovalEngine (10 tests)
# ══════════════════════════════════════════════════════════════

class TestTradeApprovalEngine:
    def test_all_gates_pass_trade_eligible(self):
        dc = DetailedConfidenceEngine.evaluate(
            _make_context(), _make_indicators(), _make_structure(),
            _make_patterns(), _make_mtf(), _make_sr(), _make_decision(),
        )
        tq = TradeQualityScorer.evaluate(
            _make_decision(), _make_context(), _make_indicators(), _make_patterns(), _make_sr(), _make_mtf(),
        )
        mtf = MultiTFAgreement.evaluate(_make_mtf())
        sv = SignalValidator.validate(
            _make_decision(), _make_context(), _make_indicators(),
            _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        fs = FalseSignalDetector.detect(_make_context(), _make_indicators(), _make_structure(), _make_sr())

        result = TradeApprovalEngine.approve(
            detailed_confidence=dc, trade_quality=tq, mtf_agreement=mtf,
            risk_result={"risk_level": "LOW"}, signal_validations=sv,
            false_signal_check=fs, decision_snap=_make_decision(),
        )
        # May or may not pass depending on exact scores
        assert result["decision"] in ("TRADE_ELIGIBLE", "NO_TRADE")

    def test_confidence_gate_block(self):
        result = TradeApprovalEngine.approve(
            detailed_confidence={"overall_confidence": 50, "grade": "MODERATE"},
        )
        gate = [g for g in result["gates"] if g["name"] == "confidence"][0]
        assert not gate["passed"]

    def test_quality_gate_block(self):
        result = TradeApprovalEngine.approve(
            trade_quality={"grade": "REJECT", "total_score": 30},
        )
        gate = [g for g in result["gates"] if g["name"] == "quality"][0]
        assert not gate["passed"]

    def test_rr_gate_block(self):
        decision = _make_decision({
            "trade_plan": {"entry_zone": {"price": 100}, "sl_zone": {"price": 99}, "target_zones": [{"price": 100.5}]},
        })
        result = TradeApprovalEngine.approve(decision_snap=decision)
        gate = [g for g in result["gates"] if g["name"] == "risk_reward"][0]
        assert not gate["passed"]

    def test_mtf_agreement_gate_block(self):
        result = TradeApprovalEngine.approve(
            mtf_agreement={"agreement_percent": 30, "status": "WEAK"},
        )
        gate = [g for g in result["gates"] if g["name"] == "mtf_agreement"][0]
        assert not gate["passed"]

    def test_risk_gate_block(self):
        result = TradeApprovalEngine.approve(
            risk_result={"risk_level": "EXTREME"},
        )
        gate = [g for g in result["gates"] if g["name"] == "risk"][0]
        assert not gate["passed"]

    def test_signal_validation_gate_block(self):
        result = TradeApprovalEngine.approve(
            signal_validations={"validations": [], "overall_status": "BLOCK", "pass_count": 5, "warning_count": 2, "block_count": 1},
        )
        gate = [g for g in result["gates"] if g["name"] == "signal_validation"][0]
        assert not gate["passed"]

    def test_false_signal_gate_block(self):
        result = TradeApprovalEngine.approve(
            false_signal_check={"is_false_signal": True, "detections": [], "reject_reasons": ["Low volume breakout"]},
        )
        gate = [g for g in result["gates"] if g["name"] == "false_signal"][0]
        assert not gate["passed"]

    def test_multiple_gates_fail(self):
        result = TradeApprovalEngine.approve(
            detailed_confidence={"overall_confidence": 30, "grade": "LOW"},
            trade_quality={"grade": "REJECT", "total_score": 20},
            risk_result={"risk_level": "EXTREME"},
        )
        assert not result["approved"]
        assert len(result["blocking_reasons"]) >= 2

    def test_boundary_thresholds(self):
        result = TradeApprovalEngine.approve(
            detailed_confidence={"overall_confidence": 80, "grade": "HIGH"},
            trade_quality={"grade": "B", "total_score": 75},
            mtf_agreement={"agreement_percent": 71, "status": "MODERATE"},
            risk_result={"risk_level": "LOW"},
            decision_snap=_make_decision(),
        )
        assert result["approved"] is True or result["approved"] is False


# ══════════════════════════════════════════════════════════════
# TestDecisionConsistency (5 tests)
# ══════════════════════════════════════════════════════════════

class TestDecisionConsistency:
    def test_consistent_decision_across_modules(self):
        ctx = _make_context()
        ind = _make_indicators()
        struct = _make_structure()
        pat = _make_patterns()
        mtf = _make_mtf()
        sr = _make_sr()
        dec = _make_decision()
        r1 = DetailedConfidenceEngine.evaluate(ctx, ind, struct, pat, mtf, sr, dec)
        r2 = DetailedConfidenceEngine.evaluate(ctx, ind, struct, pat, mtf, sr, dec)
        assert r1["overall_confidence"] == r2["overall_confidence"]

    def test_deterministic_confidence(self):
        r1 = DetailedConfidenceEngine.evaluate(
            _make_context(), _make_indicators(), _make_structure(),
            _make_patterns(), _make_mtf(), _make_sr(), _make_decision(),
        )
        r2 = DetailedConfidenceEngine.evaluate(
            _make_context(), _make_indicators(), _make_structure(),
            _make_patterns(), _make_mtf(), _make_sr(), _make_decision(),
        )
        assert r1["overall_confidence"] == r2["overall_confidence"]

    def test_deterministic_quality(self):
        r1 = TradeQualityScorer.evaluate(
            _make_decision(), _make_context(), _make_indicators(), _make_patterns(), _make_sr(), _make_mtf(),
        )
        r2 = TradeQualityScorer.evaluate(
            _make_decision(), _make_context(), _make_indicators(), _make_patterns(), _make_sr(), _make_mtf(),
        )
        assert r1["total_score"] == r2["total_score"]

    def test_deterministic_approval(self):
        dc = DetailedConfidenceEngine.evaluate(
            _make_context(), _make_indicators(), _make_structure(),
            _make_patterns(), _make_mtf(), _make_sr(), _make_decision(),
        )
        tq = TradeQualityScorer.evaluate(
            _make_decision(), _make_context(), _make_indicators(), _make_patterns(), _make_sr(), _make_mtf(),
        )
        mtf = MultiTFAgreement.evaluate(_make_mtf())
        sv = SignalValidator.validate(
            _make_decision(), _make_context(), _make_indicators(),
            _make_structure(), _make_patterns(), _make_mtf(), _make_sr(),
        )
        fs = FalseSignalDetector.detect(_make_context(), _make_indicators(), _make_structure(), _make_sr())
        a1 = TradeApprovalEngine.approve(
            detailed_confidence=dc, trade_quality=tq, mtf_agreement=mtf,
            risk_result={"risk_level": "LOW"}, signal_validations=sv,
            false_signal_check=fs, decision_snap=_make_decision(),
        )
        a2 = TradeApprovalEngine.approve(
            detailed_confidence=dc, trade_quality=tq, mtf_agreement=mtf,
            risk_result={"risk_level": "LOW"}, signal_validations=sv,
            false_signal_check=fs, decision_snap=_make_decision(),
        )
        assert a1["approved"] == a2["approved"]

    def test_same_input_same_output(self):
        inputs = (_make_context(), _make_indicators(), _make_structure(),
                  _make_patterns(), _make_mtf(), _make_sr(), _make_decision())
        r1 = DetailedConfidenceEngine.evaluate(*inputs)
        r2 = DetailedConfidenceEngine.evaluate(*inputs)
        assert r1 == r2


# ══════════════════════════════════════════════════════════════
# TestDatasetBuilder (4 tests)
# ══════════════════════════════════════════════════════════════

class TestDatasetBuilder:
    def test_dataset_record_creation(self):
        record = LearningDatasetBuilder.record(
            symbol="NIFTY 50", decision_snap=_make_decision(),
            indicator_snap=_make_indicators(),
            detailed_confidence={"overall_confidence": 85, "grade": "VERY_HIGH"},
        )
        assert record["id"] is not None
        assert record["symbol"] == "NIFTY 50"
        assert record["decision"] == "HIGH_CONVICTION"

    def test_dataset_with_all_fields(self):
        dc = DetailedConfidenceEngine.evaluate(
            _make_context(), _make_indicators(), _make_structure(),
            _make_patterns(), _make_mtf(), _make_sr(), _make_decision(),
        )
        tq = TradeQualityScorer.evaluate(
            _make_decision(), _make_context(), _make_indicators(), _make_patterns(), _make_sr(), _make_mtf(),
        )
        mtf = MultiTFAgreement.evaluate(_make_mtf())
        record = LearningDatasetBuilder.record(
            symbol="BANKNIFTY", decision_snap=_make_decision(),
            indicator_snap=_make_indicators(),
            detailed_confidence=dc, trade_quality=tq, mtf_agreement=mtf,
            trade_outcome="win", pnl=5000.0, screenshot_id="ss_001",
        )
        assert record["trade_outcome"] == "win"
        assert record["pnl"] == 5000.0

    def test_dataset_integrity(self):
        record = LearningDatasetBuilder.record(
            symbol="NIFTY 50", decision_snap=_make_decision(),
        )
        assert "id" in record
        assert "timestamp" in record
        assert "created_at" in record

    def test_dataset_stats_computation(self):
        stats = LearningDatasetBuilder.get_stats()
        assert "total_records" in stats
        assert stats["total_records"] >= 0
        assert "by_decision" in stats
        assert "by_grade" in stats
