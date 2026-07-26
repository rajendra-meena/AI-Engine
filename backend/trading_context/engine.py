"""
Trading Context Engine

Merges IndicatorSnapshot + MarketStructureSnapshot + PatternSnapshot into
a single TradingContextSnapshot describing institutional market conditions.

Subscribes to: INDICATORS_UPDATED, STRUCTURE_UPDATED, PATTERN_DETECTED
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

from core.event_bus import EventBus, Event
from indicators.events import INDICATORS_UPDATED
from market_structure.events import STRUCTURE_UPDATED
from patterns.events import PATTERN_DETECTED
from trading_context.snapshot import TradingContextSnapshot
from trading_context.events import (
    TRADING_CONTEXT_UPDATED,
    BIAS_CHANGED,
    RISK_CHANGED,
    MODE_CHANGED,
)
from trading_context.modules.trend_context import TrendContext
from trading_context.modules.momentum_context import MomentumContext
from trading_context.modules.volatility_context import VolatilityContext
from trading_context.modules.liquidity_context import LiquidityContext
from trading_context.modules.session_context import SessionContext
from trading_context.modules.strength_context import StrengthContext
from utils.logger import log_info, log_error

_HISTORY_LIMIT = 500


class TradingContextUnit:
    """Holds latest snapshots from upstream engines for one (symbol, interval)."""

    def __init__(self, symbol: str, interval: str):
        self.symbol = symbol
        self.interval = interval
        self._indicator: dict[str, Any] | None = None
        self._structure: dict[str, Any] | None = None
        self._patterns: dict[str, Any] | None = None
        self._sr: dict[str, Any] | None = None
        self._history: deque[TradingContextSnapshot] = deque(maxlen=_HISTORY_LIMIT)
        self._update_count = 0
        self._last_bias: str = ""
        self._last_risk: str = ""
        self._last_mode: str = ""
        # Track candle versions for version-aware barrier
        self._input_versions: dict[str, str] = {}

    def _check_version(self, payload: dict) -> str:
        cv = payload.get("candle_version", "")
        return cv

    def update_indicator(self, payload: dict):
        if (
            payload.get("symbol") == self.symbol
            and payload.get("interval") == self.interval
        ):
            cv = self._check_version(payload)
            if cv:
                self._input_versions["indicator"] = cv
            self._indicator = payload
            self._try_produce()

    def update_structure(self, payload: dict):
        if (
            payload.get("symbol") == self.symbol
            and payload.get("interval") == self.interval
        ):
            cv = self._check_version(payload)
            if cv:
                self._input_versions["structure"] = cv
            self._structure = payload
            self._try_produce()

    def update_patterns(self, payload: dict):
        if (
            payload.get("symbol") == self.symbol
            and payload.get("interval") == self.interval
        ):
            cv = self._check_version(payload)
            if cv:
                self._input_versions["patterns"] = cv
            self._patterns = payload
            self._try_produce()

    def update_sr(self, payload: dict):
        if (
            payload.get("symbol") == self.symbol
            and payload.get("interval") == self.interval
        ):
            cv = self._check_version(payload)
            if cv:
                self._input_versions["sr"] = cv
            self._sr = payload
            self._try_produce()

    def _all_inputs_ready(self) -> tuple[bool, str]:
        """Version-aware barrier: indicator + structure must be ready and same version.

        SR and patterns are beneficial but not mandatory for context.
        Returns (ready: bool, reason: str).
        """
        if not self._indicator:
            return False, "Missing indicator"
        if not self._structure:
            return False, "Missing market structure"
        # At minimum, indicator and structure must agree on candle version
        ind_cv = self._indicator.get("candle_version", "")
        struct_cv = self._structure.get("candle_version", "")
        if ind_cv and struct_cv and ind_cv != struct_cv:
            return False, f"Version mismatch: indicator={ind_cv} vs structure={struct_cv}"
        return True, "Ready"

    def _try_produce(self) -> TradingContextSnapshot | None:
        ready, reason = self._all_inputs_ready()
        if not ready:
            return None

        trend = TrendContext.evaluate(self._indicator, self._structure)
        momentum = MomentumContext.evaluate(self._indicator)
        volatility = VolatilityContext.evaluate(self._indicator, self._patterns)
        liquidity = LiquidityContext.evaluate(self._structure)
        session = SessionContext.evaluate(self._structure.get("timestamp"))
        strength = StrengthContext.evaluate(
            trend, momentum, self._structure, self._patterns
        )

        snap = TradingContextSnapshot(
            symbol=self.symbol,
            interval=self.interval,
            timestamp=self._indicator.get("timestamp", ""),
            trend=trend["bias"],
            trend_strength=trend["strength"],
            momentum=momentum["state"],
            momentum_strength=momentum["strength"],
            volatility=volatility["state"],
            volatility_state=volatility["state"],
            liquidity_state=liquidity["state"],
            market_phase=self._structure.get("market_phase", "undefined"),
            session=session["session"],
            pattern_bias=(
                self._patterns.get("pattern_direction", "NEUTRAL").upper()
                if self._patterns
                else "NEUTRAL"
            ),
            structure_bias=self._structure.get("trend", "NEUTRAL"),
            indicator_bias=trend["bias"],
            overall_bias=strength["overall_bias"],
            overall_strength=strength["overall_strength"],
            confidence=strength["confidence"],
            risk_level=strength["risk_level"],
            recommended_mode=strength["recommended_mode"],
            warnings=strength["warnings"],
        )

        self._history.append(snap)
        self._update_count += 1
        self._last_bias = strength["overall_bias"]
        self._last_risk = strength["risk_level"]
        self._last_mode = strength["recommended_mode"]
        return snap

    def latest(self) -> dict[str, Any] | None:
        if self._history:
            return self._history[-1].to_dict()
        return None

    def history(self, count: int = 100) -> list[dict[str, Any]]:
        return [s.to_dict() for s in list(self._history)[-count:]]

    def get_state(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "has_indicator": self._indicator is not None,
            "has_structure": self._structure is not None,
            "has_patterns": self._patterns is not None,
            "update_count": self._update_count,
            "snapshots": len(self._history),
        }


class TradingContextEngine:
    """Aggregates indicators, structure, and patterns into unified context."""

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._units: dict[tuple[str, str], TradingContextUnit] = {}
        self._stats = {
            "total_updates": 0,
            "total_errors": 0,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "bias_distribution": {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0},
            "mode_distribution": {},
        }
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self._event_bus.subscribe(
            INDICATORS_UPDATED, self._on_indicator, name="trading_context_indicator"
        )
        self._event_bus.subscribe(
            STRUCTURE_UPDATED, self._on_structure, name="trading_context_structure"
        )
        self._event_bus.subscribe(
            PATTERN_DETECTED, self._on_patterns, name="trading_context_patterns"
        )
        log_info("TradingContextEngine started")

    async def stop(self):
        self._running = False
        log_info("TradingContextEngine stopped")

    async def _on_indicator(self, event: Event):
        await self._route("indicator", event.payload)

    async def _on_structure(self, event: Event):
        await self._route("structure", event.payload)

    async def _on_patterns(self, event: Event):
        await self._route("patterns", event.payload)

    async def _route(self, source: str, payload: dict):
        if not self._running:
            return
        try:
            symbol = payload.get("symbol", "")
            interval = payload.get("interval", "")
            if not symbol or not interval:
                return

            key = (symbol, interval)
            if key not in self._units:
                self._units[key] = TradingContextUnit(symbol, interval)

            unit = self._units[key]
            if source == "indicator":
                unit.update_indicator(payload)
            elif source == "structure":
                unit.update_structure(payload)
            elif source == "patterns":
                unit.update_patterns(payload)

            snap = unit.latest()
            if snap:
                self._stats["total_updates"] += 1
                self._stats["bias_distribution"][snap["overall_bias"]] = (
                    self._stats["bias_distribution"].get(snap["overall_bias"], 0) + 1
                )
                self._stats["mode_distribution"][snap["recommended_mode"]] = (
                    self._stats["mode_distribution"].get(snap["recommended_mode"], 0)
                    + 1
                )

                ev = Event(
                    type=TRADING_CONTEXT_UPDATED,
                    source="trading_context_engine",
                    payload={
                        "symbol": symbol,
                        "interval": interval,
                        "candle_version": payload.get("candle_version", ""),
                        "analysis_cycle_id": payload.get("analysis_cycle_id", ""),
                        "snapshot": snap,
                    },
                )
                await self._event_bus.publish(ev)

        except Exception as e:
            self._stats["total_errors"] += 1
            log_error("TradingContextEngine error", error=str(e))

    def latest(self, symbol: str, interval: str) -> dict[str, Any] | None:
        unit = self._units.get((symbol, interval))
        return unit.latest() if unit else None

    def history(
        self, symbol: str, interval: str, count: int = 100
    ) -> list[dict[str, Any]]:
        unit = self._units.get((symbol, interval))
        return unit.history(count) if unit else []

    def get_stats(self) -> dict[str, Any]:
        s = dict(self._stats)
        s["running"] = self._running
        s["units"] = len(self._units)
        s["avg_confidence"] = 0  # simplified
        return s
