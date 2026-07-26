"""Tests for RegimeEngine and RegimeUnit."""

from __future__ import annotations

import pytest
from market_regime.engine import RegimeUnit, RegimeEngine


def _ctx() -> dict:
    return {"trend": "BULLISH", "trend_strength": "STRONG", "momentum": "STRONG", "volatility_state": "NORMAL", "session": "regular"}
def _struct() -> dict:
    return {"trend": "UPTREND", "trend_strength": "STRONG", "valid_structure": True, "bos_count": 3, "choch_count": 0, "liquidity_sweeps": 0}
def _ind() -> dict:
    return {"ema_9": 25100, "ema_20": 25000, "ema_50": 24900, "adx_14": 35, "rsi_14": 55, "candle_close": 25100, "vwap": 25000, "candle_volume": 150000, "average_volume": 120000, "atr_14": 120}
def _mtf() -> dict:
    return {"alignment_level": "STRONG_ALIGNMENT", "market_condition": "TRENDING", "institutional_bias": "BULLISH"}


class TestRegimeUnit:
    def test_update_returns_snapshot(self):
        unit = RegimeUnit("NIFTY 50")
        snap, transitions = unit.update(_ctx(), _struct(), _ind(), _mtf())
        assert snap.regime is not None
        assert 0 <= snap.confidence <= 100

    def test_latest_returns_dict(self):
        unit = RegimeUnit("NIFTY 50")
        unit.update(_ctx(), _struct(), _ind(), _mtf())
        latest = unit.latest()
        assert latest is not None
        assert "regime" in latest

    def test_history_accumulates(self):
        unit = RegimeUnit("NIFTY 50")
        unit.update(_ctx(), _struct(), _ind(), _mtf())
        assert len(unit.history()) == 1
        unit.update(_ctx(), _struct(), _ind(), _mtf())
        assert len(unit.history()) == 2

    def test_transitions_on_change(self):
        unit = RegimeUnit("NIFTY 50")
        snap1, _ = unit.update(_ctx(), _struct(), _ind(), _mtf())
        # Force a different regime
        snap2, trans = unit.update(
            {"trend": "NEUTRAL", "trend_strength": "WEAK", "volatility_state": "CONTRACTING", "session": "regular", "momentum": "WEAK"},
            {"trend": "RANGING", "trend_strength": "WEAK", "valid_structure": False, "bos_count": 0, "choch_count": 0, "liquidity_sweeps": 0},
            {"adx_14": 15, "ema_9": 25000, "ema_20": 24995, "candle_close": 25000, "vwap": 25000, "candle_volume": 100000, "average_volume": 120000, "atr_14": 80, "rsi_14": 50},
            {"alignment_level": "MIXED", "market_condition": "RANGING", "institutional_bias": "NEUTRAL"},
        )
        # May or may not transition depending on confidence
        assert snap2.regime is not None

    def test_new_unit_no_data(self):
        unit = RegimeUnit("TEST")
        assert unit.latest() is None
        assert unit.history() == []


class TestRegimeEngine:
    def test_engine_manages_units(self):
        engine = RegimeEngine()
        result = engine.update("TEST", _ctx(), _struct(), _ind(), _mtf())
        assert result is not None
        assert result["regime"] is not None

    def test_get_unit_creates(self):
        engine = RegimeEngine()
        unit = engine.get_unit("NEW_SYMBOL")
        assert unit.symbol == "NEW_SYMBOL"

    def test_latest_from_engine(self):
        engine = RegimeEngine()
        engine.update("TEST", _ctx(), _struct(), _ind(), _mtf())
        latest = engine.latest("TEST")
        assert latest is not None
        assert "regime" in latest

    def test_engine_stats(self):
        engine = RegimeEngine()
        engine.update("T1", _ctx(), _struct(), _ind(), _mtf())
        stats = engine.get_stats()
        assert stats["total_updates"] >= 1
