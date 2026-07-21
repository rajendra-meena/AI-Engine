"""Multi-Timeframe configuration — hierarchy weights and intervals."""

from dataclasses import dataclass

HIERARCHY = ["60m", "30m", "15m", "10m", "5m", "3m", "2m", "1m"]
"""Ordered highest to lowest timeframe."""

WEIGHTS = {
    "60m": 0.30,
    "30m": 0.20,
    "15m": 0.20,
    "10m": 0.10,
    "5m": 0.10,
    "3m": 0.05,
    "2m": 0.03,
    "1m": 0.02,
}
"""Alignment score weights — higher TF dominates."""

EXECUTION_TF = {
    "trend": "60m",
    "confirmation": "15m",
    "entry": "5m",
    "precision": "1m",
}
"""Recommended execution timeframes."""

BIAS_SCORE_MAP = {"BULLISH": 1.0, "NEUTRAL": 0.0, "BEARISH": -1.0}
