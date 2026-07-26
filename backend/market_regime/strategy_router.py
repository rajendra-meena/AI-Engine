"""
Strategy Router — recommends optimal strategies per detected market regime.
"""

from __future__ import annotations

from typing import Any


REGIME_STRATEGY_MAP: dict[str, dict[str, Any]] = {
    "STRONG_BULL_TREND": {
        "primary": "trend_following",
        "secondary": "pullback",
        "avoid": ["reversal", "range", "mean_reversion"],
        "expected_win_rate": 0.72,
        "reasoning": "Strong directional uptrend favors trend following on pullbacks to moving averages",
    },
    "STRONG_BEAR_TREND": {
        "primary": "trend_following",
        "secondary": "pullback",
        "avoid": ["reversal", "range", "mean_reversion"],
        "expected_win_rate": 0.70,
        "reasoning": "Strong bearish trend favors trend following on retracements to resistance",
    },
    "WEAK_BULL_TREND": {
        "primary": "pullback",
        "secondary": "range",
        "avoid": ["breakout", "momentum"],
        "expected_win_rate": 0.58,
        "reasoning": "Weak uptrend: counter-trend pulls and range trades outperform breakouts",
    },
    "WEAK_BEAR_TREND": {
        "primary": "pullback",
        "secondary": "range",
        "avoid": ["breakout", "momentum"],
        "expected_win_rate": 0.56,
        "reasoning": "Weak downtrend: anticipate reversals and range trading near support",
    },
    "SIDEWAYS_RANGE": {
        "primary": "range",
        "secondary": "mean_reversion",
        "avoid": ["trend_following", "breakout", "momentum"],
        "expected_win_rate": 0.55,
        "reasoning": "Range-bound market: buy support, sell resistance, avoid trend strategies",
    },
    "HIGH_VOLATILITY": {
        "primary": "momentum",
        "secondary": "breakout",
        "avoid": ["range", "mean_reversion", "scalping"],
        "expected_win_rate": 0.50,
        "reasoning": "High volatility favors momentum and breakout trades with wider stops",
    },
    "LOW_VOLATILITY": {
        "primary": "no_trade",
        "secondary": "scalping",
        "avoid": ["breakout", "momentum", "trend_following"],
        "expected_win_rate": 0.30,
        "reasoning": "Low volatility: avoid directional trades, prefer no trade or tight scalps",
    },
    "BREAKOUT": {
        "primary": "breakout",
        "secondary": "momentum",
        "avoid": ["range", "mean_reversion", "reversal"],
        "expected_win_rate": 0.55,
        "reasoning": "Breakout detected: enter with momentum in breakout direction with volume confirmation",
    },
    "FAKE_BREAKOUT": {
        "primary": "mean_reversion",
        "secondary": "reversal",
        "avoid": ["breakout", "momentum", "trend_following"],
        "expected_win_rate": 0.55,
        "reasoning": "False breakout: anticipate reversal to range, favor mean reversion strategies",
    },
    "MEAN_REVERSION": {
        "primary": "mean_reversion",
        "secondary": "scalping",
        "avoid": ["trend_following", "breakout"],
        "expected_win_rate": 0.52,
        "reasoning": "Overextended price: fade the extreme, anticipate reversion to mean",
    },
    "NEWS_DRIVEN": {
        "primary": "no_trade",
        "secondary": "scalping",
        "avoid": ["trend_following", "range", "breakout", "mean_reversion", "momentum", "pullback"],
        "expected_win_rate": 0.35,
        "reasoning": "News-driven moves are unpredictable — avoid most directional strategies",
    },
    "OPENING_AUCTION": {
        "primary": "scalping",
        "secondary": "no_trade",
        "avoid": ["trend_following", "breakout", "range"],
        "expected_win_rate": 0.45,
        "reasoning": "Opening auction: trade the initial balance range, avoid trend and breakout strategies",
    },
    "CLOSING_SESSION": {
        "primary": "scalping",
        "secondary": "reversal",
        "avoid": ["breakout", "trend_following"],
        "expected_win_rate": 0.48,
        "reasoning": "Closing session: positional closing creates scalping and reversal opportunities",
    },
    "ILLIQUID_MARKET": {
        "primary": "no_trade",
        "secondary": "scalping",
        "avoid": ["trend_following", "breakout", "momentum", "pullback", "range", "mean_reversion", "reversal"],
        "expected_win_rate": 0.20,
        "reasoning": "Illiquid market: avoid all but the tightest scalps, prefer no trade",
    },
}


class StrategyRouter:
    """Recommends optimal strategies per market regime."""

    @staticmethod
    def get_best_strategy(
        regime: str,
        performance_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return primary + secondary + avoid strategies for a regime."""
        base = REGIME_STRATEGY_MAP.get(regime, REGIME_STRATEGY_MAP["SIDEWAYS_RANGE"])

        result = dict(base)
        result["regime"] = regime

        if performance_data and regime in performance_data:
            hist = performance_data[regime]
            win_rate = hist.get("win_rate", 50) / 100.0
            result["historical_success"] = round(win_rate, 2)
            result["confidence"] = min(100, max(0, int(base["expected_win_rate"] * 50 + win_rate * 50)))
        else:
            result["historical_success"] = base["expected_win_rate"]
            result["confidence"] = int(base["expected_win_rate"] * 100)

        return result

    @staticmethod
    def list_all_recommendations() -> list[dict[str, Any]]:
        """Return recommendations for all regimes."""
        results = []
        for regime in REGIME_STRATEGY_MAP:
            rec = StrategyRouter.get_best_strategy(regime)
            results.append(rec)
        return results
