"""
MarketMind AI — Market Structure Engine

Coordinates swing, trend, structure, and liquidity detectors to produce
a unified MarketStructureSnapshot on each closed candle.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.event_bus import EventBus, Event
from candles.events import CANDLE_CLOSED
from market_structure.snapshot import MarketStructureSnapshot
from market_structure.events import (
    STRUCTURE_UPDATED,
    NEW_SWING,
    BOS_DETECTED,
    CHOCH_DETECTED,
)
from market_structure.modules.swing_detector import SwingDetector
from market_structure.modules.trend_detector import TrendDetector
from market_structure.modules.structure_detector import StructureDetector
from market_structure.modules.liquidity_detector import LiquidityDetector
from models.candle import Candle
from utils.logger import log_info, log_error


class MarketStructureUnit:
    """Holds all detectors for one (symbol, interval)."""

    def __init__(self, symbol: str, interval: str):
        self.symbol = symbol
        self.interval = interval
        self.swing = SwingDetector(lookback=2)
        self.trend = TrendDetector()
        self.structure = StructureDetector()
        self.liquidity = LiquidityDetector()
        self.candles_processed = 0
        self.snapshots: list[MarketStructureSnapshot] = []

    def update(self, candle: Candle) -> MarketStructureSnapshot:
        self.candles_processed += 1

        # 1. Swing
        new_swings = self.swing.update(candle)
        latest_high = self.swing.latest_swing_high()
        latest_low = self.swing.latest_swing_low()

        # 2. Trend
        trend_info = self.trend.get_info()
        self.trend.update(self.swing.recent_swings(10))

        # 3. Structure
        new_structure = self.structure.update(
            candle, self.trend.get_info(), self.swing.recent_swings(10)
        )

        # 4. Liquidity
        new_liquidity = self.liquidity.update(candle)

        # Build snapshot
        snap = MarketStructureSnapshot(
            symbol=self.symbol,
            interval=self.interval,
            timestamp=candle.time or datetime.now(timezone.utc).isoformat(),
            trend=trend_info.get("direction", "RANGING"),
            trend_strength=trend_info.get("strength", "WEAK"),
            trend_age=trend_info.get("age", 0),
            last_hh=trend_info.get("last_hh"),
            last_hl=trend_info.get("last_hl"),
            last_lh=trend_info.get("last_lh"),
            last_ll=trend_info.get("last_ll"),
            current_swing_high=latest_high.price if latest_high else None,
            current_swing_low=latest_low.price if latest_low else None,
            total_swings=self.swing.swings_count,
            market_phase=self.structure.get_info().get("phase", "undefined"),
            last_bos=self.structure.get_info().get("last_bos"),
            last_choch=self.structure.get_info().get("last_choch"),
            bos_count=self.structure.get_info().get("bos_count", 0),
            choch_count=self.structure.get_info().get("choch_count", 0),
            impulse_active=self.structure.get_info().get("impulse_active", False),
            pullback_active=self.structure.get_info().get("pullback_active", False),
            consolidation_bars=self.structure.get_info().get("consolidation_bars", 0),
            equal_highs=(
                [z.price for z in self.liquidity.liquidity_above(candle.close)][-5:]
                if new_liquidity
                else None
            ),
            equal_lows=(
                [z.price for z in self.liquidity.liquidity_below(candle.close)][-5:]
                if new_liquidity
                else None
            ),
            liquidity_sweeps=self.liquidity.get_info().get("sweeps", 0),
            valid_structure=self.swing.swings_count >= 2,
        )

        self.snapshots.append(snap)
        return snap, new_swings, new_structure

    def latest_snapshot(self) -> MarketStructureSnapshot | None:
        return self.snapshots[-1] if self.snapshots else None

    def reset(self):
        self.swing.reset()
        self.trend.reset()
        self.structure.reset()
        self.liquidity.reset()
        self.candles_processed = 0
        self.snapshots.clear()


class MarketStructureEngine:
    """Subscribes to CANDLE_CLOSED, produces MarketStructureSnapshots."""

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._units: dict[tuple[str, str], MarketStructureUnit] = {}
        self._stats = {
            "total_processed": 0,
            "total_errors": 0,
            "start_time": datetime.now(timezone.utc).isoformat(),
        }
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self._event_bus.subscribe(
            CANDLE_CLOSED, self._on_candle_closed, name="market_structure_engine"
        )
        log_info("MarketStructureEngine started")

    async def stop(self):
        self._running = False
        log_info("MarketStructureEngine stopped")

    async def _on_candle_closed(self, event: Event):
        if not self._running:
            return
        try:
            payload = event.payload
            cd = payload.get("candle", {})
            symbol = payload.get("symbol", cd.get("symbol", ""))
            interval = payload.get("interval", cd.get("interval", ""))
            if not symbol or not interval:
                return
            candle = Candle.from_dict(cd)
            key = (symbol, interval)
            if key not in self._units:
                self._units[key] = MarketStructureUnit(symbol, interval)
            unit = self._units[key]
            snap, new_swings, new_structure = unit.update(candle)
            self._stats["total_processed"] += 1

            # Publish snapshot event with candle identity from incoming event
            payload = snap.to_dict()
            payload["candle_version"] = event.payload.get("candle_version", "")
            payload["analysis_cycle_id"] = event.payload.get("analysis_cycle_id", "")
            await self._publish(STRUCTURE_UPDATED, payload)

            # Publish sub-events
            for s in new_swings:
                await self._publish(NEW_SWING, s.to_dict())
            for e in new_structure:
                if e.event_type == "bos":
                    await self._publish(BOS_DETECTED, e.to_dict())
                elif e.event_type == "choch":
                    await self._publish(CHOCH_DETECTED, e.to_dict())

        except Exception as e:
            self._stats["total_errors"] += 1
            log_error("MarketStructureEngine error", error=str(e))

    def latest_snapshot(self, symbol: str, interval: str) -> dict[str, Any] | None:
        unit = self._units.get((symbol, interval))
        snap = unit.latest_snapshot() if unit else None
        return snap.to_dict() if snap else None

    def get_stats(self) -> dict[str, Any]:
        s = dict(self._stats)
        s["running"] = self._running
        s["units"] = len(self._units)
        return s

    async def _publish(self, event_type: str, payload: dict):
        await self._event_bus.publish(
            Event(type=event_type, source="market_structure_engine", payload=payload)
        )
