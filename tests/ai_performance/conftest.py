"""Shared test helpers for Phase 57 tests."""

from __future__ import annotations

from typing import Any


def _make_prediction(overrides: dict | None = None) -> dict[str, Any]:
    base = {
        "id": "pred_001",
        "symbol": "NIFTY 50", "interval": "15m",
        "decision": "HIGH_CONVICTION", "direction": "BUY",
        "score": 80, "confidence": 75, "risk_score": 20,
        "entry_price": 25100.0, "stop_loss": 24800.0, "target": 25700.0,
        "risk_reward": 2.0,
        "strategy_id": "trend_following",
        "market_regime": "TRENDING", "trend": "BULLISH",
        "market_phase": "markup", "mtf_alignment": "STRONG_ALIGNMENT",
        "volatility": 120.0, "momentum": 0.8,
        "created_at": "2026-07-26T09:30:00Z",
        "pattern_snapshot": '{"strongest_pattern": "bull_flag", "chart_patterns": [{"name": "bull_flag"}]}',
        "indicator_snapshot": '{"candle_volume": 150000, "average_volume": 120000, "candle_close": 25100, "rsi_14": 55}',
        "quantity": 1,
    }
    if overrides:
        base.update(overrides)
    return base


def _make_outcome(overrides: dict | None = None) -> dict[str, Any]:
    base = {
        "id": "out_001",
        "prediction_id": "pred_001",
        "outcome_eod": "WIN",
        "actual_return": 250.0,
        "max_favorable_excursion": 350.0,
        "max_adverse_excursion": -80.0,
        "target_hit": 0,
        "stop_loss_hit": 0,
        "error_category": "",
        "error_reason": "",
        "maximum_return": 350.0,
        "maximum_drawdown": -80.0,
    }
    if overrides:
        base.update(overrides)
    return base


def _make_feedback(overrides: dict | None = None) -> dict[str, Any]:
    base = {
        "id": "fb_001",
        "prediction_id": "pred_001",
        "entry_slippage": 2.5,
        "exit_slippage": 1.5,
        "gross_pnl": 250.0,
        "net_pnl": 246.0,
        "planned_risk": 300.0,
        "actual_risk": 300.0,
        "planned_rr": 2.0,
        "actual_rr": 1.8,
        "holding_duration": 180,  # minutes
        "exit_reason": "target_hit",
    }
    if overrides:
        base.update(overrides)
    return base


def _sample_predictions(n: int = 5) -> list[dict[str, Any]]:
    results = []
    for i in range(n):
        p = _make_prediction({
            "id": f"pred_{i:03d}",
            "symbol": "NIFTY 50",
            "score": 70 + i,
            "confidence": 60 + i * 3,
            "strategy_id": ["trend_following", "breakout", "reversal"][i % 3],
            "direction": "BUY" if i % 2 == 0 else "SELL",
            "actual_return": 200.0 if i % 3 != 0 else -100.0,
        })
        results.append(p)
    return results


def _make_mistake(overrides: dict | None = None) -> dict[str, Any]:
    base = {
        "prediction_id": "pred_002",
        "mistake_type": "early_exit",
        "severity": "major",
        "description": "Exited at 100.0, MFE was 250.0",
        "impact": 150.0,
        "lesson": "Let winners run closer to target",
    }
    if overrides:
        base.update(overrides)
    return base
