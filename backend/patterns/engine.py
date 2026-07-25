"""
Pattern Recognition Engine

Coordinates candlestick, chart, and breakout pattern detectors to produce
a unified PatternSnapshot on each closed candle.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.event_bus import EventBus, Event
from candles.events import CANDLE_CLOSED
from patterns.snapshot import PatternSnapshot
from patterns.events import PATTERN_DETECTED, BREAKOUT_DETECTED
from patterns.modules.candlestick_patterns import CandlestickPatternDetector
from patterns.modules.chart_patterns import ChartPatternDetector
from patterns.modules.breakout_patterns import BreakoutPatternDetector
from models.candle import Candle
from utils.logger import log_info, log_error

_PATTERN_STRENGTH_ORDER = {"strong": 3, "moderate": 2, "weak": 1}


class PatternUnit:
    """Holds all detectors for one (symbol, interval)."""

    def __init__(self, symbol: str, interval: str):
        self.symbol = symbol
        self.interval = interval
        self.candle = CandlestickPatternDetector()
        self.chart = ChartPatternDetector()
        self.breakout = BreakoutPatternDetector()
        self.candles_processed = 0
        self.snapshots: list[PatternSnapshot] = []
        self._latest_swings_high: list[float] = []
        self._latest_swings_low: list[float] = []

    def update_swings(self, highs: list[float], lows: list[float]):
        self._latest_swings_high = highs
        self._latest_swings_low = lows

    def update(self, candle: Candle) -> PatternSnapshot:
        self.candles_processed += 1

        cs = self.candle.update(candle)
        bp = self.breakout.update(candle)
        cp = self.chart.update(
            candle, self._latest_swings_high, self._latest_swings_low
        )

        cs_dicts = [p.to_dict() for p in cs]
        cp_dicts = [p.to_dict() for p in cp]
        bp_dicts = [p.to_dict() for p in bp]

        all_patterns = cs_dicts + cp_dicts + bp_dicts
        strongest = self._find_strongest(all_patterns)
        direction = self._determine_direction(all_patterns)

        snap = PatternSnapshot(
            symbol=self.symbol,
            interval=self.interval,
            timestamp=candle.time or datetime.now(timezone.utc).isoformat(),
            candlestick_patterns=cs_dicts,
            chart_patterns=cp_dicts,
            breakout_patterns=bp_dicts,
            strongest_pattern=strongest,
            pattern_direction=direction,
            confidence=(
                "high"
                if len(all_patterns) >= 3
                else "medium" if all_patterns else "low"
            ),
            total_count=len(all_patterns),
        )
        self.snapshots.append(snap)
        return snap, all_patterns

    def latest_snapshot(self) -> PatternSnapshot | None:
        return self.snapshots[-1] if self.snapshots else None

    @staticmethod
    def _find_strongest(patterns: list[dict]) -> str:
        if not patterns:
            return ""
        best = max(
            patterns,
            key=lambda p: _PATTERN_STRENGTH_ORDER.get(p.get("strength", "weak"), 0),
        )
        return best.get("name", "")

    @staticmethod
    def _determine_direction(patterns: list[dict]) -> str:
        bullish = sum(1 for p in patterns if p.get("direction") == "bullish")
        bearish = sum(1 for p in patterns if p.get("direction") == "bearish")
        if bullish > bearish:
            return "bullish"
        elif bearish > bullish:
            return "bearish"
        return "neutral"

    def reset(self):
        self.candle.reset()
        self.chart.reset()
        self.breakout.reset()
        self.candles_processed = 0
        self.snapshots.clear()


class PatternEngine:
    """Subscribes to CANDLE_CLOSED, produces PatternSnapshots."""

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._units: dict[tuple[str, str], PatternUnit] = {}
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
            CANDLE_CLOSED, self._on_candle_closed, name="pattern_engine"
        )
        log_info("PatternEngine started")

    async def stop(self):
        self._running = False
        log_info("PatternEngine stopped")

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
                self._units[key] = PatternUnit(symbol, interval)
            unit = self._units[key]

            # Feed swings if available in payload
            swings_high = [
                s.get("price", 0)
                for s in payload.get("swings", [])
                if s.get("type") == "high"
            ]
            swings_low = [
                s.get("price", 0)
                for s in payload.get("swings", [])
                if s.get("type") == "low"
            ]
            if swings_high or swings_low:
                unit.update_swings(swings_high, swings_low)

            snap, all_patterns = unit.update(candle)
            self._stats["total_processed"] += 1

            await self._publish(PATTERN_DETECTED, snap.to_dict())

            # Also publish BREAKOUT_DETECTED for breakout patterns
            for p in all_patterns:
                if (
                    p.get("name", "").startswith("range_break")
                    or p.get("name") == "nr7"
                ):
                    await self._publish(BREAKOUT_DETECTED, p)

        except Exception as e:
            self._stats["total_errors"] += 1
            log_error("PatternEngine error", error=str(e))

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
            Event(type=event_type, source="pattern_engine", payload=payload)
        )
