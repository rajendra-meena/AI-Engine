"""
AI Decision Intelligence Engine — Capstone engine.

Subscribes to TRADING_CONTEXT_UPDATED, MTF_UPDATED, SR_UPDATED.
Runs all sub-engines and produces a final DecisionSnapshot.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

from core.event_bus import EventBus, Event
from trading_context.events import TRADING_CONTEXT_UPDATED
from multi_timeframe.events import MTF_UPDATED
from support_resistance.events import SUPPORT_RESISTANCE_UPDATED
from ai_decision.snapshot import DecisionSnapshot
from ai_decision.events import AI_DECISION_UPDATED
from ai_decision.modules.score import ScoreEngine
from ai_decision.modules.confidence import ConfidenceEngine
from ai_decision.modules.risk import RiskEngine
from ai_decision.modules.trade_plan import TradePlanner
from ai_decision.modules.orchestrator import Orchestrator
from utils.logger import log_info, log_error

_HISTORY_LIMIT = 200


class AIUnit:
    """Tracks data for one symbol and produces decisions."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self._context: dict[str, Any] | None = None
        self._mtf: dict[str, Any] | None = None
        self._sr: dict[str, Any] | None = None
        self._history: deque[DecisionSnapshot] = deque(maxlen=_HISTORY_LIMIT)
        self._update_count = 0
        # Track candle versions for version-aware barrier
        self._input_versions: dict[str, str] = {}
        # ── Version-barrier diagnostics ──
        self._barrier_failure_count = 0
        self._last_barrier_failure: dict[str, Any] | None = None
        self._last_barrier_failure_time: str = ""

    def update_context(self, payload: dict):
        if payload.get("symbol") == self.symbol:
            cv = payload.get("candle_version", "")
            if cv:
                self._input_versions["context"] = cv
            self._context = payload.get("snapshot", payload)
            self._produce()

    def update_mtf(self, payload: dict):
        if payload.get("symbol") == self.symbol:
            cv = payload.get("candle_version", "")
            if cv:
                self._input_versions["mtf"] = cv
            self._mtf = payload
            self._produce()

    def update_sr(self, payload: dict):
        if payload.get("symbol") == self.symbol:
            cv = payload.get("candle_version", "")
            if cv:
                self._input_versions["sr"] = cv
            self._sr = payload
            self._produce()

    def _all_inputs_same_version(self) -> bool:
        """Version-aware barrier: all 3 inputs must share the same candle_version."""
        if len(self._input_versions) < 3:
            self._barrier_failure_count += 1
            missing = [k for k in ("context", "mtf", "sr") if k not in self._input_versions]
            self._last_barrier_failure = {
                "reason": f"Missing inputs: {missing}",
                "context_only": "context" in self._input_versions,
                "versions": dict(self._input_versions),
            }
            self._last_barrier_failure_time = datetime.now(timezone.utc).isoformat()
            return False
        versions = set(self._input_versions.values())
        if len(versions) != 1:
            self._barrier_failure_count += 1
            self._last_barrier_failure = {
                "reason": f"Version mismatch: context={self._input_versions['context']} mtf={self._input_versions['mtf']} sr={self._input_versions['sr']}",
                "versions": dict(self._input_versions),
            }
            self._last_barrier_failure_time = datetime.now(timezone.utc).isoformat()
            return False
        cv = versions.pop()
        return bool(cv)

    def barrier_diagnostics(self) -> dict[str, Any]:
        """Return version-barrier state for monitoring."""
        return {
            "symbol": self.symbol,
            "input_versions": dict(self._input_versions),
            "barrier_failure_count": self._barrier_failure_count,
            "last_barrier_failure": self._last_barrier_failure,
            "last_barrier_failure_time": self._last_barrier_failure_time,
            "has_context": self._context is not None,
            "has_mtf": self._mtf is not None,
            "has_sr": self._sr is not None,
        }

    def _produce(self):
        if not self._context:
            return
        # Version barrier: require all inputs on same candle_version
        if not self._all_inputs_same_version():
            return

        score_result = ScoreEngine.evaluate(self._context, self._mtf, self._sr)
        conf_result = ConfidenceEngine.evaluate(self._context, self._mtf, None)
        risk_result = RiskEngine.evaluate(self._context, self._mtf, self._sr)
        plan = TradePlanner.evaluate(
            score_result, conf_result, risk_result, self._context, self._mtf, self._sr
        )
        final = Orchestrator.orchestrate(
            score_result, conf_result, risk_result, plan, self._context, self._mtf
        )

        snap = DecisionSnapshot(
            symbol=self.symbol,
            timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            decision=final["decision"],
            score=final["score"],
            score_grade=final["score_grade"],
            confidence=final["confidence"],
            confidence_grade=final["confidence_grade"],
            risk_level=final["risk_level"],
            risk_score=final["risk_score"],
            max_risk_percent=final["max_risk_percent"],
            trade_plan=final.get("trade_plan"),
            reasoning=final.get("reasoning"),
            warnings=final.get("warnings"),
        )
        self._history.append(snap)
        self._update_count += 1
        return snap

    def latest(self) -> dict[str, Any] | None:
        return self._history[-1].to_dict() if self._history else None

    def history(self, count: int = 100) -> list[dict[str, Any]]:
        return [s.to_dict() for s in list(self._history)[-count:]]


class AIDecisionEngine:
    """Capstone engine — subscribes to 3 events, produces decisions."""

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._units: dict[str, AIUnit] = {}
        self._stats = {
            "total_decisions": 0,
            "total_errors": 0,
            "decision_distribution": {},
            "start_time": datetime.now(timezone.utc).isoformat(),
        }
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self._event_bus.subscribe(
            TRADING_CONTEXT_UPDATED, self._on_context, name="ai_decision_context"
        )
        self._event_bus.subscribe(MTF_UPDATED, self._on_mtf, name="ai_decision_mtf")
        self._event_bus.subscribe(SUPPORT_RESISTANCE_UPDATED, self._on_sr, name="ai_decision_sr")
        log_info("AIDecisionEngine started")

    async def stop(self):
        self._running = False
        log_info("AIDecisionEngine stopped", decisions=self._stats["total_decisions"])

    async def _on_context(self, event: Event):
        if not self._running:
            return
        try:
            symbol = event.payload.get("symbol", "")
            if symbol:
                self._get_unit(symbol).update_context(event.payload)
                self._stats["total_decisions"] += 1
        except Exception as e:
            self._stats["total_errors"] += 1
            log_error("AIDecisionEngine error", error=str(e))

    async def _on_mtf(self, event: Event):
        if not self._running:
            return
        try:
            symbol = event.payload.get("symbol", "")
            if symbol:
                self._get_unit(symbol).update_mtf(event.payload)
        except Exception:
            pass

    async def _on_sr(self, event: Event):
        if not self._running:
            return
        try:
            symbol = event.payload.get("symbol", "")
            if symbol:
                self._get_unit(symbol).update_sr(event.payload)
        except Exception:
            pass

    def _get_unit(self, symbol: str) -> AIUnit:
        if symbol not in self._units:
            self._units[symbol] = AIUnit(symbol)
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
        # Barrier diagnostics for all symbols
        s["barrier_diagnostics"] = {
            sym: unit.barrier_diagnostics()
            for sym, unit in self._units.items()
        }
        return s
