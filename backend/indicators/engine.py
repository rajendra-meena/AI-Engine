"""
MarketMind AI — Indicator Engine

Consumes CANDLE_CLOSED events from the Candle Engine, computes all
configured indicators for each symbol/interval, and produces
IndicatorSnapshot instances.

Design:
    - One compute unit per (symbol, interval) pair
    - Each compute unit holds all indicator instances
    - On CANDLE_CLOSED: update all indicators → snapshot → publish
    - Snapshot history kept for queries
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.event_bus import EventBus, Event
from core.events import NEW_CANDLE  # shared event constant
from candles.events import CANDLE_CLOSED
from indicators.snapshot import IndicatorSnapshot
from indicators.events import INDICATORS_UPDATED, INDICATOR_READY, INDICATOR_RESET
from indicators.modules.ema import EMA
from indicators.modules.sma import SMA
from indicators.modules.rsi import RSI
from indicators.modules.atr import ATR
from indicators.modules.macd import MACD
from indicators.modules.vwap import VWAP
from indicators.modules.adx import ADX
from indicators.modules.supertrend import SuperTrend
from models.candle import Candle
from utils.logger import log_info, log_error


class IndicatorComputeUnit:
    """Holds all indicators for one (symbol, interval)."""

    def __init__(self, symbol: str, interval: str):
        self.symbol = symbol
        self.interval = interval
        self.ema_9 = EMA(9)
        self.ema_20 = EMA(20)
        self.ema_50 = EMA(50)
        self.ema_200 = EMA(200)
        self.sma_20 = SMA(20)
        self.sma_50 = SMA(50)
        self.rsi_14 = RSI(14)
        self.atr_14 = ATR(14)
        self.vwap = VWAP()
        self.macd = MACD(12, 26, 9)
        self.adx_14 = ADX(14)
        self.supertrend = SuperTrend(10, 3.0)
        self.candles_processed = 0
        self.snapshots: list[IndicatorSnapshot] = []

    def update(self, candle: Candle) -> IndicatorSnapshot | None:
        self.candles_processed += 1

        ema_9 = self.ema_9.update(candle)
        ema_20 = self.ema_20.update(candle)
        ema_50 = self.ema_50.update(candle)
        ema_200 = self.ema_200.update(candle)
        sma_20 = self.sma_20.update(candle)
        sma_50 = self.sma_50.update(candle)
        rsi = self.rsi_14.update(candle)
        atr = self.atr_14.update(candle)
        vwap = self.vwap.update(candle)
        macd_val = self.macd.update(candle)
        adx = self.adx_14.update(candle)
        st = self.supertrend.update(candle)

        all_ready = (
            ema_9 is not None and rsi is not None and atr is not None
        )

        snapshot = IndicatorSnapshot(
            symbol=self.symbol,
            interval=self.interval,
            timestamp=candle.time or datetime.now(timezone.utc).isoformat(),
            ema_9=ema_9, ema_20=ema_20, ema_50=ema_50, ema_200=ema_200,
            sma_20=sma_20, sma_50=sma_50,
            rsi_14=rsi, atr_14=atr, vwap=vwap,
            macd=macd_val.macd if macd_val else None,
            macd_signal=macd_val.signal if macd_val else None,
            macd_histogram=macd_val.histogram if macd_val else None,
            adx_14=adx,
            supertrend_trend=st.trend if st else None,
            supertrend_upper=st.upper_band if st else None,
            supertrend_lower=st.lower_band if st else None,
            candle_open=candle.open,
            candle_high=candle.high,
            candle_low=candle.low,
            candle_close=candle.close,
            candle_volume=candle.volume,
            all_ready=all_ready,
        )

        self.snapshots.append(snapshot)
        return snapshot

    def latest_snapshot(self) -> IndicatorSnapshot | None:
        return self.snapshots[-1] if self.snapshots else None

    def reset(self):
        self.ema_9.reset(); self.ema_20.reset(); self.ema_50.reset()
        self.ema_200.reset(); self.sma_20.reset(); self.sma_50.reset()
        self.rsi_14.reset(); self.atr_14.reset(); self.vwap.reset()
        self.macd.reset(); self.adx_14.reset(); self.supertrend.reset()
        self.candles_processed = 0
        self.snapshots.clear()


class IndicatorEngine:
    """
    Centralized indicator computation engine.

    Subscribes to CANDLE_CLOSED events on the Event Bus.
    """

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._units: dict[tuple[str, str], IndicatorComputeUnit] = {}
        self._stats = {
            "total_candles_processed": 0,
            "total_snapshots_created": 0,
            "total_errors": 0,
            "active_units": 0,
            "start_time": datetime.now(timezone.utc).isoformat(),
        }
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self._event_bus.subscribe(CANDLE_CLOSED, self._on_candle_closed, name="indicator_engine")
        log_info("IndicatorEngine started")

    async def stop(self):
        self._running = False
        log_info("IndicatorEngine stopped", processed=self._stats["total_candles_processed"])

    async def _on_candle_closed(self, event: Event):
        if not self._running:
            return

        try:
            payload = event.payload
            candle_data = payload.get("candle", {})
            symbol = payload.get("symbol", candle_data.get("symbol", ""))
            interval = payload.get("interval", candle_data.get("interval", ""))

            if not symbol or not interval:
                return

            candle = Candle.from_dict(candle_data)
            if not candle.is_closed:
                return

            key = (symbol, interval)
            if key not in self._units:
                self._units[key] = IndicatorComputeUnit(symbol, interval)

            unit = self._units[key]
            snapshot = unit.update(candle)

            if snapshot:
                self._stats["total_candles_processed"] += 1
                self._stats["total_snapshots_created"] += 1
                self._stats["active_units"] = len(self._units)

                ev = Event(
                    type=INDICATORS_UPDATED,
                    source="indicator_engine",
                    payload=snapshot.to_dict(),
                )
                await self._event_bus.publish(ev)

        except Exception as e:
            self._stats["total_errors"] += 1
            log_error("IndicatorEngine error", error=str(e))

    def latest_snapshot(self, symbol: str, interval: str) -> dict[str, Any] | None:
        unit = self._units.get((symbol, interval))
        snap = unit.latest_snapshot() if unit else None
        return snap.to_dict() if snap else None

    def get_stats(self) -> dict[str, Any]:
        s = dict(self._stats)
        s["running"] = self._running
        s["units"] = [
            {"symbol": k[0], "interval": k[1], "candles_processed": v.candles_processed, "snapshots": len(v.snapshots)}
            for k, v in self._units.items()
        ]
        return s

    def reset_symbol(self, symbol: str, interval: str):
        key = (symbol, interval)
        if key in self._units:
            self._units[key].reset()
            del self._units[key]
