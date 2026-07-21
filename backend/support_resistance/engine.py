"""
SR Engine — combines horizontal, dynamic, supply/demand, and psychological levels.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

from core.event_bus import EventBus, Event
from candles.events import CANDLE_CLOSED
from market_structure.events import STRUCTURE_UPDATED
from indicators.events import INDICATORS_UPDATED
from support_resistance.snapshot import SRSnapshot
from support_resistance.events import S_UPDATED
from support_resistance.config import HISTORY_LIMIT
from support_resistance.modules.horizontal_levels import HorizontalLevels
from support_resistance.modules.dynamic_levels import DynamicLevels
from support_resistance.modules.supply_demand import SupplyDemandDetector
from support_resistance.modules.psychological_levels import PsychologicalLevels
from support_resistance.modules.zone_merge import ZoneMerger
from models.candle import Candle
from utils.logger import log_info, log_error


class SRUnit:
    """Tracks all S/R data for one symbol."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self._candle: Candle | None = None
        self._indicator: dict[str, Any] | None = None
        self._structure: dict[str, Any] | None = None
        self._supply_demand = SupplyDemandDetector()
        self._history: deque = _dq(maxlen=HISTORY_LIMIT)
        self._update_count = 0

    def update_candle(self, payload: dict):
        try:
            cd = payload.get("candle", {})
            if cd.get("symbol") == self.symbol:
                self._candle = Candle.from_dict(cd)
                self._produce()
        except Exception:
            pass

    def update_structure(self, payload: dict):
        if payload.get("symbol") == self.symbol:
            self._structure = payload
            self._produce()

    def update_indicator(self, payload: dict):
        if payload.get("symbol") == self.symbol:
            self._indicator = payload
            self._produce()

    def _produce(self):
        if not self._candle or not self._indicator or not self._structure:
            return

        c = self._candle
        swings_high = [s.get("price", 0) for s in
                       (self._structure.get("swings") or []) if s.get("type") == "high"]
        swings_low = [s.get("price", 0) for s in
                      (self._structure.get("swings") or []) if s.get("type") == "low"]

        # If structure doesn't have swings list, extract from swing points
        # Fallback: use current_swing_high/low
        if not swings_high and self._structure.get("current_swing_high"):
            swings_high = [self._structure["current_swing_high"]]
        if not swings_low and self._structure.get("current_swing_low"):
            swings_low = [self._structure["current_swing_low"]]

        # Horizontal levels
        horiz = HorizontalLevels.generate(c.close, swings_high, swings_low, self._structure)

        # Dynamic levels
        dynamic = DynamicLevels.generate(self._indicator)

        # Supply/Demand
        sd_zones = self._supply_demand.update(swings_high, swings_low, c.close)
        supply = [z.to_dict() for z in self._supply_demand.get_active() if z.zone_type == "supply"]
        demand = [z.to_dict() for z in self._supply_demand.get_active() if z.zone_type == "demand"]

        # Psychological
        psy = PsychologicalLevels.generate(c.close, range_around=3)

        # Merge all levels
        all_levels = ZoneMerger.merge(horiz + dynamic + psy, max_levels=15)
        nearest_s, nearest_r = ZoneMerger.nearest(all_levels, c.close)

        # Separate major supports and resistances
        majors_s = [l.to_dict() for l in all_levels if l.level_type == "support"][:5]
        majors_r = [l.to_dict() for l in all_levels if l.level_type == "resistance"][:5]

        # Breakout state
        breakout_state = "none"
        if nearest_r and c.close > nearest_r.price:
            breakout_state = "breakout_above"
        elif nearest_s and c.close < nearest_s.price:
            breakout_state = "breakdown_below"

        confidence = min(100, 50 + len(all_levels) * 5 + len(supply + demand) * 10)

        warnings = []
        if not swings_high:
            warnings.append("No swing data available")
        if self._update_count < 5:
            warnings.append("Still building level history")

        snap = SRSnapshot(
            symbol=self.symbol,
            timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            nearest_support=nearest_s.price if nearest_s else None,
            nearest_resistance=nearest_r.price if nearest_r else None,
            major_supports=majors_s,
            major_resistances=majors_r,
            dynamic_levels=[l.to_dict() for l in dynamic],
            supply_zones=supply,
            demand_zones=demand,
            psychological_levels=[l.to_dict() for l in psy],
            breakout_state=breakout_state,
            zone_strength="STRONG" if len(supply + demand) >= 3 else "NORMAL",
            confidence=confidence,
            warnings=warnings,
        )
        self._history.append(snap)
        self._update_count += 1
        return snap

    def latest(self) -> dict[str, Any] | None:
        return self._history[-1].to_dict() if self._history else None

    def history(self, count: int = 100) -> list[dict[str, Any]]:
        return [s.to_dict() for s in list(self._history)[-count:]]


class SREngine:
    """Subscribes to candle, structure, and indicator events."""

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._units: dict[str, SRUnit] = {}
        self._stats = {"total_updates": 0, "total_errors": 0,
                       "start_time": datetime.now(timezone.utc).isoformat()}
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self._event_bus.subscribe(CANDLE_CLOSED, self._on_candle, name="sr_candle")
        self._event_bus.subscribe(STRUCTURE_UPDATED, self._on_structure, name="sr_structure")
        self._event_bus.subscribe(INDICATORS_UPDATED, self._on_indicator, name="sr_indicator")
        log_info("SREngine started")

    async def stop(self):
        self._running = False
        log_info("SREngine stopped")

    async def _on_candle(self, event: Event):
        if not self._running:
            return
        try:
            symbol = event.payload.get("symbol") or event.payload.get("candle", {}).get("symbol", "")
            if symbol:
                self._get_unit(symbol).update_candle(event.payload)
                self._stats["total_updates"] += 1
        except Exception as e:
            self._stats["total_errors"] += 1
            log_error("SREngine candle error", error=str(e))

    async def _on_structure(self, event: Event):
        if not self._running:
            return
        try:
            symbol = event.payload.get("symbol", "")
            if symbol:
                self._get_unit(symbol).update_structure(event.payload)
        except Exception as e:
            self._stats["total_errors"] += 1

    async def _on_indicator(self, event: Event):
        if not self._running:
            return
        try:
            symbol = event.payload.get("symbol", "")
            if symbol:
                self._get_unit(symbol).update_indicator(event.payload)
        except Exception as e:
            self._stats["total_errors"] += 1

    def _get_unit(self, symbol: str) -> SRUnit:
        if symbol not in self._units:
            self._units[symbol] = SRUnit(symbol)
        return self._units[symbol]

    def latest(self, symbol: str) -> dict[str, Any] | None:
        unit = self._units.get(symbol)
        return unit.latest() if unit else None

    def history(self, symbol: str, count: int = 100) -> list[dict[str, Any]]:
        unit = self._units.get(symbol)
        return unit.history(count) if unit else []

    def get_stats(self) -> dict[str, Any]:
        s = dict(self._stats)
        s["running"] = self._running
        s["units"] = len(self._units)
        return s
