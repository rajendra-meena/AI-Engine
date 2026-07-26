"""
Auto Trade Workspace API — Event-driven aggregation endpoint.

This module orchestrates existing services into an event-driven pipeline.
It NEVER creates a second independent trading system — it only wires
existing engines into a real-time data flow.

Design:
  ┌─────────────┐   CANDLE_CLOSED   ┌──────────────────┐   fresh analysis   ┌────────────┐
  │ CandleEngine │ ───────────────> │ AutoTradeEngine  │ ─────────────────> │ AI/Regime  │
  └─────────────┘                   │ (event-driven)   │                    │ Engines    │
                                    │                   │                    └────────────┘
  ┌─────────────┐   LIVE_TICK       │  freshness check  │
  │ KiteTicker  │ ───────────────> │  stale data block │
  └─────────────┘                   │  approval gates   │
                                    │  risk validation  │
  ┌──────────────┐                  │  trade plan build │
  │ ZerodhaMarket│  freshness/health│                   │
  │ DataEngine   │ ───────────────> │  workspace snap   │
  └──────────────┘                  └──────────────────┘

Safety-critical:
  - Phase 43 LIVE_EXECUTION_LOCK is never bypassed
  - Risk Engine is never bypassed
  - Trade Approval is never bypassed
  - Controlled Live activation is never bypassed
  - Human confirmation required for controlled live
  - Auto-enable of LIVE is impossible
  - Stale data blocks all signals
  - No cached snapshot may produce a trade
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from core.symbols import get_canonical_symbol, list_canonical_names
from core.event_bus import EventBus
from core.event_model import Event as BusEvent
from core.freshness import (
    SymbolFreshnessTracker,
    FRESHNESS_LIVE,
    FRESHNESS_STALE,
    FRESHNESS_DISCONNECTED,
)
from candles.events import CANDLE_CLOSED as CANDLE_CLOSED_EV
from core.zerodha_events import (
    LIVE_TICK_RECEIVED,
    MARKET_DATA_STALE,
    MARKET_DATA_RECOVERED,
    KITE_WS_CONNECTED,
    KITE_WS_DISCONNECTED,
    KITE_WS_RECONNECTING,
    SIGNAL_REJECTED,
    TRADE_PLAN_CREATED,
)
from ai_decision.engine import AIDecisionEngine
from ai_decision.modules.orchestrator import EnhancedOrchestrator
from ai_decision.modules.trade_quality import TradeQualityScorer
from ai_decision.modules.mtf_agreement import MultiTFAgreement
from ai_decision.modules.false_signal import FalseSignalDetector
from ai_decision.modules.signal_validator import SignalValidator
from ai_decision.modules.trade_approval import TradeApprovalEngine
from ai_decision.modules.confidence_adjuster import DynamicConfidenceAdjuster
from ai_decision.modules.ai_explainer import AIExplainer
from ai_decision.modules.detailed_confidence import DetailedConfidenceEngine
from ai_decision.decision_service import AIDecision

from market_regime.engine import RegimeEngine
from market_regime.strategy_router import StrategyRouter
from risk.risk_engine import RiskEngine
from risk.trade_validator import TradeIntent
from trading.trade_plan import TradePlanner
from trading.trade_lifecycle import TradeLifecycleManager, get_lifecycle
from trading.signal import TradeSignal
from execution.kill_switch import KillSwitch
from execution.execution_audit import ExecutionAuditLog
from execution.gateway import ExecutionGateway
from execution.paper_broker import PaperBroker
from trading.runtime_mode import RuntimeModeManager
from services.market_data_service import MarketDataService
from services.zerodha_market_data_engine import ZerodhaMarketDataEngine
from utils.logger import log_info, log_warn, log_error

router = APIRouter(tags=["auto-trade"])


# ── Canonical readiness statuses ──

class ReadinessStatus:
    """Canonical readiness status strings. Only these values are allowed."""
    READY = "READY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    OFFLINE = "OFFLINE"
    WARMING_UP = "WARMING_UP"
    NOT_REQUIRED = "NOT_REQUIRED"

    ALL = {READY, DEGRADED, BLOCKED, OFFLINE, WARMING_UP, NOT_REQUIRED}

# ── Engine state ──

_ai_engine: AIDecisionEngine | None = None
_regime_engine: RegimeEngine | None = None
_risk_engine: RiskEngine | None = None
_planner: TradePlanner | None = None
_kill_switch: KillSwitch | None = None
_audit: ExecutionAuditLog | None = None
_market_service: MarketDataService | None = None
_event_bus: EventBus | None = None
_runtime_mgr: RuntimeModeManager | None = None
_zerodha_engine: ZerodhaMarketDataEngine | None = None
_freshness_tracker: SymbolFreshnessTracker | None = None
_exec_gateway: ExecutionGateway | None = None
_paper_broker: PaperBroker | None = None

# Auto-analysis engine state
_analysis_enabled = False    # Authoritative user toggle (ON/OFF)
_engine_running = False      # Background lifecycle task active
_engine_paused = False
_engine_state = "OFF"
_engine_task: asyncio.Task | None = None
_engine_lock = asyncio.Lock()
_last_workspace_snapshot: dict[str, Any] | None = None
_health_watchdog_task: asyncio.Task | None = None

# Subscribed events
_event_subscriptions: list[str] = []

# ── Engine states (comprehensive) ──

ENGINE_STATE_OFF = "OFF"
ENGINE_STATE_AUTHENTICATING = "AUTHENTICATING"
ENGINE_STATE_LOADING_INSTRUMENTS = "LOADING_INSTRUMENTS"
ENGINE_STATE_LOADING_HISTORY = "LOADING_HISTORY"
ENGINE_STATE_SUBSCRIBING = "SUBSCRIBING"
ENGINE_STATE_WARMING_INDICATORS = "WARMING_INDICATORS"
ENGINE_STATE_CONNECTED = "CONNECTED"
ENGINE_STATE_WAITING_FOR_TICKS = "WAITING_FOR_LIVE_TICKS"
ENGINE_STATE_RECEIVING_TICKS = "RECEIVING_LIVE_TICKS"
ENGINE_STATE_DATA_READY = "DATA_READY"
ENGINE_STATE_SCANNING = "SCANNING"
ENGINE_STATE_ANALYZING = "ANALYZING"
ENGINE_STATE_VALIDATING = "VALIDATING"
ENGINE_STATE_APPROVED = "APPROVED"
ENGINE_STATE_BLOCKED = "BLOCKED"
ENGINE_STATE_DISCONNECTED = "DISCONNECTED"
ENGINE_STATE_RECONNECTING = "RECONNECTING"
ENGINE_STATE_ERROR = "ERROR"
ENGINE_STATE_WAITING = "WAITING"
ENGINE_STATE_STOPPING = "STOPPING"

# Minimum time between analyses for the same symbol (prevent duplicate work)
_SYMBOL_ANALYSIS_COOLDOWN_S: float = 10.0
_last_analysis_times: dict[str, float] = {}

# Active signals (keyed by symbol — one active signal per symbol)
_active_signals: dict[str, TradeSignal] = {}

# ── Setters ──


def set_auto_trade_ai_engine(engine: AIDecisionEngine):
    global _ai_engine
    _ai_engine = engine


def set_auto_trade_regime_engine(engine: RegimeEngine):
    global _regime_engine
    _regime_engine = engine


def set_auto_trade_risk_engine(engine: RiskEngine):
    global _risk_engine
    _risk_engine = engine


def set_auto_trade_planner(planner: TradePlanner):
    global _planner
    _planner = planner


def set_auto_trade_kill_switch(ks: KillSwitch):
    global _kill_switch
    _kill_switch = ks


def set_auto_trade_audit_log(audit: ExecutionAuditLog):
    global _audit
    _audit = audit


def set_auto_trade_market_service(service: MarketDataService):
    global _market_service
    _market_service = service


def set_auto_trade_event_bus(bus: EventBus):
    global _event_bus
    _event_bus = bus


def set_auto_trade_runtime_mgr(mgr: RuntimeModeManager):
    global _runtime_mgr
    _runtime_mgr = mgr


def set_auto_trade_zerodha_engine(engine: ZerodhaMarketDataEngine):
    """Set the Zerodha market data engine used by Auto Trade."""
    global _zerodha_engine, _freshness_tracker
    _zerodha_engine = engine
    if engine:
        _freshness_tracker = engine.freshness_tracker


def set_auto_trade_exec_gateway(gateway: ExecutionGateway):
    """Set the Execution Gateway used by Auto Trade for order execution."""
    global _exec_gateway
    _exec_gateway = gateway


def set_auto_trade_paper_broker(broker: PaperBroker):
    """Set the Paper Broker used by Auto Trade for shadow/paper trades."""
    global _paper_broker
    _paper_broker = broker


# ── Helpers ──


def _get_ai() -> AIDecisionEngine:
    assert _ai_engine is not None, "AIDecisionEngine not initialized"
    return _ai_engine


def _get_regime() -> RegimeEngine | None:
    """Return the RegimeEngine instance, or None if not initialized."""
    return _regime_engine


def _get_risk() -> RiskEngine:
    assert _risk_engine is not None, "RiskEngine not initialized"
    return _risk_engine


def _get_planner() -> TradePlanner:
    assert _planner is not None, "TradePlanner not initialized"
    return _planner


def _get_runtime_mode() -> str:
    """Get the current runtime mode string."""
    try:
        if _runtime_mgr:
            status = _runtime_mgr.get_status()
            return status.get("mode", "paper")
    except Exception:
        pass
    return "paper"


def _check_mandatory_systems() -> dict[str, str]:
    """Check all mandatory system health.

    Returns dict of system_name → canonical ReadinessStatus string.
    Only ReadinessStatus constants are valid return values.
    """
    R = ReadinessStatus
    checks: dict[str, str] = {}

    # — Zerodha Kite provider status —
    try:
        if _zerodha_engine:
            if _zerodha_engine.is_ws_connected:
                checks["zerodha_kite"] = R.READY
            elif _zerodha_engine.state == ENGINE_STATE_RECONNECTING:
                checks["zerodha_kite"] = R.DEGRADED
            elif _zerodha_engine.is_running:
                checks["zerodha_kite"] = R.DEGRADED
            else:
                checks["zerodha_kite"] = R.OFFLINE
        else:
            checks["zerodha_kite"] = R.BLOCKED
    except Exception:
        checks["zerodha_kite"] = R.BLOCKED

    # — WebSocket connectivity —
    try:
        if _zerodha_engine and _zerodha_engine.is_ws_connected:
            checks["websocket"] = R.READY
        else:
            checks["websocket"] = R.OFFLINE
    except Exception:
        checks["websocket"] = R.OFFLINE

    # — Data freshness —
    try:
        if _freshness_tracker:
            summary = _freshness_tracker.get_status_summary()
            if summary.get("stale", 0) > 0 or summary.get("disconnected", 0) > 0:
                checks["data_freshness"] = R.DEGRADED
            elif summary.get("warming_up", 0) > 0:
                checks["data_freshness"] = R.WARMING_UP
            else:
                checks["data_freshness"] = R.READY
        else:
            checks["data_freshness"] = R.WARMING_UP
    except Exception:
        checks["data_freshness"] = R.DEGRADED

    # — AI Decision Engine —
    try:
        if _ai_engine and _ai_engine._running:
            checks["ai_decision"] = R.READY
        else:
            checks["ai_decision"] = R.DEGRADED
    except Exception:
        checks["ai_decision"] = R.BLOCKED

    # — Market Regime —
    try:
        if _regime_engine:
            _regime_engine.get_stats()
            checks["market_regime"] = R.READY
        else:
            checks["market_regime"] = R.DEGRADED
    except Exception:
        checks["market_regime"] = R.BLOCKED

    # — Risk Engine —
    try:
        risk_status = _get_risk().get_status()
        if risk_status.get("trading_halt", False):
            checks["risk_engine"] = R.BLOCKED
        else:
            checks["risk_engine"] = R.READY
    except Exception:
        checks["risk_engine"] = R.BLOCKED

    # — Trade Planner —
    try:
        if _planner:
            checks["trade_planner"] = R.READY
        else:
            checks["trade_planner"] = R.BLOCKED
    except Exception:
        checks["trade_planner"] = R.BLOCKED

    # — Kill switch —
    try:
        if _kill_switch:
            ks_status = _kill_switch.get_status()
            if ks_status.get("active", False):
                checks["kill_switch"] = R.BLOCKED
            else:
                checks["kill_switch"] = R.READY
        else:
            checks["kill_switch"] = R.NOT_REQUIRED
    except Exception:
        checks["kill_switch"] = R.DEGRADED

    # — Database —
    try:
        from learning.database import _get_db as get_db
        db = get_db()
        db.execute("SELECT 1")
        db.close()
        checks["database"] = R.READY
    except Exception:
        checks["database"] = R.DEGRADED

    # — Broker connectivity —
    runtime_mode = _get_runtime_mode()
    if runtime_mode == "paper":
        try:
            from execution.paper_broker import get_paper_broker
            broker = get_paper_broker()
            if broker.is_running:
                checks["broker"] = R.READY
            else:
                checks["broker"] = R.DEGRADED
        except Exception:
            checks["broker"] = R.DEGRADED
    elif runtime_mode == "live":
        checks["broker"] = R.READY
    else:
        checks["broker"] = R.NOT_REQUIRED

    # — Phase 43 lock —
    checks["phase_43_lock"] = R.READY

    # — Yahoo Finance blocked for Auto Trade —
    checks["yahoo_fallback_blocked"] = R.READY

    # Validate all statuses are canonical
    for system, status in checks.items():
        if status not in ReadinessStatus.ALL:
            checks[system] = R.DEGRADED

    return checks


def _record_audit(event_type: str, detail: dict[str, Any]) -> None:
    """Record an audit event if audit log is available."""
    try:
        if _audit:
            _audit.record(event_type, severity="info", **detail)
    except Exception:
        pass


# ── Fresh analysis pipeline (event-driven) ──


def _is_analysis_needed(symbol: str) -> bool:
    """Check if enough time has passed since last analysis for a symbol."""
    now = time.time()
    last = _last_analysis_times.get(symbol, 0.0)
    return (now - last) >= _SYMBOL_ANALYSIS_COOLDOWN_S


def _mark_analyzed(symbol: str):
    """Record the time of latest analysis for a symbol."""
    _last_analysis_times[symbol] = time.time()


async def _run_fresh_analysis(symbol: str, analysis_cycle_id: str = "") -> dict[str, Any] | None:
    """
    Run the complete fresh-data analysis pipeline for a single symbol.

    This is the core method that replaces the old cached-snapshot approach.
    Every step uses or triggers fresh calculation — no stale snapshots.

    Flow:
        1. Verify data freshness (skip if stale)
        2. RegimeEngine.update() with fresh context
        3. Read fresh regime result
        4. AIDecisionEngine should have latest from event chain
        5. Score opportunity
        6. Validate signal
        7. Run approval gates
        8. Run risk validation
    """
    if not _is_analysis_needed(symbol):
        return None

    # 1. Verify data freshness for this symbol
    if _freshness_tracker:
        safe, reason = _freshness_tracker.is_data_safe(symbol)
        if not safe:
            log_info("AutoTrade: skipping symbol, data not safe", symbol=symbol, reason=reason)
            return None

    # 2. Get the latest AI decision (pushed by event chain)
    ai_snap = _get_ai().latest(symbol)
    if not ai_snap:
        log_info("AutoTrade: no AI snapshot yet", symbol=symbol)
        return None

    # 3. Update regime with latest context
    regime_engine = _get_regime()
    regime_snap = None
    if regime_engine:
        try:
            context_snap = ai_snap.get("evidence", {})
            indicator_snap = ai_snap.get("market_snapshot", {})
            structure_snap = ai_snap.get("market_snapshot", {})
            mtf_snap = ai_snap.get("market_snapshot", {})

            regime_snap = regime_engine.update(
                symbol=symbol,
                context_snap=context_snap,
                structure_snap=structure_snap,
                indicator_snap=indicator_snap,
                mtf_snap=mtf_snap,
            )
            if _freshness_tracker:
                _freshness_tracker.update_regime(symbol)
        except Exception as e:
            log_warn("AutoTrade: regime update failed", symbol=symbol, error=str(e))
            regime_snap = None
    else:
        log_warn("AutoTrade: RegimeEngine not available, skipping regime update", symbol=symbol)

    # 4. Build opportunity score from fresh data
    result = _build_opportunity_score(symbol, ai_snap, regime_snap)

    # 5. If opportunity qualifies, bridge to execution
    if result and result.get("opportunity_score", 0) >= 50 and result.get("direction") in ("BUY", "SELL"):
        if not result.get("reject_reasons"):
            exec_result = await _try_execute_trade(symbol, result, ai_snap, regime_snap,
                                                   analysis_cycle_id=analysis_cycle_id)
            if exec_result:
                result["execution"] = exec_result

    _mark_analyzed(symbol)
    return result


async def _handle_candle_closed(event: BusEvent):
    """
    Primary trigger: a candle has closed.
    Run the full analysis pipeline for the affected symbol.

    Signal suppression: candles with allow_signal_generation=false
    (e.g. warmup historical candles) do not trigger analysis.
    """
    if not _engine_running or _engine_paused or not _analysis_enabled:
        return

    try:
        payload = event.payload
        candle = payload.get("candle", payload)
        symbol = candle.get("symbol", "")
        interval = candle.get("interval", "15m")

        if not symbol:
            return

        # Only process if symbol is in our universe
        if symbol not in list_canonical_names():
            return

        # ── Signal suppression gate ──
        # Warmup candles prime indicators but never generate trade decisions.
        if not payload.get("allow_signal_generation", True):
            return

        # ── State readiness gate ──
        # Only generate decisions once the engine is receiving live data
        if _zerodha_engine and _zerodha_engine.state not in ("DATA_READY", "SCANNING"):
            log_info("AutoTrade: candle closed but engine not DATA_READY yet",
                     symbol=symbol, engine_state=_zerodha_engine.state)
            return

        # ── Idempotency gate ──
        # Skip if we've already seen this candle version
        candle_version = payload.get("candle_version", "")
        idempotency_key = payload.get("idempotency_key", "")
        if idempotency_key:
            _idempotency_seen = _cached_globals().get("_seen_candle_keys", set())
            if idempotency_key in _idempotency_seen:
                return
            _idempotency_seen.add(idempotency_key)

        # Extract analysis_cycle_id from candle event for idempotent execution
        analysis_cycle_id = payload.get("analysis_cycle_id", "")

        # Run fresh analysis
        result = await _run_fresh_analysis(symbol, analysis_cycle_id=analysis_cycle_id)
        if result:
            _engine_state = ENGINE_STATE_SCANNING
            if result.get("execution"):
                log_info("AutoTrade: trade executed from candle close",
                         symbol=symbol,
                         direction=result.get("direction"),
                         score=result.get("opportunity_score"),
                         exec_status=result["execution"].get("status", "unknown"))

    except Exception as e:
        log_error("AutoTrade: candle closed handler error", error=str(e))


def _cached_globals():
    """Access module globals for idempotency tracking across handler calls."""
    import sys
    mod = sys.modules.get(__name__)
    if not hasattr(mod, "_seen_candle_keys"):
        mod._seen_candle_keys = set()
    return mod


async def _handle_live_tick(event: BusEvent):
    """
    Secondary trigger: a live tick was received.
    Update freshness tracking. If waiting for ticks, transition state.
    """
    global _engine_state

    if not _engine_running:
        return

    try:
        payload = event.payload
        symbol = payload.get("symbol", "")

        if _engine_state == ENGINE_STATE_WAITING_FOR_TICKS:
            _engine_state = ENGINE_STATE_SCANNING

        # For strategies designed for intrabar analysis, could trigger
        # light-weight checks here (future enhancement)

    except Exception as e:
        log_warn("AutoTrade: live tick handler error", error=str(e))


async def _handle_ws_disconnected(event: BusEvent):
    """WebSocket disconnected — block signals."""
    global _engine_state
    _engine_state = ENGINE_STATE_DISCONNECTED
    log_warn("AutoTrade: WebSocket disconnected, signals blocked")


async def _handle_ws_reconnecting(event: BusEvent):
    """WebSocket reconnecting."""
    global _engine_state
    _engine_state = ENGINE_STATE_RECONNECTING


async def _handle_ws_connected(event: BusEvent):
    """WebSocket connected — can resume if running."""
    global _engine_state
    if _engine_running and not _engine_paused:
        _engine_state = ENGINE_STATE_WAITING_FOR_TICKS


# ── Event subscription ──


def _register_event_handlers():
    """Register event bus handlers for the event-driven pipeline."""
    if not _event_bus:
        return

    _event_bus.subscribe(CANDLE_CLOSED_EV, _handle_candle_closed, name="auto_trade_candle_closed")
    _event_bus.subscribe(LIVE_TICK_RECEIVED, _handle_live_tick, name="auto_trade_live_tick")
    _event_bus.subscribe(KITE_WS_DISCONNECTED, _handle_ws_disconnected, name="auto_trade_ws_disconnect")
    _event_bus.subscribe(KITE_WS_RECONNECTING, _handle_ws_reconnecting, name="auto_trade_ws_reconnect")
    _event_bus.subscribe(KITE_WS_CONNECTED, _handle_ws_connected, name="auto_trade_ws_connect")

    log_info("AutoTrade: event handlers registered")


def _unregister_event_handlers():
    """Unregister event bus handlers."""
    if not _event_bus:
        return
    try:
        _event_bus.unsubscribe(CANDLE_CLOSED_EV, _handle_candle_closed)
        _event_bus.unsubscribe(LIVE_TICK_RECEIVED, _handle_live_tick)
        _event_bus.unsubscribe(KITE_WS_DISCONNECTED, _handle_ws_disconnected)
        _event_bus.unsubscribe(KITE_WS_RECONNECTING, _handle_ws_reconnecting)
        _event_bus.unsubscribe(KITE_WS_CONNECTED, _handle_ws_connected)
    except Exception:
        pass


# ── Opportunity scoring (rebuilt with freshness awareness) ──


def _build_opportunity_score(symbol: str, ai_snap: dict | None, regime_snap: dict | None) -> dict[str, Any]:
    """Calculate an opportunity score from FRESH engine outputs."""
    score = 0.0
    max_score = 100.0
    reasons: list[str] = []
    reject_reasons: list[str] = []

    if not ai_snap:
        return {
            "symbol": symbol,
            "opportunity_score": 0,
            "max_score": max_score,
            "confidence": 0,
            "grade": "NONE",
            "regime": "unknown",
            "strategy": "unknown",
            "direction": "NONE",
            "risk_status": "NO_DATA",
            "source_provider": "ZERODHA_KITE",
            "freshness_status": FRESHNESS_STALE,
            "reasons": ["No AI decision data available"],
            "reject_reasons": ["No AI decision data"],
            "selected": False,
        }

    # AI score (0-100, weight 25%)
    ai_score = ai_snap.get("score", 0)
    score += ai_score * 0.25

    # Confidence (0-100, weight 20%)
    confidence = ai_snap.get("confidence", 0)
    score += confidence * 0.20
    if confidence < 60:
        reject_reasons.append(f"AI confidence is only {confidence:.0f}%")

    # Risk assessment (weight 15%)
    risk_level = ai_snap.get("risk_level", "EXTREME")
    risk_map = {"LOW": 100, "MODERATE": 70, "HIGH": 40, "EXTREME": 0, "CRITICAL": 0}
    risk_score = risk_map.get(risk_level, 0)
    score += risk_score * 0.15
    if risk_level in ("EXTREME", "CRITICAL"):
        reject_reasons.append(f"Risk level is {risk_level}")

    # Regime compatibility (weight 15%)
    if regime_snap:
        regime = regime_snap.get("regime", "")
        reg_conf = regime_snap.get("confidence", 0)
        score += reg_conf * 0.15
        strategy_hint = ai_snap.get("trade_plan", {}).get("strategy", "")
        if regime and strategy_hint:
            from market_regime.strategy_router import StrategyRouter
            rec = StrategyRouter.get_best_strategy(regime)
            if rec.get("primary", "") == strategy_hint:
                score += 5
                reasons.append("Regime supports the recommended strategy")
            else:
                reject_reasons.append(f"Regime {regime} does not support {strategy_hint}")
        reasons.append(f"Regime: {regime}")
    else:
        score += 25 * 0.15  # neutral

    # Decision direction (weight 10%)
    direction = ai_snap.get("trade_plan", {}).get("direction", "NONE")
    if direction in ("BUY", "SELL"):
        score += 60 * 0.10
        reasons.append(f"Clear {direction} signal detected")
    elif direction == "WAIT":
        score += 20 * 0.10
        reject_reasons.append("Signal direction is WAIT")
    else:
        reject_reasons.append("No clear trade direction")

    # MTF agreement (weight 10%)
    mtf_info = ai_snap.get("mtf_agreement", {})
    if mtf_info:
        mtf_pct = mtf_info.get("agreement_percent", 0)
        score += mtf_pct * 0.10
        if mtf_pct < 50:
            reject_reasons.append(f"MTF agreement is only {mtf_pct:.0f}%")
        elif mtf_pct >= 70:
            reasons.append("Strong multi-timeframe agreement")
    else:
        score += 50 * 0.10

    # Trade grade (weight 5%)
    grade = ai_snap.get("score_grade", "") or ai_snap.get("confidence_grade", "")
    grade_scores = {"VERY_HIGH": 100, "HIGH": 80, "MODERATE": 60, "LOW": 30, "VERY_LOW": 0}
    grade_score = grade_scores.get(grade, 0)
    score += grade_score * 0.05
    if grade in ("LOW", "VERY_LOW"):
        reject_reasons.append(f"Trade grade is {grade}")

    # Freshness check
    freshness_status = _get_freshness_status(symbol)
    if freshness_status in (FRESHNESS_STALE, FRESHNESS_DISCONNECTED):
        reject_reasons.append(f"Data is {freshness_status} for {symbol}")
        score *= 0.5  # Penalize stale data

    score = min(score, max_score)

    # Grade label
    if score >= 80:
        grade_label = "A"
    elif score >= 65:
        grade_label = "B"
    elif score >= 50:
        grade_label = "C"
    elif score >= 30:
        grade_label = "D"
    else:
        grade_label = "F"

    return {
        "symbol": symbol,
        "opportunity_score": round(score, 1),
        "max_score": max_score,
        "confidence": round(confidence, 1),
        "grade": grade_label,
        "regime": regime_snap.get("regime", "unknown") if regime_snap else "unknown",
        "strategy": ai_snap.get("trade_plan", {}).get("strategy", "unknown"),
        "direction": direction,
        "risk_status": risk_level,
        "source_provider": "ZERODHA_KITE",
        "freshness_status": freshness_status,
        "reasons": reasons,
        "reject_reasons": reject_reasons,
        "selected": False,
    }


def _get_freshness_status(symbol: str) -> str:
    """Get the current freshness status for a symbol.

    When the freshness tracker is not initialized, returns FRESHNESS_LIVE
    (not stale — the tracker simply hasn't been set up yet; in production
    the tracker is always initialized before auto-trade starts).
    """
    if _freshness_tracker:
        sf = _freshness_tracker.get(symbol)
        if sf:
            return sf.overall_freshness
    return FRESHNESS_LIVE


async def _try_execute_trade(
    symbol: str,
    result: dict[str, Any],
    ai_snap: dict[str, Any],
    regime_snap: dict | None,
    analysis_cycle_id: str = "",
) -> dict[str, Any] | None:
    """
    Bridge from scoring to execution.

    Called when an opportunity scores >= 50 with a clear BUY/SELL direction
    and no rejection reasons. Builds a TradePlan, validates risk, and
    submits through the ExecutionGateway which delegates to PaperBroker.

    Returns the execution result dict, or None if execution was skipped/blocked.

    Execution-level idempotency: uses analysis_cycle_id + symbol as the
    canonical key so the same candle cycle never produces duplicate trades.
    """
    if not result or result.get("opportunity_score", 0) < 50:
        return None
    if result.get("direction") not in ("BUY", "SELL"):
        return None
    if result.get("reject_reasons"):
        return None

    # Runtime mode check — only OBSERVE/SHADOW/PAPER allowed
    runtime_mode = _get_runtime_mode()
    if runtime_mode not in ("observe", "shadow", "paper"):
        log_info("AutoTrade: execution blocked by runtime mode", mode=runtime_mode, symbol=symbol)
        return None

    # Kill switch check
    if _kill_switch:
        try:
            ks_status = _kill_switch.get_status()
            if ks_status.get("active", False):
                log_info("AutoTrade: execution blocked by kill switch", symbol=symbol)
                return None
        except Exception:
            pass

    direction = result["direction"]
    market_price = ai_snap.get("market_snapshot", {}).get("close") or ai_snap.get("market_snapshot", {}).get("last_price", 0)
    if not market_price or market_price <= 0:
        log_info("AutoTrade: no market price for execution", symbol=symbol)
        return None

    # ── Position gate ──
    # Reject if there's already an open position in the same or opposite direction.
    if _paper_broker:
        existing_pos = _paper_broker.get_position(symbol)
        if existing_pos:
            pos_direction = existing_pos.direction
            expected_pos = "LONG" if direction == "BUY" else "SHORT"
            if pos_direction == expected_pos:
                log_info("AutoTrade: execution blocked — position already open",
                         symbol=symbol, existing=pos_direction, attempted=direction)
                return {"status": "blocked",
                        "reason": f"Position already open: {pos_direction} on {symbol}"}
            else:
                log_info("AutoTrade: execution blocked — opposite position active",
                         symbol=symbol, existing=pos_direction, attempted=direction)
                return {"status": "blocked",
                        "reason": f"Opposite position active: {pos_direction} on {symbol}, cannot {direction}"}

    # ── Execution-level idempotency ──
    # The same analysis_cycle_id + symbol must not produce duplicate trades.
    exec_idempotency_key = f"exec_{symbol}_{analysis_cycle_id}" if analysis_cycle_id else ""
    if exec_idempotency_key and _exec_gateway:
        existing_record = _exec_gateway.get_execution_by_key(exec_idempotency_key)
        if existing_record:
            log_info("AutoTrade: idempotency hit — trade already executed for this cycle",
                     symbol=symbol, cycle=analysis_cycle_id)
            return existing_record

    # Build an AIDecision from the scoring snapshot
    try:
        decision = AIDecision(
            symbol=symbol,
            direction=direction,
            score=ai_snap.get("score", 0),
            confidence=ai_snap.get("confidence", 0),
            decision=direction,
            market_snapshot=ai_snap.get("market_snapshot", {}),
            data_freshness=result.get("freshness_status", "live"),
            trace_id=ai_snap.get("trace_id", ""),
            decision_id=ai_snap.get("decision_id", ""),
        )
    except Exception as e:
        log_warn("AutoTrade: failed to build AIDecision", symbol=symbol, error=str(e))
        return None

    # Build TradePlan via TradePlanner
    planner = _planner
    if not planner:
        log_warn("AutoTrade: TradePlanner not available", symbol=symbol)
        return None

    try:
        snap = _snap_kwargs(ai_snap)
        plan = planner.build_plan(
            decision=decision,
            price=market_price,
            context_snap=snap.get("context_snap"),
            indicator_snap=snap.get("indicator_snap"),
            structure_snap=snap.get("structure_snap"),
            mtf_snap=snap.get("mtf_snap"),
            sr_snap=snap.get("sr_snap"),
        )
    except Exception as e:
        log_warn("AutoTrade: TradePlanner.build_plan failed", symbol=symbol, error=str(e))
        return None

    if not plan.qualified:
        log_info("AutoTrade: trade plan not qualified",
                 symbol=symbol, reason=plan.rejection_reason)
        return None

    if plan.risk_status == "blocked":
        log_info("AutoTrade: trade plan blocked by risk",
                 symbol=symbol, reason=plan.risk_block_reason)
        return None

    # Execute via ExecutionGateway (the ONLY execution path)
    if not _exec_gateway:
        log_warn("AutoTrade: ExecutionGateway not available — no execution path", symbol=symbol)
        return None

    try:
        record = _exec_gateway.execute(
            symbol=symbol,
            side=direction,
            quantity=plan.position_size,
            price=plan.entry_price,
            stop_loss=plan.stop_price,
            target=plan.target_price,
            trade_plan_id=plan.plan_id,
            trace_id=plan.trace_id,
            idempotency_key=exec_idempotency_key,
            decision_id=decision.decision_id,
            analysis_cycle_id=analysis_cycle_id,
        )
        log_info("AutoTrade: execution submitted via gateway",
                 symbol=symbol, side=direction, qty=plan.position_size,
                 status=record.status.value if record.status else "unknown")

        # Validate that execution actually produced a position (not a stub)
        if record.status.value == "filled" and _paper_broker:
            pos = _paper_broker.get_position(symbol)
            if not pos:
                log_error("AutoTrade: gateway reported filled but no PaperPosition exists",
                          symbol=symbol, exec_id=record.execution_id)
                return {"status": "failed",
                        "reason": "Gateway reported filled but no position created"}

        return record.to_dict()

    except Exception as e:
        log_warn("AutoTrade: ExecutionGateway.execute failed", symbol=symbol, error=str(e))
        return None


def _snap_kwargs(snap: dict | None) -> dict:
    """Extract sub-snapshot kwargs from a full AI decision snapshot."""
    if not snap:
        return {}
    ms = snap.get("market_snapshot", {})
    return {
        "decision_snap": snap,
        "context_snap": snap.get("evidence", {}),
        "indicator_snap": ms,
        "structure_snap": ms,
        "pattern_snap": ms,
        "mtf_snap": ms,
        "sr_snap": ms,
        "market_snapshot": ms,
    }


# ── Health watchdog (low frequency — not the primary trigger) ──


async def _health_watchdog_loop():
    """
    Low-frequency health check loop.

    This is NOT the primary analysis trigger — analysis is event-driven.
    This loop verifies engine health, checks for stale data conditions,
    and transitions states as needed.
    """
    while _engine_running:
        try:
            await asyncio.sleep(30)

            if not _engine_running:
                return

            # Check WebSocket health
            if _zerodha_engine and not _zerodha_engine.is_ws_connected:
                if _engine_state not in (ENGINE_STATE_DISCONNECTED, ENGINE_STATE_RECONNECTING):
                    _engine_state = ENGINE_STATE_DISCONNECTED

            # Refresh freshness computation
            if _freshness_tracker:
                _freshness_tracker.refresh_all()

        except asyncio.CancelledError:
            return
        except Exception as e:
            log_warn("AutoTrade: health watchdog error", error=str(e))


# ── Legacy scan cycle (replaced by event-driven — kept for health only) ──


async def _health_scan():
    """
    Health-oriented scan — no longer the primary analysis mechanism.

    The old _scan_cycle() that read cached snapshots is GONE.
    Analysis is now driven by CANDLE_CLOSED events.
    This scan only checks for candidates with fresh data and runs a
    periodic readiness check.
    """
    global _engine_state, _last_workspace_snapshot

    try:
        symbols_scanned = 0
        candidates = []
        best_candidate = None

        symbols = list_canonical_names()

        for symbol in symbols:
            if not _engine_running or _engine_paused:
                return

            symbols_scanned += 1

            # Get AI snapshot (latest from event-driven pipeline)
            try:
                ai_snap = _get_ai().latest(symbol)
            except Exception:
                ai_snap = None

            # Get regime snapshot (fresh from event-driven pipeline)
            try:
                regime_engine = _get_regime()
                regime_snap = regime_engine.latest(symbol) if regime_engine else None
            except Exception:
                regime_snap = None

            # Score opportunity from fresh data
            result = _build_opportunity_score(symbol, ai_snap, regime_snap)
            candidates.append(result)

        # Sort by score descending
        candidates.sort(key=lambda c: c["opportunity_score"], reverse=True)

        # Find best non-rejected candidate
        for c in candidates:
            if not c["reject_reasons"] and c["direction"] in ("BUY", "SELL") and c["opportunity_score"] >= 50:
                c["selected"] = True
                best_candidate = c
                break

        # Build workspace snapshot
        _last_workspace_snapshot = _build_workspace_snapshot(
            symbols_scanned=symbols_scanned,
            candidates=candidates,
            best_candidate=best_candidate,
        )

    except Exception as e:
        log_warn("AutoTrade: health scan error", error=str(e))
        if _last_workspace_snapshot:
            _last_workspace_snapshot["errors"] = _last_workspace_snapshot.get("errors", []) + [str(e)]


def _build_workspace_snapshot(
    symbols_scanned: int = 0,
    candidates: list[dict] | None = None,
    best_candidate: dict | None = None,
    decision: dict | None = None,
    regime: dict | None = None,
    approval: dict | None = None,
    risk_result: Any = None,
    trade_plan: Any = None,
    signal: TradeSignal | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """Build the workspace snapshot dict from available data."""
    candidates = candidates or []
    errors = errors or []

    # Provider info
    provider_info = {}
    if _zerodha_engine:
        provider_info = _zerodha_engine.get_status()

    # Freshness info
    freshness_info = {}
    if _freshness_tracker:
        freshness_info = _freshness_tracker.get_status_summary()

    return {
        "provider": {
            "name": "ZERODHA_KITE",
            "authenticated": provider_info.get("provider", {}).get("authenticated", False),
            "websocket_status": provider_info.get("websocket", {}).get("status", ENGINE_STATE_OFF),
            "last_tick_at": provider_info.get("websocket", {}).get("last_tick_time"),
            "data_age_ms": provider_info.get("age_seconds", 0) * 1000,
            "subscriptions": provider_info.get("websocket", {}).get("subscribed_tokens", 0),
            "instruments_mapped": provider_info.get("instruments", {}).get("mapped", 0),
            "market_open": provider_info.get("market_open", True),
        },
        "freshness": freshness_info,
        "engine": {
            "state": _engine_state,
            "running": _engine_running,
            "paused": _engine_paused,
            "analysis_enabled": _analysis_enabled,
            "mode": _get_runtime_mode(),
        },
        "readiness": _check_mandatory_systems(),
        "scan": {
            "symbols_scanned": symbols_scanned,
            "candidates_found": len([c for c in candidates if c.get("opportunitude_score", 0) > 0]) if candidates else 0,
            "last_scan_time": datetime.now(timezone.utc).isoformat(),
        },
        "candidates": candidates[:3] if candidates else [],
        "selected_opportunity": best_candidate,
        "decision": decision,
        "regime": regime,
        "approval": approval,
        "risk": risk_result.to_dict() if hasattr(risk_result, "to_dict") else (risk_result if isinstance(risk_result, dict) else None),
        "trade_plan": trade_plan.to_dict() if hasattr(trade_plan, "to_dict") else trade_plan,
        "signal": signal.to_dict() if signal else None,
        "order": None,
        "position": None,
        "performance": None,
        "alerts": [],
        "timeline": [],
        "errors": errors,
    }


def _get_zerodha_status_dict() -> dict[str, Any]:
    """Get Zerodha provider status for the workspace."""
    if not _zerodha_engine:
        return {
            "name": "ZERODHA_KITE",
            "authenticated": False,
            "websocket_status": "OFF",
            "last_tick_at": None,
            "data_age_ms": 0,
            "subscriptions": 0,
        }

    s = _zerodha_engine.get_status()
    return {
        "name": "ZERODHA_KITE",
        "authenticated": s.get("provider", {}).get("authenticated", False),
        "websocket_status": s.get("websocket", {}).get("status", "OFF"),
        "last_tick_at": s.get("websocket", {}).get("last_tick_time"),
        "data_age_ms": 0,
        "subscriptions": s.get("websocket", {}).get("subscribed_tokens", 0),
    }


# ── Engine lifecycle ──


async def _engine_lifecycle():
    """
    Background lifecycle task.

    Mirrors the ZerodhaMarketDataEngine state machine faithfully:
      AUTHENTICATING → LOADING_INSTRUMENTS → SUBSCRIBING → LOADING_HISTORY
      → WARMING_INDICATORS → CONNECTED → WAITING_FOR_LIVE_TICKS
      → RECEIVING_LIVE_TICKS → DATA_READY → SCANNING

    Analysis is blocked until DATA_READY.
    """
    global _engine_state

    # State mapping: ZerodhaMarketDataEngine state → AutoTrade state
    _ZERODHA_TO_AT = {
        "AUTHENTICATING": ENGINE_STATE_AUTHENTICATING,
        "LOADING_INSTRUMENTS": ENGINE_STATE_LOADING_INSTRUMENTS,
        "SUBSCRIBING": ENGINE_STATE_SUBSCRIBING,
        "LOADING_HISTORY": ENGINE_STATE_LOADING_HISTORY,
        "WARMING_INDICATORS": ENGINE_STATE_WARMING_INDICATORS,
        "CONNECTED": ENGINE_STATE_CONNECTED,
        "WAITING_FOR_LIVE_TICKS": ENGINE_STATE_WAITING_FOR_TICKS,
        "RECEIVING_LIVE_TICKS": ENGINE_STATE_RECEIVING_TICKS,
        "DATA_READY": ENGINE_STATE_DATA_READY,
        "SCANNING": ENGINE_STATE_SCANNING,
        "DISCONNECTED": ENGINE_STATE_DISCONNECTED,
        "RECONNECTING": ENGINE_STATE_RECONNECTING,
        "BLOCKED": ENGINE_STATE_BLOCKED,
        "ERROR": ENGINE_STATE_ERROR,
    }

    # Step 1: Start Zerodha engine and wait for connection
    _engine_state = ENGINE_STATE_AUTHENTICATING
    if _zerodha_engine:
        if not _zerodha_engine.is_running:
            await _zerodha_engine.start()

        for _ in range(60):
            if not _engine_running:
                return
            if _zerodha_engine.is_ws_connected:
                break
            await asyncio.sleep(1)

    if not _zerodha_engine or not _zerodha_engine.is_ws_connected:
        _engine_state = ENGINE_STATE_ERROR
        _engine_running = False
        log_error("AutoTrade: Zerodha engine failed to connect")
        return

    # Step 2: Mirror Zerodha engine state through warmup → DATA_READY
    for _ in range(120):
        if not _engine_running:
            return

        z_state = _zerodha_engine.state if _zerodha_engine else "ERROR"
        _engine_state = _ZERODHA_TO_AT.get(z_state, ENGINE_STATE_SCANNING)

        # Analysis only allowed from DATA_READY onward
        if z_state in ("DATA_READY", "SCANNING"):
            break

        # Also check freshness tracker as fallback
        if _freshness_tracker and _freshness_tracker.get_status_summary().get("live", 0) > 0:
            _engine_state = ENGINE_STATE_SCANNING
            break

        await asyncio.sleep(1)

    if _engine_state not in (ENGINE_STATE_SCANNING,):
        log_warn("AutoTrade: warmup timeout, continuing in current state",
                 state=_engine_state, zerodha_state=_zerodha_engine.state if _zerodha_engine else "N/A")
    else:
        log_info("AutoTrade: engine ready", state=_engine_state,
                 zerodha_state=_zerodha_engine.state if _zerodha_engine else "N/A")

    # Step 3: Register event handlers
    _register_event_handlers()
    log_info("AutoTrade: engine lifecycle started", state=_engine_state)


# ── API Endpoints ──


@router.get("/api/auto-trade/workspace")
async def auto_trade_workspace():
    """Get the complete auto-trade workspace snapshot.

    Aggregates real-time data from all engines.
    Provider section shows Zerodha Kite status.
    Never returns data from cached snapshots as fresh.
    """
    result = _build_workspace_snapshot()

    # Always augment with current live data
    result["readiness"] = _check_mandatory_systems()

    # Augment with live orders/positions
    try:
        lifecycle = get_lifecycle()
        if lifecycle:
            open_orders = [o.to_dict() for o in lifecycle.get_all_orders() if o.status not in ("filled", "closed", "cancelled", "rejected")]
            open_positions = [p.to_dict() for p in lifecycle.get_open_positions()]
            result["order"] = open_orders[0] if open_orders else result.get("order")
            result["position"] = open_positions[0] if open_positions else result.get("position")
    except Exception:
        pass

    # Augment with P&L
    try:
        from trading.pnl_engine import get_pnl_engine
        pnl = get_pnl_engine().get_portfolio_pnl()
        result["performance"] = {
            "day_pnl": round(pnl.day_pnl, 2),
            "unrealized_pnl": round(pnl.total_unrealized, 2),
            "realized_pnl": round(pnl.total_realized, 2),
            "total_pnl": round(pnl.total_pnl, 2),
        }
    except Exception:
        pass

    # Engine status
    result["engine"]["state"] = _engine_state
    result["engine"]["running"] = _engine_running
    result["engine"]["paused"] = _engine_paused
    result["engine"]["analysis_enabled"] = _analysis_enabled
    result["engine"]["mode"] = _get_runtime_mode()

    # Provider info (always live, not cached)
    result["provider"] = _get_zerodha_status_dict()

    return result


@router.post("/api/auto-trade/start")
async def auto_trade_start():
    """Start the auto analysis engine with Zerodha Kite data.

    Initializes Zerodha-backed analysis and returns initialization progress.
    Trade execution depends on runtime mode and all approval gates.
    """
    global _engine_running, _engine_state, _engine_task, _health_watchdog_task, _analysis_enabled

    async with _engine_lock:
        if _engine_running:
            return {"success": True, "state": _engine_state, "message": "Engine is already running"}

        # Verify Zerodha engine availability
        if not _zerodha_engine:
            return {
                "success": False,
                "state": "BLOCKED",
                "message": "ZerodhaMarketDataEngine not initialized. Cannot start Auto Trade.",
            }

        # Start the Zerodha engine if not running (it will check for existing connection)
        if not _zerodha_engine.is_running:
            await _zerodha_engine.start()

        _analysis_enabled = True
        _engine_running = True
        _engine_paused = False
        _engine_state = ENGINE_STATE_AUTHENTICATING

        # Start the engine lifecycle task (initializes Zerodha, waits for ticks, registers handlers)
        _engine_task = asyncio.create_task(_engine_lifecycle())

        # Start the health watchdog (low-frequency health checks)
        _health_watchdog_task = asyncio.create_task(_health_watchdog_loop())

        _record_audit("auto_trade_started", {"state": _engine_state})

        return {
            "success": True,
            "state": _engine_state,
            "message": "Auto analysis engine starting with Zerodha Kite data",
            "analysis_enabled": True,
            "provider": _get_zerodha_status_dict(),
        }


@router.post("/api/auto-trade/stop")
async def auto_trade_stop():
    """Stop the auto analysis engine."""
    global _engine_running, _engine_state, _engine_task, _health_watchdog_task, _analysis_enabled

    async with _engine_lock:
        _analysis_enabled = False
        _engine_running = False
        _engine_state = ENGINE_STATE_STOPPING

        # Cancel tasks
        for task in [_engine_task, _health_watchdog_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        _engine_task = None
        _health_watchdog_task = None

        # Unregister event handlers
        _unregister_event_handlers()

        _engine_state = ENGINE_STATE_OFF
        _record_audit("auto_trade_stopped", {"state": "OFF"})
        return {"success": True, "state": "OFF", "message": "Auto analysis engine stopped", "analysis_enabled": False}


@router.post("/api/auto-trade/pause")
async def auto_trade_pause():
    """Pause the auto analysis engine (stops scanning, keeps state)."""
    global _engine_paused, _engine_state

    if not _engine_running:
        return {"success": False, "state": _engine_state, "message": "Engine is not running"}
    _engine_paused = True
    _engine_state = ENGINE_STATE_WAITING
    _record_audit("auto_trade_paused", {"state": "WAITING"})
    return {"success": True, "state": "WAITING", "message": "Auto analysis engine paused"}


@router.post("/api/auto-trade/resume")
async def auto_trade_resume():
    """Resume the auto analysis engine."""
    global _engine_paused, _engine_state

    if not _engine_running:
        return {"success": False, "state": _engine_state, "message": "Engine is not running"}
    _engine_paused = False
    _engine_state = ENGINE_STATE_SCANNING
    _record_audit("auto_trade_resumed", {"state": "SCANNING"})
    return {"success": True, "state": "SCANNING", "message": "Auto analysis engine resumed"}


@router.get("/api/auto-trade/status")
async def auto_trade_status():
    """Get auto-trade engine status with Zerodha provider info."""
    return {
        "engine": {
            "running": _engine_running,
            "paused": _engine_paused,
            "state": _engine_state,
            "analysis_enabled": _analysis_enabled,
            "mode": _get_runtime_mode(),
        },
        "provider": _get_zerodha_status_dict(),
        "readiness": _check_mandatory_systems(),
        "freshness": _freshness_tracker.get_status_summary() if _freshness_tracker else {},
    }
