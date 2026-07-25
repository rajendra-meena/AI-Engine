"""
Multi-Timeframe Analysis Engine

Combines TradingContextSnapshots from 1m-60m into a unified alignment view.
Provides institutional bias, market condition, and trading permission.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

from core.event_bus import EventBus, Event
from trading_context.events import TRADING_CONTEXT_UPDATED
from multi_timeframe.config import HIERARCHY, EXECUTION_TF, BIAS_SCORE_MAP
from multi_timeframe.snapshot import MTFSnapshot
from multi_timeframe.events import (
    MTF_UPDATED,
    ALIGNMENT_CHANGED,
    MARKET_CONDITION_CHANGED,
    TRADING_PERMISSION_CHANGED,
)
from multi_timeframe.modules.alignment import AlignmentAnalyzer
from multi_timeframe.modules.condition import ConditionAnalyzer
from multi_timeframe.modules.permission import PermissionAnalyzer
from utils.logger import log_info, log_error

_HISTORY_LIMIT = 500


class MTFUnit:
    """Tracks TradingContextSnapshots across all timeframes for one symbol."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self._contexts: dict[str, dict[str, Any] | None] = {
            tf: None for tf in HIERARCHY
        }
        self._history: deque[MTFSnapshot] = deque(maxlen=_HISTORY_LIMIT)
        self._last_level = ""
        self._last_condition = ""
        self._last_permission = ""

    def update(self, payload: dict) -> MTFSnapshot | None:
        interval = payload.get("interval", "")
        if interval not in self._contexts:
            return None

        self._contexts[interval] = payload

        # Produce once we have at least one timeframe context available
        available = [tf for tf, c in self._contexts.items() if c is not None]
        if not available:
            return None

        alignment = AlignmentAnalyzer.evaluate(self._contexts)
        condition = ConditionAnalyzer.evaluate(alignment, self._contexts)
        permission_data = PermissionAnalyzer.evaluate(
            alignment, condition, self._contexts
        )

        # Institutional bias from the highest available timeframe
        top_available = min(available, key=lambda tf: HIERARCHY.index(tf))
        htf_ctx = self._contexts.get(top_available)
        htf_bias = htf_ctx.get("overall_bias", "NEUTRAL") if htf_ctx else "NEUTRAL"

        # Overall confidence: weighted average across populated TFs
        confidences = [
            c.get("confidence", 0) or 0 for c in self._contexts.values() if c
        ]
        avg_conf = int(sum(confidences) / len(confidences)) if confidences else 0

        # Per-timeframe summary for output
        tf_summary = {}
        for tf in HIERARCHY:
            ctx = self._contexts.get(tf)
            if ctx:
                tf_summary[tf] = {
                    "bias": ctx.get("overall_bias", "NEUTRAL"),
                    "trend": ctx.get("trend", ""),
                    "confidence": ctx.get("confidence", 0),
                    "mode": ctx.get("recommended_mode", ""),
                }

        snap = MTFSnapshot(
            symbol=self.symbol,
            timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            timeframes=tf_summary,
            alignment_level=alignment["level"],
            alignment_score=alignment["score"],
            institutional_bias=htf_bias,
            market_condition=condition,
            execution_timeframe=dict(EXECUTION_TF),
            trading_permission=permission_data["permission"],
            overall_confidence=avg_conf,
            warnings=permission_data["warnings"],
        )

        self._history.append(snap)
        self._last_level = alignment["level"]
        self._last_condition = condition
        self._last_permission = permission_data["permission"]
        return snap

    def latest(self) -> dict[str, Any] | None:
        if self._history:
            return self._history[-1].to_dict()
        return None

    def history(self, count: int = 100) -> list[dict[str, Any]]:
        return [s.to_dict() for s in list(self._history)[-count:]]


class MTFEngine:
    """Subscribes to TRADING_CONTEXT_UPDATED, produces MTFSnapshot."""

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._units: dict[str, MTFUnit] = {}
        self._stats = {
            "total_updates": 0,
            "total_errors": 0,
            "alignment_distribution": {},
            "condition_distribution": {},
            "permission_distribution": {},
            "start_time": datetime.now(timezone.utc).isoformat(),
        }
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self._event_bus.subscribe(
            TRADING_CONTEXT_UPDATED, self._on_context, name="mtf_engine"
        )
        log_info("MTFEngine started")

    async def stop(self):
        self._running = False
        log_info("MTFEngine stopped")

    async def _on_context(self, event: Event):
        if not self._running:
            return
        try:
            payload = event.payload
            symbol = payload.get("symbol", "")
            snapshot_data = payload.get("snapshot", payload)
            if not symbol:
                return

            if symbol not in self._units:
                self._units[symbol] = MTFUnit(symbol)

            snap = self._units[symbol].update(snapshot_data)
            if snap:
                self._stats["total_updates"] += 1
                d = snap.to_dict()
                self._stats["alignment_distribution"][d["alignment_level"]] = (
                    self._stats["alignment_distribution"].get(d["alignment_level"], 0)
                    + 1
                )
                self._stats["condition_distribution"][d["market_condition"]] = (
                    self._stats["condition_distribution"].get(d["market_condition"], 0)
                    + 1
                )
                self._stats["permission_distribution"][d["trading_permission"]] = (
                    self._stats["permission_distribution"].get(
                        d["trading_permission"], 0
                    )
                    + 1
                )

                ev = Event(type=MTF_UPDATED, source="mtf_engine", payload=d)
                await self._event_bus.publish(ev)

        except Exception as e:
            self._stats["total_errors"] += 1
            log_error("MTFEngine error", error=str(e))

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
