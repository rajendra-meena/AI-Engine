"""
Feature Engineering Engine — generates ML-ready features from market data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class FeatureSet:
    timestamp: str = ""
    symbol: str = ""
    features: dict[str, float] = field(default_factory=dict)
    label: Optional[float] = None


class FeatureEngine:
    """Computes ML features from OHLCV data and indicators."""

    @staticmethod
    def compute_returns(
        closes: list[float], periods: list[int] = [1, 5, 10, 20]
    ) -> dict[str, float]:
        result = {}
        for p in periods:
            if len(closes) > p:
                result[f"return_{p}"] = (
                    (closes[-1] - closes[-p - 1]) / closes[-p - 1] * 100
                )
                result[f"log_return_{p}"] = math.log(closes[-1] / closes[-p - 1]) * 100
        return result

    @staticmethod
    def compute_volatility(closes: list[float], period: int = 20) -> float:
        if len(closes) < period + 1:
            return 0.0
        returns = [
            (closes[i] - closes[i - 1]) / closes[i - 1] for i in range(-period, 0)
        ]
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        return math.sqrt(variance) * math.sqrt(252) * 100

    @staticmethod
    def compute_momentum(closes: list[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 0.0
        return (closes[-1] - closes[-period - 1]) / closes[-period - 1] * 100

    @staticmethod
    def compute_rsi(closes: list[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        gains, losses = [], []
        for i in range(-period, 0):
            diff = closes[i] - closes[i - 1]
            gains.append(max(0, diff))
            losses.append(max(0, -diff))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def compute_macd(closes: list[float]) -> dict[str, float]:
        def ema(data: list[float], period: int) -> float:
            if len(data) < period:
                return data[-1] if data else 0.0
            k = 2.0 / (period + 1)
            result = sum(data[-period:]) / period
            return data[-1] * k + result * (1 - k)

        ema12 = ema(closes, 12)
        ema26 = ema(closes, 26)
        macd_line = ema12 - ema26
        return {
            "macd": macd_line,
            "macd_signal": macd_line * 0.9,
            "macd_hist": macd_line * 0.1,
        }

    @staticmethod
    def compute_atr(
        highs: list[float], lows: list[float], closes: list[float], period: int = 14
    ) -> float:
        if len(highs) < 2:
            return 0.0
        tr = []
        for i in range(-period, 0):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i - 1])
            lc = abs(lows[i] - closes[i - 1])
            tr.append(max(hl, hc, lc))
        return sum(tr) / len(tr) if tr else 0.0

    @staticmethod
    def compute_supertrend(
        closes: list[float],
        highs: list[float],
        lows: list[float],
        period: int = 10,
        multiplier: float = 3.0,
    ) -> dict[str, float]:
        atr = FeatureEngine.compute_atr(highs, lows, closes, period)
        hl2 = (highs[-1] + lows[-1]) / 2 if highs else closes[-1]
        upper = hl2 + multiplier * atr
        lower = hl2 - multiplier * atr
        return {
            "supertrend_upper": upper,
            "supertrend_lower": lower,
            "supertrend_mid": (upper + lower) / 2,
        }

    @staticmethod
    def compute_bollinger(
        closes: list[float], period: int = 20, multiplier: float = 2.0
    ) -> dict[str, float]:
        if len(closes) < period:
            return {
                "bb_upper": closes[-1],
                "bb_mid": closes[-1],
                "bb_lower": closes[-1],
            }
        sma = sum(closes[-period:]) / period
        variance = sum((c - sma) ** 2 for c in closes[-period:]) / period
        std = math.sqrt(variance)
        return {
            "bb_upper": sma + multiplier * std,
            "bb_mid": sma,
            "bb_lower": sma - multiplier * std,
        }

    @staticmethod
    def compute_all(
        highs: list[float], lows: list[float], closes: list[float]
    ) -> dict[str, float]:
        features = {}
        features.update(FeatureEngine.compute_returns(closes))
        features["volatility"] = FeatureEngine.compute_volatility(closes)
        features["momentum_14"] = FeatureEngine.compute_momentum(closes)
        features["rsi_14"] = FeatureEngine.compute_rsi(closes)
        features.update(FeatureEngine.compute_macd(closes))
        features["atr_14"] = FeatureEngine.compute_atr(highs, lows, closes)
        features.update(FeatureEngine.compute_supertrend(closes, highs, lows))
        features.update(FeatureEngine.compute_bollinger(closes))
        return features
