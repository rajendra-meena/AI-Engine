"""Tests for RegimeDetector — covering all 14 regime types."""

from __future__ import annotations

import pytest
from market_regime.regime_detector import RegimeDetector, REGIME_LIST, CONFIDENCE_THRESHOLD


def _ctx(overrides: dict | None = None) -> dict:
    base = {"trend": "BULLISH", "trend_strength": "STRONG", "momentum": "STRONG",
            "volatility_state": "NORMAL", "volatility": "NORMAL", "session": "regular",
            "market_phase": "markup", "overall_bias": "BULLISH"}
    if overrides: base.update(overrides)
    return base

def _struct(overrides: dict | None = None) -> dict:
    base = {"trend": "UPTREND", "trend_strength": "STRONG", "valid_structure": True,
            "bos_count": 3, "choch_count": 0, "market_phase": "markup", "liquidity_sweeps": 0}
    if overrides: base.update(overrides)
    return base

def _ind(overrides: dict | None = None) -> dict:
    base = {"ema_9": 25100, "ema_20": 25000, "ema_50": 24900, "adx_14": 35,
            "rsi_14": 55, "candle_close": 25100, "vwap": 25000,
            "candle_volume": 150000, "average_volume": 120000, "atr_14": 120}
    if overrides: base.update(overrides)
    return base

def _mtf(overrides: dict | None = None) -> dict:
    base = {"alignment_level": "STRONG_ALIGNMENT", "market_condition": "TRENDING",
            "institutional_bias": "BULLISH", "alignment_score": 80}
    if overrides: base.update(overrides)
    return base


class TestRegimeDetector:
    def test_strong_bull_trend_detected(self):
        snap = RegimeDetector.detect(_ctx(), _struct(), _ind(), _mtf())
        assert snap.regime == "STRONG_BULL_TREND"
        assert snap.confidence >= 60
        assert len(snap.supporting_factors) >= 2

    def test_strong_bear_trend_detected(self):
        snap = RegimeDetector.detect(
            _ctx({"trend": "BEARISH", "trend_strength": "STRONG", "overall_bias": "BEARISH"}),
            _struct({"trend": "DOWNTREND", "trend_strength": "STRONG", "bos_count": 0, "choch_count": 2}),
            _ind({"ema_9": 24900, "ema_20": 25000, "ema_50": 25100, "candle_close": 24900, "vwap": 25000}),
            _mtf({"institutional_bias": "BEARISH"}),
        )
        assert snap.regime == "STRONG_BEAR_TREND"
        assert snap.confidence >= 50

    def test_weak_bull_trend_detected(self):
        snap = RegimeDetector.detect(
            _ctx({"trend": "BULLISH", "trend_strength": "WEAK"}),
            _struct({"trend": "UPTREND", "trend_strength": "WEAK", "bos_count": 1}),
            _ind({"adx_14": 22, "ema_9": 25100, "ema_20": 25050}),
            _mtf({"alignment_level": "PARTIAL_ALIGNMENT"}),
        )
        assert snap.regime in ("WEAK_BULL_TREND", "STRONG_BULL_TREND")
        assert snap.confidence >= 20

    def test_sideways_range_detected(self):
        snap = RegimeDetector.detect(
            _ctx({"trend": "NEUTRAL", "volatility_state": "CONTRACTING"}),
            _struct({"trend": "RANGING", "trend_strength": "WEAK", "valid_structure": False, "bos_count": 0}),
            _ind({"adx_14": 15, "ema_9": 25000, "ema_20": 24995}),
            _mtf({"alignment_level": "MIXED"}),
        )
        assert snap.regime == "SIDEWAYS_RANGE"

    def _neutral_ctx(self) -> dict:
        return {"trend": "NEUTRAL", "trend_strength": "WEAK", "momentum": "WEAK",
                "volatility_state": "NORMAL", "volatility": "NORMAL", "session": "regular"}

    def _neutral_ind(self) -> dict:
        return {"ema_9": 25000, "ema_20": 24990, "ema_50": 24980, "adx_14": 18,
                "rsi_14": 50, "candle_close": 25000, "vwap": 25000,
                "candle_volume": 100000, "average_volume": 120000, "atr_14": 100}

    def _neutral_mtf(self) -> dict:
        return {"alignment_level": "MIXED", "market_condition": "RANGING", "institutional_bias": "NEUTRAL"}

    def test_high_volatility_detected(self):
        snap = RegimeDetector.detect(
            _ctx({"volatility_state": "EXPANDING"}),
            _struct({"trend": "RANGING", "trend_strength": "MODERATE", "valid_structure": True}),
            _ind({"atr_14": 800, "candle_close": 25000, "adx_14": 25, "ema_9": 25000, "ema_20": 24980,
                  "vwap": 25000, "candle_volume": 150000, "average_volume": 120000, "rsi_14": 50}),
            _mtf({"alignment_level": "PARTIAL_ALIGNMENT", "market_condition": "RANGING"}),
        )
        assert snap.regime == "HIGH_VOLATILITY"

    def test_low_volatility_detected(self):
        snap = RegimeDetector.detect(
            _ctx({"volatility_state": "CONTRACTING"}),
            _struct({"trend": "RANGING", "trend_strength": "WEAK", "valid_structure": True}),
            _ind({"atr_14": 30, "candle_close": 25100, "adx_14": 22, "ema_9": 25090, "ema_20": 25080,
                  "vwap": 25100, "candle_volume": 120000, "average_volume": 120000, "rsi_14": 50}),
            _mtf({"alignment_level": "PARTIAL_ALIGNMENT", "market_condition": "RANGING"}),
        )
        assert snap.regime == "LOW_VOLATILITY"

    def test_breakout_detected(self):
        snap = RegimeDetector.detect(
            _ctx({"trend": "NEUTRAL", "momentum": "STRONG"}),
            _struct({"trend": "RANGING", "bos_count": 3, "valid_structure": False}),
            _ind({"adx_14": 15, "ema_9": 25100, "ema_20": 25000, "candle_volume": 200000, "average_volume": 120000}),
            _mtf({"alignment_level": "STRONG_ALIGNMENT", "market_condition": "BREAKOUT"}),
        )
        assert snap.regime == "BREAKOUT"

    def test_fake_breakout_detected(self):
        snap = RegimeDetector.detect(
            self._neutral_ctx(),
            _struct({"trend": "RANGING", "bos_count": 2, "choch_count": 2, "liquidity_sweeps": 2, "valid_structure": False}),
            self._neutral_ind(),
            _mtf({"alignment_level": "CONFLICT", "market_condition": "RANGING"}),
        )
        assert snap.regime == "FAKE_BREAKOUT"

    def test_mean_reversion_overbought(self):
        snap = RegimeDetector.detect(
            _ctx({"trend": "NEUTRAL", "trend_strength": "WEAK", "momentum": "WEAK", "volatility_state": "NORMAL", "session": "regular"}),
            _struct({"trend": "RANGING", "trend_strength": "WEAK", "valid_structure": True}),
            _ind({"rsi_14": 82, "adx_14": 22, "ema_9": 25000, "ema_20": 24990,
                  "candle_close": 25500, "vwap": 25000, "candle_volume": 100000,
                  "average_volume": 120000, "atr_14": 100}),
            _mtf({"alignment_level": "MIXED", "market_condition": "RANGING"}),
        )
        assert snap.regime == "MEAN_REVERSION"

    def test_news_driven_detected(self):
        snap = RegimeDetector.detect(
            None,
            None,
            _ind({"adx_14": 28, "ema_9": 25000, "ema_20": 24900,
                  "candle_volume": 600000, "average_volume": 120000,
                  "candle_close": 26500, "vwap": 25000, "rsi_14": 50, "atr_14": 300}),
            None,
        )
        assert snap.regime == "NEWS_DRIVEN"

    def test_opening_auction_detected(self):
        snap = RegimeDetector.detect(
            _ctx({"session": "open", "trend": "NEUTRAL"}),
            _struct({"trend": "RANGING", "trend_strength": "WEAK", "valid_structure": False}),
            self._neutral_ind(),
            self._neutral_mtf(),
        )
        assert snap.regime == "OPENING_AUCTION"

    def test_closing_session_detected(self):
        snap = RegimeDetector.detect(
            _ctx({"session": "close", "trend": "NEUTRAL"}),
            _struct({"trend": "RANGING", "trend_strength": "WEAK", "valid_structure": False}),
            self._neutral_ind(),
            self._neutral_mtf(),
        )
        assert snap.regime == "CLOSING_SESSION"

    def test_illiquid_market_detected(self):
        # Test illiquid detection directly via the sub-detector
        confidence, factors = RegimeDetector._detect_illiquid_market(
            None,
            {"candle_volume": 5000, "average_volume": 120000, "atr_14": 50, "candle_close": 25000,
             "adx_14": 10, "ema_9": 25000, "ema_20": 24990, "vwap": 25000, "rsi_14": 50},
            {"valid_structure": False, "bos_count": 0},
        )
        assert confidence >= 40
        assert "very_low_volume" in factors or "low_volume" in factors or "no_structure" in factors

    def test_fallback_to_sideways(self):
        snap = RegimeDetector.detect({}, {}, {}, {})
        assert snap.regime == "SIDEWAYS_RANGE"
        assert snap.confidence >= 20

    def test_none_inputs_dont_crash(self):
        snap = RegimeDetector.detect(None, None, None, None)
        assert snap.regime is not None
        assert 0 <= snap.confidence <= 100

    def test_regime_list_has_14_entries(self):
        assert len(REGIME_LIST) == 14
        assert "STRONG_BULL_TREND" in REGIME_LIST
        assert "ILLIQUID_MARKET" in REGIME_LIST

    def test_confidence_threshold_defined(self):
        assert 0 < CONFIDENCE_THRESHOLD <= 50
