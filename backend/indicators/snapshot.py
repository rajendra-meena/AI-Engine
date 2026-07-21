"""
MarketMind AI — Indicator Snapshot

An immutable snapshot of ALL indicator values for one symbol/timeframe at a point in time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IndicatorSnapshot:
    symbol: str = ""
    interval: str = ""
    timestamp: str = ""

    # EMA
    ema_9: float | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None

    # SMA
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None

    # RSI
    rsi_14: float | None = None

    # ATR
    atr_14: float | None = None

    # VWAP
    vwap: float | None = None

    # MACD
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None

    # ADX
    adx_14: float | None = None

    # SuperTrend
    supertrend_trend: str | None = None
    supertrend_upper: float | None = None
    supertrend_lower: float | None = None

    # Candle that triggered this snapshot
    candle_open: float | None = None
    candle_high: float | None = None
    candle_low: float | None = None
    candle_close: float | None = None
    candle_volume: float | None = None

    # Status
    all_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "timestamp": self.timestamp,
            "ema_9": self.ema_9,
            "ema_20": self.ema_20,
            "ema_50": self.ema_50,
            "ema_200": self.ema_200,
            "sma_20": self.sma_20,
            "sma_50": self.sma_50,
            "rsi_14": self.rsi_14,
            "atr_14": self.atr_14,
            "vwap": self.vwap,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "macd_histogram": self.macd_histogram,
            "adx_14": self.adx_14,
            "supertrend_trend": self.supertrend_trend,
            "candle_close": self.candle_close,
            "all_ready": self.all_ready,
        }
