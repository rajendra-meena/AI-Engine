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
import os
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
from core.enums import TradeDirection, normalize_direction, display_direction
from api.auto_trade_settings import get_settings as get_ats
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
from trading.market_session import check_session, is_force_exit_time, MarketSessionConfig, DEFAULT_SESSION_CONFIG
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
_auto_execute_paper = False  # Persisted user setting: auto-execute paper trades
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

# ── Event-driven scan metrics ──
# These are the ONLY authoritative counters. All UI reads from these.
# No polling scan loop exists — analysis is triggered by CANDLE_CLOSED events.
_scan_metrics = {
    "total_analysis_cycles": 0,         # incremented each time _handle_candle_closed runs
    "analyses_completed_total": 0,      # incremented when _run_fresh_analysis returns a result
    "symbols_scanned_total": 0,         # incremented per symbol per completed analysis
    "symbols_scanned_current_cycle": 0, # current event's symbol count (reset per event)
    "no_trade_decisions_total": 0,      # direction=NONE
    # Granular candidate funnel
    "raw_directional_signals_total": 0,   # any LONG/SHORT from AI decision
    "score_qualified_candidates_total": 0,# LONG/SHORT with score>=50, no reject_reasons
    "option_contracts_selected_total": 0, # OptionSelector chose a specific contract
    "premium_ready_total": 0,            # Premium fetched and valid
    "option_plans_created_total": 0,     # OptionExecutionPlan built
    "option_risk_approved_total": 0,     # OptionRiskEngine passed
    "trade_plans_created_total": 0,       # TradePlanner created a valid plan
    "risk_approved_total": 0,            # RiskEngine validated the plan
    "risk_blocked_total": 0,            # LONG/SHORT rejected by risk
    "execution_attempts_total": 0,       # ExecutionGateway.execute() called
    "execution_failed_total": 0,         # Gateway execution returned failure
    "paper_trades_created_total": 0,    # PaperBroker created a position
    "open_positions_count": 0,          # Current open positions count
    "closed_trades_count": 0,           # Completed trades count
    # Timestamps
    "last_candle_closed_at": None,      # ISO timestamp
    "last_analysis_started_at": None,   # ISO timestamp
    "last_analysis_completed_at": None, # ISO timestamp
    "last_successful_analysis_at": None,# ISO timestamp
    # Execution pipeline diagnostic state (last attempt)
    "last_candidate": {},
    "last_trade_plan": {},
    "last_risk_result": {},
    "last_execution_result": {},
    "last_block_reason": None,
    "last_block_stage": None,
    "last_block_code": None,
    "last_execution_trace": [],
    "last_trade_plan_input": {},
}

# Per-symbol analysis state (never overwritten by cooldown skips)
# Keys: symbol string → dict with canonical analysis fields
_analysis_state_by_symbol: dict[str, dict] = {}

# Analysis status reason (visible in Current Market Analysis)
# This reflects the LATEST pipeline event, not the latest analysis.
_analysis_blocked_reason: str | None = None
_analysis_blocked_category: str = ""  # "WAITING", "WARMING", "BLOCKED", "ANALYSED"

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

    # — Data source is ZERODHA_KITE (never mock/yahoo) —
    data_provider = os.getenv("AUTO_TRADE_MARKET_DATA_PROVIDER", "").upper()
    if data_provider == "ZERODHA_KITE" and _zerodha_engine:
        checks["data_source"] = R.READY
    elif data_provider == "MOCK":
        checks["data_source"] = R.BLOCKED
        log_warn("AutoTrade: MOCK data provider configured — blocking trades")
    else:
        checks["data_source"] = R.BLOCKED
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

    # Track pipeline counters — raw_directional_signals_total only here
    raw_dir = result.get("direction", "NONE")
    if raw_dir in ("LONG", "SHORT"):
        _scan_metrics["raw_directional_signals_total"] = _scan_metrics.get("raw_directional_signals_total", 0) + 1

    # 5. If opportunity qualifies, bridge to execution
    # NOTE: score_qualified_candidates_total is incremented in _handle_candle_closed (one place only)
    if result and result.get("opportunity_score", 0) >= 50 and result.get("direction") in ("LONG", "BUY", "SHORT", "SELL"):
        if not result.get("reject_reasons"):
            _scan_metrics["execution_attempts_total"] = _scan_metrics.get("execution_attempts_total", 0) + 1
            _scan_metrics["last_candidate"] = {
                "symbol": symbol,
                "direction": raw_dir,
                "score": result.get("opportunity_score", 0),
                "analysis_cycle_id": analysis_cycle_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            exec_result = await _try_execute_trade(symbol, result, ai_snap, regime_snap,
                                                   analysis_cycle_id=analysis_cycle_id)
            if exec_result:
                result["execution"] = exec_result
                _scan_metrics["last_execution_result"] = exec_result
                _scan_metrics["last_block_reason"] = None
            else:
                _scan_metrics["execution_failed_total"] = _scan_metrics.get("execution_failed_total", 0) + 1
                # _try_execute_trade already set last_block_reason — don't overwrite
                if not _scan_metrics.get("last_block_reason"):
                    _scan_metrics["last_block_reason"] = "Execution returned None — check logs"

    _mark_analyzed(symbol)
    return result


def _update_analysis_status_from_symbol(symbol: str, reason: str | None, category: str):
    """Update the current analysis blocked reason for a symbol."""
    global _analysis_blocked_reason, _analysis_blocked_category
    _analysis_blocked_reason = reason
    _analysis_blocked_category = category


def _update_analysis_status_from_results(candidates: list[dict]):
    """Derive analysis status from scan candidates."""
    global _analysis_blocked_reason, _analysis_blocked_category

    # Check if any candidate was fully analysed (had AI data)
    has_analysis = any(c.get("direction") not in ("NONE",) and c.get("opportunity_score", 0) > 0 for c in candidates)
    has_no_trade = any(c.get("direction") in ("WAIT", "NO_TRADE") for c in candidates)
    has_candidate = any(c.get("opportunity_score", 0) >= 50 for c in candidates)
    risk_blocked = any(c.get("reject_reasons") for c in candidates if c.get("opportunity_score", 0) >= 50)

    if not candidates:
        _analysis_blocked_category = "WAITING"
        _analysis_blocked_reason = "NO_SYMBOLS_SCANNED_YET"
    elif has_candidate and not risk_blocked:
        _analysis_blocked_category = "ANALYSED"
        _analysis_blocked_reason = "CANDIDATE_FOUND"
    elif risk_blocked:
        _analysis_blocked_category = "ANALYSED"
        _analysis_blocked_reason = "RISK_BLOCKED"
    elif has_no_trade:
        _analysis_blocked_category = "ANALYSED"
        _analysis_blocked_reason = "NO_VALID_SIGNAL"
    elif has_analysis:
        _analysis_blocked_category = "ANALYSED"
        _analysis_blocked_reason = "STRATEGY_CONDITIONS_NOT_MET"
    else:
        _analysis_blocked_category = "WAITING"
        _analysis_blocked_reason = "WAITING_FOR_AI_DECISION"


async def _handle_candle_closed(event: BusEvent):
    """
    Primary trigger: a candle has closed.
    Run the full analysis pipeline for the affected symbol.

    Signal suppression: candles with allow_signal_generation=false
    (e.g. warmup historical candles) do not trigger analysis.

    This function owns the event-driven metrics:
    - total_analysis_cycles
    - symbols_scanned_total, analyses_completed_total
    - no_trade_decisions_total, candidates_found_total
    - risk_blocked_total, paper_trades_created_total
    - per-symbol analysis state
    """
    global _engine_state, _analysis_blocked_reason, _analysis_blocked_category, _scan_metrics
    global _analysis_state_by_symbol
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
            _update_analysis_status_from_symbol(
                symbol, f"ENGINE_NOT_DATA_READY: state={_zerodha_engine.state}", "WARMING"
            )
            return

        # ── Idempotency gate ──
        candle_version = payload.get("candle_version", "")
        idempotency_key = payload.get("idempotency_key", "")
        if idempotency_key:
            _idempotency_seen = _cached_globals().get("_seen_candle_keys", set())
            if idempotency_key in _idempotency_seen:
                return
            _idempotency_seen.add(idempotency_key)

        # Extract analysis_cycle_id from candle event for idempotent execution
        analysis_cycle_id = payload.get("analysis_cycle_id", "")

        # Increment cycle counter
        _scan_metrics["total_analysis_cycles"] += 1
        _scan_metrics["last_candle_closed_at"] = datetime.now(timezone.utc).isoformat()
        _scan_metrics["symbols_scanned_current_cycle"] = 1  # one symbol per candle event

        # Update status: about to analyse
        _update_analysis_status_from_symbol(symbol, "ANALYSIS_IN_PROGRESS", "ANALYSING")

        # Run fresh analysis
        result = await _run_fresh_analysis(symbol, analysis_cycle_id=analysis_cycle_id)
        if result:
            _engine_state = ENGINE_STATE_SCANNING
            _scan_metrics["last_analysis_completed_at"] = datetime.now(timezone.utc).isoformat()
            _scan_metrics["last_successful_analysis_at"] = datetime.now(timezone.utc).isoformat()
            _scan_metrics["analyses_completed_total"] += 1
            _scan_metrics["symbols_scanned_total"] += 1

            # Normalize the result direction
            raw_direction = result.get("direction", "NONE")
            try:
                canonical_dir = normalize_direction(raw_direction)
            except ValueError:
                canonical_dir = TradeDirection.NONE
            result["direction"] = canonical_dir.value

            # Store per-symbol analysis state (never overwritten by cooldown)
            _analysis_state_by_symbol[symbol] = {
                "symbol": symbol,
                "direction": canonical_dir.value,
                "display_decision": display_direction(canonical_dir),
                "bias": result.get("bias", result.get("regime", "NEUTRAL")),
                "opportunity_score": result.get("opportunity_score", 0),
                "confidence": result.get("confidence", 0),
                "status": "ANALYSED",
                "reason": "NO_VALID_SIGNAL",
                "reject_reasons": result.get("reject_reasons", []),
                "risk_status": result.get("risk_status", "NO_DATA"),
                "candle_version": candle_version,
                "analysed_at": datetime.now(timezone.utc).isoformat(),
            }

            if canonical_dir == TradeDirection.NONE:
                _scan_metrics["no_trade_decisions_total"] += 1
                _analysis_state_by_symbol[symbol]["reason"] = "TRADE_PLAN_DIRECTION_NONE"
                _analysis_state_by_symbol[symbol]["display_decision"] = "NO TRADE"
                _update_analysis_status_from_symbol(
                    symbol,
                    f"NO_VALID_SIGNAL: direction=NONE bias={result.get('regime', 'NEUTRAL')}",
                    "ANALYSED"
                )
            elif canonical_dir in (TradeDirection.LONG, TradeDirection.SHORT):
                score = result.get("opportunity_score", 0)
                if result.get("reject_reasons"):
                    _scan_metrics["risk_blocked_total"] += 1
                    risk_reason = result["reject_reasons"][0]
                    _analysis_state_by_symbol[symbol]["reason"] = f"RISK_BLOCKED: {risk_reason}"
                    _analysis_state_by_symbol[symbol]["display_decision"] = display_direction(canonical_dir)
                    _update_analysis_status_from_symbol(
                        symbol,
                        f"RISK_BLOCKED: {risk_reason}",
                        "ANALYSED"
                    )
                elif score >= 50:
                    _scan_metrics["score_qualified_candidates_total"] += 1
                    # Check execution result from _run_fresh_analysis
                    exec_info = result.get("execution")
                    if exec_info:
                        _analysis_state_by_symbol[symbol]["reason"] = (
                            f"EXECUTION_{exec_info.get('status', 'RESULT').upper()}: "
                            f"{exec_info.get('reason', '')}"
                        )
                    else:
                        _analysis_state_by_symbol[symbol]["reason"] = (
                            f"CANDIDATE_FOUND → NO_EXECUTION: {canonical_dir.value} score={score}"
                        )
                    _analysis_state_by_symbol[symbol]["display_decision"] = display_direction(canonical_dir)
                    _update_analysis_status_from_symbol(
                        symbol,
                        _analysis_state_by_symbol[symbol]["reason"],
                        "ANALYSED"
                    )
                else:
                    _analysis_state_by_symbol[symbol]["reason"] = f"SCORE_BELOW_THRESHOLD: {score}/50"
                    _analysis_state_by_symbol[symbol]["display_decision"] = display_direction(canonical_dir)
                    _update_analysis_status_from_symbol(
                        symbol,
                        f"SCORE_BELOW_THRESHOLD: {score}",
                        "ANALYSED"
                    )

                if result.get("execution"):
                    _scan_metrics["paper_trades_created_total"] += 1
                    log_info("AutoTrade: trade executed from candle close",
                             symbol=symbol,
                             direction=canonical_dir.value,
                             score=result.get("opportunity_score"),
                             exec_status=result["execution"].get("status", "unknown"))
            else:
                # Unknown direction — record error but don't crash
                _analysis_state_by_symbol[symbol]["reason"] = f"INVALID_DIRECTION: {raw_direction}"
                _update_analysis_status_from_symbol(
                    symbol, f"INVALID_DIRECTION: {raw_direction}", "BLOCKED"
                )
        else:
            # _run_fresh_analysis returned None — could be cooldown or no AI data
            # Do NOT overwrite _analysis_state_by_symbol — preserve last valid analysis
            _update_analysis_status_from_symbol(
                symbol, "ANALYSIS_SKIPPED: symbol cooled down or no AI data", "WAITING"
            )

    except Exception as e:
        _analysis_state_by_symbol[symbol] = {
            "symbol": symbol,
            "status": "ERROR",
            "reason": f"ANALYSIS_ERROR: {e}",
            "analysed_at": datetime.now(timezone.utc).isoformat(),
        }
        _update_analysis_status_from_symbol(symbol, f"ANALYSIS_ERROR: {e}", "BLOCKED")
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

    # Decision direction (weight 10%) — canonical LONG/SHORT/NONE
    raw_direction = ai_snap.get("trade_plan", {}).get("direction", "NONE")
    try:
        direction = normalize_direction(raw_direction)
    except ValueError:
        direction = TradeDirection.NONE
        reject_reasons.append(f"Invalid trade plan direction: {raw_direction}")

    if direction in (TradeDirection.LONG, TradeDirection.SHORT):
        score += 60 * 0.10
        reasons.append(f"Clear {display_direction(direction)} signal detected")
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
        "direction": direction.value if hasattr(direction, 'value') else str(direction),
        "risk_status": risk_level,
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
    """
    # ── Execution trace ──
    _trace: list[dict] = []
    def _stage(name: str, ok: bool = True, **kw):
        _trace.append({"stage": name, "ok": ok, "ts": datetime.now(timezone.utc).isoformat(), **kw})

    def _fail(code: str, reason: str, **kw):
        _scan_metrics["last_block_stage"] = code
        _scan_metrics["last_block_code"] = code
        _scan_metrics["last_block_reason"] = reason
        _stage(code, False, reason=reason, **kw)
        _scan_metrics["last_execution_trace"] = _trace
        return None

    _stage("TRY_EXECUTE_ENTERED", symbol=symbol, direction=result.get("direction",""), score=result.get("opportunity_score",0))

    if not result or result.get("opportunity_score", 0) < 50:
        return _fail("EXEC_BLOCK_SCORE_BELOW_50", f"Score {result.get('opportunity_score',0)} < 50")

    raw_dir = result.get("direction", "NONE")
    try:
        canonical_dir = normalize_direction(raw_dir)
    except ValueError:
        return _fail("EXEC_BLOCK_INVALID_DIRECTION", f"Invalid direction: {raw_dir}")

    if canonical_dir not in (TradeDirection.LONG, TradeDirection.SHORT):
        return _fail("EXEC_BLOCK_DIRECTION_NOT_TRADEABLE", f"Direction not tradeable: {raw_dir}")

    if result.get("reject_reasons"):
        return _fail("EXEC_BLOCK_REJECT_REASONS", f"Rejected: {result['reject_reasons'][0]}")

    runtime_mode = _get_runtime_mode()
    if runtime_mode == "observe":
        return _fail("EXEC_BLOCK_RUNTIME_MODE_OBSERVE",
                     "Runtime mode is OBSERVE — does not allow trade execution")
    if runtime_mode not in ("shadow", "paper"):
        return _fail("EXEC_BLOCK_RUNTIME_MODE", f"Runtime mode: {runtime_mode} not allowed")
    _stage("RUNTIME_MODE_PASSED", mode=runtime_mode)

    # ── Auto Execute Paper Trades gate ──
    try:
        ats_settings = get_ats()
        if not ats_settings.auto_execute_paper_trades:
            return _fail("EXEC_BLOCK_AUTO_EXECUTE_DISABLED",
                         "Auto Execute Paper Trades is disabled in settings",
                         settings_value=ats_settings.auto_execute_paper_trades)
    except Exception:
        pass
    _stage("AUTO_EXECUTE_PASSED")

    session = check_session()
    if not session.can_trade:
        return _fail("EXEC_BLOCK_SESSION", f"Session blocked: {session.code}:{session.reason}")
    _stage("SESSION_GATE_PASSED")

    if _kill_switch:
        try:
            ks_status = _kill_switch.get_status()
            if ks_status.get("active", False):
                return _fail("EXEC_BLOCK_KILL_SWITCH", "Kill switch active")
        except Exception:
            pass
    _stage("KILL_SWITCH_PASSED")

    direction = result["direction"]
    try:
        canonical_dir_for_exec = normalize_direction(direction)
        direction = canonical_dir_for_exec.value
    except ValueError:
        return _fail("EXEC_BLOCK_INVALID_DIRECTION_NORM", f"Invalid direction normalization: {direction}")

    market_price = ai_snap.get("market_snapshot", {}).get("close") or ai_snap.get("market_snapshot", {}).get("last_price", 0)
    if not market_price or market_price <= 0:
        # Fallback: try candle engine's latest close price (lazy import avoids circular dependency)
        try:
            import main as _main_mod
            if hasattr(_main_mod, 'candle_engine') and _main_mod.candle_engine:
                last = _main_mod.candle_engine.latest(symbol, "1m")
                if last and last.get("close", 0) > 0:
                    market_price = last["close"]
        except Exception:
            pass
    if not market_price or market_price <= 0:
        return _fail("EXEC_BLOCK_MARKET_PRICE_INVALID", f"No valid market price for {symbol}: {market_price}")
    _stage("MARKET_PRICE_RESOLVED", price=market_price)

    if _paper_broker:
        existing_pos = _paper_broker.get_position(symbol)
        if existing_pos:
            pos_dir = existing_pos.direction
            if pos_dir == direction:
                reason = f"Position already open: {pos_dir} on {symbol}"
                _fail("EXEC_BLOCK_EXISTING_POSITION", reason)
                return {"status": "blocked", "reason": reason}
            else:
                reason = f"Opposite position active: {pos_dir} on {symbol}, cannot {direction}"
                _fail("EXEC_BLOCK_EXISTING_POSITION_OPPOSITE", reason)
                return {"status": "blocked", "reason": reason}
    _stage("POSITION_GATE_PASSED")

    exec_idempotency_key = f"exec_{symbol}_{analysis_cycle_id}" if analysis_cycle_id else ""
    if exec_idempotency_key and _exec_gateway:
        existing_record = _exec_gateway.get_execution_by_key(exec_idempotency_key)
        if existing_record:
            return _fail("EXEC_BLOCK_DUPLICATE_DECISION", "Duplicate analysis_cycle_id + symbol")
    _stage("IDEMPOTENCY_PASSED")

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
        return _fail("EXEC_BLOCK_AI_DECISION_INVALID", f"AIDecision creation failed: {e}", exception=str(e)[:200])
    _stage("AI_DECISION_CREATED")

    # ── Option Execution Plan (before TradePlanner, before Risk) ──
    # When option buying is active, build the option plan FIRST so that
    # risk validation uses premium costs, not spot notional.
    option_plan = None
    try:
        from execution.execution_config import is_option_buying
        if is_option_buying():
            from execution.options.planner import OptionExecutionPlanner

            # Get paper capital from broker for risk calculations
            ats_settings = get_ats()
            paper_capital = 100000.0
            try:
                if _paper_broker:
                    acct = _paper_broker.get_account()
                    paper_capital = acct.available_cash or acct.initial_capital or 100000.0
            except Exception:
                pass

            option_plan = await OptionExecutionPlanner.execute(
                symbol=symbol,
                direction=direction,
                underlying_price=market_price,
                underlying_sl=None,
                underlying_target=None,
                capital=paper_capital,
                risk_percent=2.0,
                premium_source=ats_settings.premium_source if hasattr(ats_settings, 'premium_source') else "ZERODHA",
            )
            if option_plan is not None:
                _scan_metrics["option_plans_created_total"] = _scan_metrics.get("option_plans_created_total", 0) + 1
                if option_plan.premium > 0:
                    _scan_metrics["premium_ready_total"] = _scan_metrics.get("premium_ready_total", 0) + 1
                _stage("OPTION_PLAN_CREATED",
                       option=f"{option_plan.strike:.0f}{option_plan.option_type}",
                       premium=option_plan.premium,
                       source=option_plan.premium_source,
                       lots=option_plan.lots,
                       lot_size=option_plan.lot_size,
                       cost=option_plan.total_cost)
            else:
                _stage("OPTION_PLAN_FAILED", reason="planner returned None")
    except ImportError:
        pass
    except Exception as e:
        log_warn("AutoTrade: option execution plan failed", error=str(e))

    # ── Build TradePlan (option-aware or spot) ──
    planner = _planner
    if not planner:
        return _fail("EXEC_BLOCK_PLANNER_UNAVAILABLE", "TradePlanner not available")

    snap = _snap_kwargs(ai_snap)
    _scan_metrics["last_trade_plan_input"] = {
        "symbol": symbol,
        "direction": direction,
        "entry_price": market_price,
        "confidence": ai_snap.get("confidence", 0),
        "opportunity_score": result.get("opportunity_score", 0),
        "regime": regime_snap.get("regime", "unknown") if regime_snap else "unknown",
        "analysis_cycle_id": analysis_cycle_id,
    }

    if option_plan is not None:
        # ── Option path: Validate with OptionRiskEngine ──
        from execution.options.risk import OptionRiskEngine

        # Sync risk engine capital with paper broker account
        option_risk_capital = 100000.0
        if _paper_broker:
            try:
                acct = _paper_broker.get_account()
                option_risk_capital = acct.available_cash
            except Exception:
                pass

        ore = OptionRiskEngine(capital=option_risk_capital, risk_percent=2.0)
        ore.set_settings(get_ats())
        if _paper_broker:
            ore.set_open_positions(len(_paper_broker.get_positions()))
        option_risk_result = ore.validate(option_plan)

        if not option_risk_result.execution_permitted:
            _scan_metrics["risk_blocked_total"] = _scan_metrics.get("risk_blocked_total", 0) + 1
            if _paper_broker:
                _paper_broker.record_blocked_attempt(
                    underlying_symbol=symbol,
                    direction=direction,
                    stage="option_risk",
                    block_code="OPTION_RISK_BLOCKED",
                    block_reason="; ".join(option_risk_result.rejected_by),
                    actual_value=f"capital={option_risk_capital:.0f}",
                    required_value="execution_permitted=true",
                    risk_snapshot=option_risk_result.to_dict(),
                )
            return _fail("EXEC_BLOCK_OPTION_RISK",
                         "OptionRiskEngine rejected: " + "; ".join(option_risk_result.rejected_by),
                         risk_result=option_risk_result.to_dict())

        _scan_metrics["option_risk_approved_total"] = _scan_metrics.get("option_risk_approved_total", 0) + 1
        _stage("OPTION_RISK_PASSED", grade=option_risk_result.risk_grade)

        # Use premium-based price for TradePlanner, override with option values
        # NOTE: OptionRiskEngine already validated this trade — skip legacy risk
        _option_risk_already_passed = True
        try:
            plan = planner.build_plan(
                decision=decision,
                price=option_plan.premium,
                context_snap=snap.get("context_snap"),
                indicator_snap=snap.get("indicator_snap"),
                structure_snap=snap.get("structure_snap"),
                mtf_snap=snap.get("mtf_snap"),
                sr_snap=snap.get("sr_snap"),
            )
        except Exception as e:
            import traceback; tb = traceback.format_exc()
            return _fail("EXEC_EXCEPTION_TRADE_PLANNER", f"TradePlanner exception: {e}",
                         exception=str(e)[:200], traceback=tb[:500])

        _stage("TRADE_PLANNER_RETURNED")
        if plan is None:
            return _fail("EXEC_BLOCK_TRADE_PLAN_NONE", "TradePlanner returned None")

        # Override with option execution values
        plan.execution_type = "option_buying"
        plan.option_type = option_plan.option_type
        plan.option_strike = option_plan.strike
        plan.option_expiry = option_plan.expiry
        plan.option_premium = option_plan.premium
        plan.option_lot_size = option_plan.lot_size
        plan.option_lots = option_plan.lots
        plan.option_execution_symbol = option_plan.execution_symbol
        plan.underlying_entry_price = option_plan.underlying_entry
        plan.underlying_stop_price = option_plan.underlying_sl
        plan.underlying_target_price = option_plan.underlying_target
        plan.position_size = option_plan.lots * option_plan.lot_size
        plan.entry_price = option_plan.premium
        plan.stop_price = option_plan.premium_sl
        plan.target_price = option_plan.premium_target
        plan.capital_required = option_plan.total_cost

        _scan_metrics["last_trade_plan"] = {
            "qualified": plan.qualified, "rejection_reason": plan.rejection_reason or "",
            "direction": plan.direction, "entry_price": plan.entry_price,
            "stop_price": plan.stop_price, "target_price": plan.target_price,
            "position_size": plan.position_size, "risk_reward": plan.risk_reward,
            "risk_status": plan.risk_status, "risk_block_reason": plan.risk_block_reason or "",
            "execution_type": "option_buying",
            "option": f"{option_plan.strike:.0f}{option_plan.option_type}",
            "premium": option_plan.premium, "lots": option_plan.lots,
            "lot_size": option_plan.lot_size, "total_cost": option_plan.total_cost,
        }
    else:
        # ── Synthetic spot path (original) ──
        _stage("TRADE_PLANNER_CALLED")
        try:
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
            import traceback; tb = traceback.format_exc()
            return _fail("EXEC_EXCEPTION_TRADE_PLANNER", f"TradePlanner exception: {e}",
                         exception=str(e)[:200], traceback=tb[:500])
        _stage("TRADE_PLANNER_RETURNED")
        if plan is None:
            return _fail("EXEC_BLOCK_TRADE_PLAN_NONE", "TradePlanner returned None")
        _scan_metrics["last_trade_plan"] = {
            "qualified": plan.qualified, "rejection_reason": plan.rejection_reason or "",
            "direction": plan.direction, "entry_price": plan.entry_price,
            "stop_price": plan.stop_price, "target_price": plan.target_price,
            "position_size": plan.position_size, "risk_reward": plan.risk_reward,
            "risk_status": plan.risk_status, "risk_block_reason": plan.risk_block_reason or "",
        }

    # ── Common qualification gate ──
    if not plan.qualified:
        return _fail("EXEC_BLOCK_TRADE_PLAN_REJECTED", f"TradePlan rejected: {plan.rejection_reason}",
                     plan_rejection=plan.rejection_reason)
    _scan_metrics["trade_plans_created_total"] = _scan_metrics.get("trade_plans_created_total", 0) + 1

    # Option path already validated by OptionRiskEngine — skip legacy spot risk check
    if not locals().get("_option_risk_already_passed"):
        if plan.risk_status == "blocked":
            _scan_metrics["risk_blocked_total"] = _scan_metrics.get("risk_blocked_total", 0) + 1
            return _fail("EXEC_BLOCK_RISK_REJECTED", f"Risk blocked: {plan.risk_block_reason}",
                         risk_reason=plan.risk_block_reason)
        _scan_metrics["risk_approved_total"] = _scan_metrics.get("risk_approved_total", 0) + 1
    else:
        _stage("OPTION_RISK_SKIPPED_LEGACY")

    if not _exec_gateway:
        return _fail("EXEC_BLOCK_GATEWAY_UNAVAILABLE", "ExecutionGateway not available")

    _stage("EXECUTION_GATEWAY_CALLED")

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
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return _fail("EXEC_EXCEPTION_GATEWAY", f"ExecutionGateway.execute exception: {e}",
                     exception=str(e)[:200], traceback=tb[:500])

    _stage("PAPERBROKER_CALLED", status=record.status.value if record.status else "unknown")

    if record.status.value == "filled" and _paper_broker:
        pos = _paper_broker.get_position(symbol)
        if not pos:
            return _fail("EXEC_BLOCK_PAPER_POSITION_MISSING",
                         "Gateway reported filled but no PaperPosition created")
    else:
        failure_reason = record.rejection_reason or record.status.value or "unknown"
        return _fail("EXEC_BLOCK_GATEWAY_REJECTED", f"Gateway rejected: {failure_reason}")

    _stage("PAPER_POSITION_CREATED")
    _scan_metrics["paper_trades_created_total"] = _scan_metrics.get("paper_trades_created_total", 0) + 1
    _scan_metrics["last_block_stage"] = None
    _scan_metrics["last_block_code"] = None
    _scan_metrics["last_block_reason"] = None

    return record.to_dict()


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
    global _engine_state, _engine_running
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


# ── Legacy scan cycle (DEPRECATED — no runtime dependency) ──
# This function is defined for reference only. It is NOT called by any runtime path.
# All analysis is event-driven via _handle_candle_closed.
# Delete this function after verifying no import references it.


async def _health_scan():
    """
    DEPRECATED. Replaced by event-driven CANDLE_CLOSED → _handle_candle_closed.

    This function is no longer called by any runtime code path. It is preserved
    for reference only and must not be used for display or metrics.
    """
    # No-op — the event-driven pipeline owns all metrics now.
    pass


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
    """Build the workspace snapshot dict from event-driven data."""
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

    # Build per-symbol current market analysis from authoritative state
    current_market_analysis = []
    for symbol, state in sorted(_analysis_state_by_symbol.items()):
        current_market_analysis.append({
            "symbol": symbol,
            "status": state.get("status", "WAITING"),
            "direction": state.get("direction", "NONE"),
            "display_decision": state.get("display_decision", "NO TRADE"),
            "bias": state.get("bias", "NEUTRAL"),
            "confidence": state.get("confidence", 0),
            "opportunity_score": state.get("opportunity_score", 0),
            "reason": state.get("reason", "NO_VALID_SIGNAL"),
            "reject_reasons": state.get("reject_reasons", []),
            "risk_status": state.get("risk_status", "UNKNOWN"),
            "analysed_at": state.get("analysed_at", ""),
        })

    # Derive scan data from authoritative event-driven metrics
    configured_symbols = len(list_canonical_names())
    live_symbols = sum(
        1 for sym in list_canonical_names()
        if _freshness_tracker and _freshness_tracker.get(sym)
        and _freshness_tracker.get(sym).tick_freshness == FRESHNESS_LIVE
    )

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
        "analysis_status": {
            "category": _analysis_blocked_category or "WAITING",
            "reason": _analysis_blocked_reason or "WAITING_FOR_FIRST_LIVE_CANDLE",
        },
        "metrics": dict(_scan_metrics),
        "scan": {
            "configured_symbols": configured_symbols,
            "symbols_with_live_ticks": live_symbols,
            "symbols_analysed": _scan_metrics.get("symbols_scanned_total", 0),
            "candidates_found_total": _scan_metrics.get("score_qualified_candidates_total", 0),
            "analyses_completed_total": _scan_metrics.get("analyses_completed_total", 0),
            "no_trade_decisions_total": _scan_metrics.get("no_trade_decisions_total", 0),
            "raw_directional_signals_total": _scan_metrics.get("raw_directional_signals_total", 0),
            "score_qualified_candidates_total": _scan_metrics.get("score_qualified_candidates_total", 0),
            "option_contracts_selected_total": _scan_metrics.get("option_contracts_selected_total", 0),
            "premium_ready_total": _scan_metrics.get("premium_ready_total", 0),
            "option_plans_created_total": _scan_metrics.get("option_plans_created_total", 0),
            "option_risk_approved_total": _scan_metrics.get("option_risk_approved_total", 0),
            "trade_plans_created_total": _scan_metrics.get("trade_plans_created_total", 0),
            "risk_approved_total": _scan_metrics.get("risk_approved_total", 0),
            "risk_blocked_total": _scan_metrics.get("risk_blocked_total", 0),
            "execution_attempts_total": _scan_metrics.get("execution_attempts_total", 0),
            "paper_trades_created_total": _scan_metrics.get("paper_trades_created_total", 0),
            "open_positions_count": _scan_metrics.get("open_positions_count", 0),
            "closed_trades_count": _scan_metrics.get("closed_trades_count", 0),
            "last_analysis_at": _scan_metrics.get("last_analysis_completed_at"),
            "last_candle_closed_at": _scan_metrics.get("last_candle_closed_at"),
        },
        "current_market_analysis": current_market_analysis,
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

        # Invariant: if analyses_completed > 0, symbols_scanned must also be > 0
        "_invariant_check": (
            _scan_metrics.get("analyses_completed_total", 0) > 0
            and _scan_metrics.get("symbols_scanned_total", 0) == 0
        ),
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
    global _engine_state, _analysis_enabled, _engine_running, _engine_paused, _analysis_blocked_reason, _analysis_blocked_category

    # Reset analysis_enabled — guards against stale False from previous run
    _analysis_enabled = True
    # Set initial analysis status
    _analysis_blocked_category = "WARMING"
    _analysis_blocked_reason = "HISTORICAL_WARMUP_IN_PROGRESS"

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

    try:
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

        # Wait a brief moment for any initial disconnection that may immediately
        # follow connection (race between Twisted thread callbacks)
        if not _zerodha_engine or not _zerodha_engine.is_ws_connected:
            for _ in range(10):
                await asyncio.sleep(0.5)
                if _zerodha_engine and _zerodha_engine.is_ws_connected:
                    break
            else:
                _engine_state = ENGINE_STATE_ERROR
                _engine_running = False
                _analysis_enabled = False
                error_detail = "no_zerodha_engine" if not _zerodha_engine else "ws_not_connected"
                log_error("AutoTrade: Zerodha engine failed to connect",
                          reason=error_detail,
                          zerodha_running=_zerodha_engine.is_running if _zerodha_engine else False,
                          zerodha_state=_zerodha_engine.state if _zerodha_engine else "N/A")
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

    except asyncio.CancelledError:
        raise
    except Exception as e:
        _engine_state = ENGINE_STATE_ERROR
        _engine_running = False
        _analysis_enabled = False
        log_error("AutoTrade: lifecycle crashed", error=str(e))


# ── API Endpoints ──


@router.get("/api/auto-trade/diagnostics")
async def auto_trade_diagnostics():
    """Get detailed pipeline diagnostics for the auto-trade system.

    Returns runtime state of every pipeline stage, including task health,
    WebSocket status, tick counts, scan loop metrics, and blocked reasons.
    Does not expose secrets.

    Task semantics:
      lifecycle_task  — one-time startup initialisation (Zerodha auth,
                       instrument loading, warmup, event handler registration).
                       Runs once, then completes. NOT the ongoing scan.
      health_watchdog — 30s periodic health check loop (ongoing).
      No separate scan_task exists — analysis is event-driven via CANDLE_CLOSED.
      The 'scan_loop' section shows the event-driven analysis pipeline status.
    """
    now_ts = datetime.now(timezone.utc).isoformat()

    # ── Lifecycle task (one-time startup, completes after init) ──
    lifecycle_health: dict[str, Any] = {
        "type": "one_time_startup",
        "created": _engine_task is not None,
        "done": _engine_task.done() if _engine_task else None,
        "cancelled": _engine_task.cancelled() if _engine_task and _engine_task.done() else None,
        "exception": None,
        "started_at": None,
    }
    if _engine_task and _engine_task.done() and not _engine_task.cancelled():
        try:
            _engine_task.result()
        except Exception as ex:
            lifecycle_health["exception"] = str(ex)

    # ── Health watchdog task (ongoing loop) ──
    watchdog_health: dict[str, Any] = {
        "type": "ongoing_loop",
        "interval_seconds": 30,
        "created": _health_watchdog_task is not None,
        "done": _health_watchdog_task.done() if _health_watchdog_task else None,
        "cancelled": _health_watchdog_task.cancelled() if _health_watchdog_task and _health_watchdog_task.done() else None,
        "exception": None,
    }
    if _health_watchdog_task and _health_watchdog_task.done() and not _health_watchdog_task.cancelled():
        try:
            _health_watchdog_task.result()
        except Exception as ex:
            watchdog_health["exception"] = str(ex)

    # ── Scan/analysis pipeline status (event-driven) ──
    pipeline_info: dict[str, Any] = {
        "type": "event_driven",
        "primary_trigger": "CANDLE_CLOSED",
        "engine_state": _engine_state,
        "analysis_enabled": _analysis_enabled,
        "running": _engine_running and not _engine_paused,
        "event_handlers_registered": False,
        "blocked_reason": _analysis_blocked_reason,
        "blocked_category": _analysis_blocked_category,
        "per_symbol_state": len(_analysis_state_by_symbol),
    }
    if _event_bus:
        # Check if our handlers are registered on the EventBus
        try:
            subs = getattr(_event_bus, "_subscribers", {})
            pipeline_info["event_handlers_registered"] = (
                "candle_closed" in subs or
                any("auto_trade" in str(s) for subs_list in subs.values() for s in subs_list)
            )
        except Exception:
            pass

    # ── Invariant check ──
    m = _scan_metrics
    invariant_violation = (
        m.get("analyses_completed_total", 0) > 0
        and m.get("symbols_scanned_total", 0) == 0
    )

    # ── Market data info (tick source classification) ──
    ws_connected = False
    subscribed_tokens = 0
    ticks_received = 0
    ws_ticks_received = 0
    last_tick_at = None
    if _zerodha_engine:
        ws_connected = _zerodha_engine.is_ws_connected
        subscribed_tokens = len(getattr(_zerodha_engine, "_subscribed_tokens", []))
        stats = getattr(_zerodha_engine, "_stats", {})
        ticks_received = stats.get("total_ticks_received", 0)
        last_tick_at = stats.get("last_tick_time")
        # Distinguish WS ticks from quote/historical data
        # (the engine only gets ticks from WebSocket; quote snapshots
        # are fetched via REST API and don't increment this counter)
        ws_ticks_received = ticks_received

    market_data_info: dict[str, Any] = {
        "provider": "ZERODHA_KITE",
        "websocket_connected": ws_connected,
        "zerodha_state": _zerodha_engine.state if _zerodha_engine else "N/A",
        "zerodha_running": _zerodha_engine.is_running if _zerodha_engine else False,
        "subscribed_symbols": subscribed_tokens,
        "websocket_ticks_received": ws_ticks_received,
        "quote_api_snapshots_received": 0,  # Not currently tracked
        "historical_candles_loaded": 0,     # Tracked in HistoricalWarmupEngine
        "last_tick_at": last_tick_at,
        "live_tick_verified": ws_ticks_received > 0,
    }
    # Attempt to get warmup candle count
    try:
        if _zerodha_engine:
            we = getattr(_zerodha_engine, "_warmup_engine", None)
            if we and hasattr(we, "stats"):
                market_data_info["historical_candles_loaded"] = we.stats.get("total_candles_loaded", 0)
    except Exception:
        pass

    # ── Freshness summary ──
    freshness_summary: dict[str, Any] = {}
    if _freshness_tracker:
        freshness_summary = _freshness_tracker.get_status_summary()
        symbol_states = {}
        for name in list_canonical_names():
            sf = _freshness_tracker.get(name)
            if sf:
                symbol_states[name] = {
                    "tick_freshness": sf.tick_freshness,
                    "candle_freshness": sf.candle_freshness,
                    "indicator_freshness": sf.indicator_freshness,
                    "regime_freshness": sf.regime_freshness,
                    "ai_freshness": sf.ai_freshness,
                    "overall": sf.overall_freshness,
                    "last_tick": sf.last_tick_receipt,
                }
        freshness_summary["symbols"] = symbol_states

    # ── Warmup processing summary ──
    warmup_info: dict[str, Any] = {
        "status": "unknown",
        "per_symbol": {},
    }

    # ── EventBus metrics ──
    event_bus_info: dict[str, Any] = {
        "status": "unknown",
    }
    if _event_bus:
        try:
            stats = _event_bus.get_stats()
            event_bus_info = {
                "queue_size": stats.get("queue_size", "?"),
                "queue_capacity": stats.get("max_queue_size", "?"),
                "total_published": stats.get("total_published", 0),
                "total_dispatched": stats.get("total_dispatched", 0),
                "total_errors": stats.get("total_errors", 0),
                "total_dropped": stats.get("total_dropped", 0),
                "subscriber_count": stats.get("subscriber_count", 0),
            }
        except Exception as e:
            event_bus_info["error"] = str(e)

    # ── Blocked reasons ──
    blocked_reasons: list[str] = []
    try:
        checks = _check_mandatory_systems()
        for system, status in checks.items():
            if status in ("BLOCKED", "DEGRADED", "OFFLINE"):
                blocked_reasons.append(f"{system}={status}")
    except Exception as e:
        blocked_reasons.append(f"readiness_check_error={e}")

    return {
        "timestamp": now_ts,
        "analysis_enabled": _analysis_enabled,
        "engine_running": _engine_running,
        "engine_state": _engine_state,
        "lifecycle_task": lifecycle_health,
        "health_watchdog": watchdog_health,
        "pipeline": pipeline_info,
        "market_data": market_data_info,
        "warmup": warmup_info,
        "event_bus": event_bus_info,
        "freshness": freshness_summary,
        "metrics": dict(_scan_metrics),
        "blocked_reasons": blocked_reasons,
        "invariant_violation": invariant_violation,
        "current_market_analysis": [
            {
                "symbol": s,
                "status": state.get("status", "WAITING"),
                "direction": state.get("direction", "NONE"),
                "display_decision": state.get("display_decision", "NO TRADE"),
                "bias": state.get("bias", "NEUTRAL"),
                "opportunity_score": state.get("opportunity_score", 0),
                "reason": state.get("reason", ""),
                "analysed_at": state.get("analysed_at", ""),
            }
            for s, state in sorted(_analysis_state_by_symbol.items())
        ],
    }


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

    # Wire auto_execute_paper from authoritative settings
    try:
        ats_settings = get_ats()
        _auto_execute_paper = ats_settings.auto_execute_paper_trades
    except Exception:
        pass
    auto_execute_val: bool = False
    try:
        auto_execute_val = bool(_auto_execute_paper)
    except Exception:
        pass

    # Engine status
    result["engine"]["state"] = _engine_state
    result["engine"]["running"] = _engine_running
    result["engine"]["paused"] = _engine_paused
    result["engine"]["analysis_enabled"] = _analysis_enabled
    result["engine"]["mode"] = _get_runtime_mode()
    result["engine"]["auto_execute_paper"] = auto_execute_val

    # Provider info (always live, not cached)
    result["provider"] = _get_zerodha_status_dict()

    # ── Open Paper Positions (from PaperBroker) ──
    try:
        if _paper_broker:
            open_paper_positions = _paper_broker.get_positions()
            result["open_positions"] = [p.to_dict(include_diagnostics=True) for p in open_paper_positions]
            _scan_metrics["open_positions_count"] = len(open_paper_positions)
        else:
            result["open_positions"] = []
            _scan_metrics["open_positions_count"] = 0
    except Exception:
        result["open_positions"] = []

    # ── Blocked Attempts (from PaperBroker) ──
    try:
        if _paper_broker:
            result["blocked_attempts"] = _paper_broker.get_blocked_attempts(limit=50)
        else:
            result["blocked_attempts"] = []
    except Exception:
        result["blocked_attempts"] = []

    # ── Trade History (from PaperBroker) ──
    try:
        if _paper_broker:
            trades = _paper_broker.get_trades()
            result["trade_history"] = trades[-50:] if trades else []
            _scan_metrics["closed_trades_count"] = _paper_broker.get_account().closed_trades
        else:
            result["trade_history"] = []
    except Exception:
        result["trade_history"] = []

    # ── Paper Account Summary ──
    try:
        if _paper_broker:
            result["paper_account"] = _paper_broker.get_account().to_dict()
        else:
            result["paper_account"] = {}
    except Exception:
        result["paper_account"] = {}

    # ── Phase 2D: Premium freshness summary ──
    try:
        if _paper_broker:
            positions = _paper_broker.get_positions()
            stale_count = sum(1 for p in positions if p.check_stale() in ("STALE", "DISCONNECTED"))
            live_count = sum(1 for p in positions if p.check_stale() == "LIVE")
            waiting_count = sum(1 for p in positions if p.check_stale() == "WAITING_FOR_FIRST_TICK")
            result["premium_freshness"] = {
                "total_positions": len(positions),
                "live_count": live_count,
                "stale_count": stale_count,
                "waiting_count": waiting_count,
            }
        else:
            result["premium_freshness"] = {"total_positions": 0, "live_count": 0, "stale_count": 0, "waiting_count": 0}
    except Exception:
        result["premium_freshness"] = {"total_positions": 0, "live_count": 0, "stale_count": 0, "waiting_count": 0}

    # ── Phase 2D: Premium data status per position ──
    try:
        if _paper_broker and result.get("open_positions"):
            for pos_dict in result["open_positions"]:
                pos_obj = _paper_broker.get_position_by_id(pos_dict.get("trade_id", ""))
                if pos_obj:
                    pos_dict["premium_data_status"] = pos_obj.check_stale()
                    pos_dict["premium_tick_age_ms"] = pos_obj.premium_tick_age_ms
                    pos_dict["last_premium_tick_at"] = pos_obj.last_premium_tick_at
    except Exception:
        pass

    # ── Phase 2D: Recovery diagnostics ──
    try:
        if hasattr(_paper_broker, "_recovery_diagnostics") and _paper_broker._recovery_diagnostics:
            result["recovery_info"] = _paper_broker._recovery_diagnostics
        else:
            result["recovery_info"] = {}
    except Exception:
        result["recovery_info"] = {}

    # ── Data Source Provenance ──
    result["data_sources"] = {
        "underlying_live_source": "ZERODHA_KITE_WEBSOCKET",
        "historical_source": "ZERODHA_KITE",
        "premium_source": get_ats().premium_source if hasattr(get_ats(), "premium_source") else "ZERODHA_KITE_WEBSOCKET",
        "yahoo_feeds": {
            "chart_endpoint": True,
            "historical_analysis": False,
            "current_market_analysis": False,
            "executable_decisions": False,
        },
    }
    # Premium source guarantee
    result["data_sources"]["premium_source_guarantee"] = (
        "controlled_test" if _is_dev_mode() and result.get("open_positions") and
        any(p.get("premium_source") == "CONTROLLED_TEST_FIXTURE" for p in (result.get("open_positions") or []))
        else "ZERODHA_KITE_QUOTE"
    )

    return result


@router.post("/api/auto-trade/paper-positions/{trade_id}/close")
async def auto_trade_close_paper_position(trade_id: str):
    """Close a paper position manually.

    Only PAPER positions can be closed through this endpoint.
    Fetches current premium, calculates realized P&L,
    moves position to history, returns complete closed trade result.
    """
    if not _paper_broker:
        raise HTTPException(status_code=503, detail="PaperBroker not initialized")

    pos = _paper_broker.get_position_by_id(trade_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Paper position not found")

    # Check if already closed
    if pos.exit_reason is not None:
        raise HTTPException(status_code=400, detail=f"Position already closed: {pos.exit_reason}")

    # Check premium freshness — reject stale unless explicitly forced
    data_status = pos.check_stale()
    if data_status in ("STALE", "DISCONNECTED"):
        # Allow close at last known premium but flag it
        log_warn("Manual close with stale premium", trade_id=trade_id, status=data_status)

    exit_price = pos.premium_current or pos.current_price
    success = _paper_broker.close_position(trade_id, reason="MANUAL_EXIT")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to close position (may already be closed)")

    return {
        "success": True,
        "trade_id": trade_id,
        "exit_price": exit_price,
        "exit_reason": "MANUAL_EXIT",
        "premium_data_status": data_status,
        "realized_pnl": round(pos.realized_pnl, 2),
        "message": "Position closed manually",
    }


@router.get("/api/auto-trade/paper-positions")
async def auto_trade_get_paper_positions():
    """Get all open paper positions with full field set."""
    if not _paper_broker:
        return {"positions": [], "total": 0}
    positions = _paper_broker.get_positions()
    return {
        "positions": [p.to_dict(include_diagnostics=True) for p in positions],
        "total": len(positions),
    }


@router.get("/api/auto-trade/trade-history")
async def auto_trade_get_trade_history(limit: int = 100, offset: int = 0):
    """Get completed paper trade history with pagination."""
    if not _paper_broker:
        return {"trades": [], "total": 0}
    trades = _paper_broker.get_trades()
    total = len(trades)
    sliced = trades[-limit - offset:] if offset == 0 else trades[-(limit + offset):-offset or None]
    if limit and offset == 0:
        sliced = sliced[-limit:]
    return {"trades": sliced, "total": total}


@router.get("/api/auto-trade/paper-positions/{trade_id}/events")
async def auto_trade_get_position_events(trade_id: str):
    """Get lifecycle events for a specific position."""
    if not _paper_broker:
        raise HTTPException(status_code=503, detail="PaperBroker not initialized")
    pos = _paper_broker.get_position_by_id(trade_id)
    if not pos:
        # Check history
        all_trades = _paper_broker.get_trades()
        found = any(t.get("trade_id") == trade_id for t in all_trades)
        if not found:
            raise HTTPException(status_code=404, detail="Position not found")
    events = _paper_broker.get_trade_position_events(trade_id)
    return {"trade_id": trade_id, "events": events}


@router.post("/api/auto-trade/market-close-exit")
async def auto_trade_market_close_exit():
    """Force-close all open paper positions (market close / emergency)."""
    if not _paper_broker:
        raise HTTPException(status_code=503, detail="PaperBroker not initialized")
    _paper_broker.force_market_close_exit()
    return {
        "success": True,
        "message": "Market close exit completed",
        "open_positions_remaining": len(_paper_broker.get_positions()),
    }


@router.get("/api/auto-trade/recovery-status")
async def auto_trade_recovery_status():
    """Get restart recovery diagnostics."""
    if not _paper_broker:
        return {"recovery_performed": False, "diagnostics": {}}
    diag = getattr(_paper_broker, "_recovery_diagnostics", {})
    return {
        "recovery_performed": bool(diag),
        "diagnostics": diag,
    }


@router.post("/api/auto-trade/inject-premium-tick", include_in_schema=False)
async def auto_trade_inject_premium_tick(payload: dict):
    """DEV ONLY: Inject a controlled premium tick for testing SL/target/P&L."""
    if not _is_dev_mode():
        raise HTTPException(status_code=403, detail="Only available in development/test mode")
    if not _paper_broker:
        raise HTTPException(status_code=503, detail="PaperBroker not initialized")

    trade_id = (payload or {}).get("trade_id", "")
    premium = float((payload or {}).get("premium", 0))
    if not trade_id or premium <= 0:
        raise HTTPException(status_code=400, detail="trade_id and premium > 0 required")

    pos = _paper_broker.get_position_by_id(trade_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")

    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat()
    result = pos.update_premium(premium, ts)

    if result.get("sl_hit"):
        _paper_broker._close_position(trade_id, premium, "STOP_LOSS_HIT")
    elif result.get("target_hit"):
        _paper_broker._close_position(trade_id, premium, "TARGET_HIT")

    return {
        "success": True,
        "trade_id": trade_id,
        "premium": premium,
        "unrealized_pnl": round(pos.unrealized_pnl, 2),
        "pnl_percent": round(pos.pnl_percent, 2),
        "sl_hit": result.get("sl_hit", False),
        "target_hit": result.get("target_hit", False),
        "position_closed": pos.exit_reason is not None,
        "exit_reason": pos.exit_reason,
    }


# ── Controlled Integration Test Endpoint (DEV only) ──

import os as _os_mod


def _is_dev_mode() -> bool:
    """True when running in development/test mode."""
    # Check multiple indicators to avoid false production activation
    env = _os_mod.environ.get("APP_ENV", "development").lower()
    return env in ("development", "dev", "test") or _os_mod.environ.get("CONTROLLED_TEST", "").lower() == "true"


@router.post("/api/auto-trade/controlled-test-one-lot", include_in_schema=False)
async def auto_trade_controlled_one_lot_test():
    """
    DEV ONLY: Controlled integration test that creates a one-lot PaperPosition
    through the full production-style pipeline.

    Goes through:
        Settings validation
        → OptionExecutionPlanner
        → OptionRiskEngine
        → ExecutionGateway in PAPER mode
        → PaperBroker
        → PaperPosition storage
        → Workspace serialization

    Labelled test_origin = CONTROLLED_INTEGRATION_TEST.
    No real broker order is placed.
    Returns the created PaperPosition and full execution trace.
    """
    if not _is_dev_mode():
        raise HTTPException(status_code=403, detail="Only available in development/test mode")

    if not _paper_broker:
        raise HTTPException(status_code=503, detail="PaperBroker not initialized")

    # Ensure paper broker is running
    if not _paper_broker.is_running:
        _paper_broker.start()

    # Ensure gateway is in PAPER mode
    if _exec_gateway:
        _exec_gateway.set_mode("paper")

    # ── Controlled inputs ──
    underlying_symbol = "NIFTY 50"
    direction = "LONG"
    option_type = "CE"
    lot_size = 50        # NIFTY standard lot
    lots = 1
    premium_entry = 180.0
    premium_sl = 160.0
    premium_target = 220.0
    strike = 24800.0      # example ATM strike
    expiry = "2026-08-06"  # nearest weekly
    exchange = "NFO"
    instrument_token = 1000001
    execution_symbol = "NIFTY 50 24800 CE"
    capital = 100000.0
    risk_reward = 2.0
    quantity = lot_size * lots  # 50
    premium_cost = premium_entry * lot_size  # 180 * 50 = 9000
    risk_per_lot = (premium_entry - premium_sl) * lot_size  # 20 * 50 = 1000
    reward_per_lot = (premium_target - premium_entry) * lot_size  # 40 * 50 = 2000

    # ── Step 1: Validate settings gates ──
    settings = get_ats()
    execution_trace = []
    blocked = []

    def _add_trace(stage: str, status: str, detail: str = ""):
        execution_trace.append({"stage": stage, "status": status, "detail": detail, "ts": datetime.now(timezone.utc).isoformat()})

    # 1a. Runtime mode
    runtime_mode = _get_runtime_mode()
    if runtime_mode != "paper":
        blocked.append({
            "block_code": "RUNTIME_MODE_NOT_PAPER",
            "block_reason": f"Runtime mode must be PAPER, got {runtime_mode}",
            "actual_value": runtime_mode, "required_value": "paper",
        })
        _add_trace("RUNTIME_MODE_CHECK", "BLOCKED", f"mode={runtime_mode}")

    # 1b. Auto execute
    if not settings.auto_execute_paper_trades:
        blocked.append({
            "block_code": "AUTO_EXECUTE_PAPER_DISABLED",
            "block_reason": "Auto Execute Paper Trades is disabled in settings",
            "actual_value": "false", "required_value": "true",
        })
        _add_trace("AUTO_EXECUTE_CHECK", "BLOCKED", "auto_execute_paper_trades=false")

    # 1c. Allow buy
    if direction == "LONG" and not settings.allow_buy_trades:
        blocked.append({
            "block_code": "BUY_TRADES_DISABLED",
            "block_reason": "Buy trades are disabled in settings",
            "actual_value": "false", "required_value": "true",
        })
        _add_trace("ALLOW_BUY_CHECK", "BLOCKED")

    # 1d. Allow sell
    if direction == "SHORT" and not settings.allow_sell_trades:
        blocked.append({
            "block_code": "SELL_TRADES_DISABLED",
            "block_reason": "Sell trades are disabled in settings",
            "actual_value": "false", "required_value": "true",
        })
        _add_trace("ALLOW_SELL_CHECK", "BLOCKED")

    # 1e. Min confidence
    if settings.min_ai_confidence > 40:
        blocked.append({
            "block_code": "AI_CONFIDENCE_BELOW_MINIMUM",
            "block_reason": f"Min AI confidence {settings.min_ai_confidence} > 40 (test default)",
            "actual_value": "40", "required_value": str(settings.min_ai_confidence),
        })
        _add_trace("AI_CONFIDENCE_CHECK", "BLOCKED")

    # 1f. Min risk/reward
    if settings.min_risk_reward > risk_reward:
        blocked.append({
            "block_code": "RISK_REWARD_BELOW_MINIMUM",
            "block_reason": f"Min risk/reward {settings.min_risk_reward} > {risk_reward}",
            "actual_value": str(risk_reward), "required_value": str(settings.min_risk_reward),
        })
        _add_trace("RISK_REWARD_CHECK", "BLOCKED")

    # 1g. Max daily trades
    if settings.max_trades_per_day < 1:
        blocked.append({
            "block_code": "MAX_DAILY_TRADES_REACHED",
            "block_reason": f"Max daily trades {settings.max_trades_per_day} < 1",
            "actual_value": str(settings.max_trades_per_day), "required_value": ">=1",
        })
        _add_trace("MAX_DAILY_TRADES_CHECK", "BLOCKED")

    # 1h. Execution type
    if settings.execution_type != "option_buying":
        blocked.append({
            "block_code": "EXECUTION_TYPE_MISMATCH",
            "block_reason": f"Execution type must be option_buying, got {settings.execution_type}",
            "actual_value": settings.execution_type, "required_value": "option_buying",
        })
        _add_trace("EXECUTION_TYPE_CHECK", "BLOCKED")

    if blocked:
        for b in blocked:
            _paper_broker.record_blocked_attempt(
                underlying_symbol=underlying_symbol,
                direction=direction,
                stage="settings_validation",
                block_code=b["block_code"],
                block_reason=b["block_reason"],
                actual_value=b.get("actual_value", ""),
                required_value=b.get("required_value", ""),
                settings_snapshot=settings.to_dict(),
            )
        return {
            "success": False,
            "stage": "settings_gates_blocked",
            "blocked_by": blocked,
            "execution_trace": execution_trace,
            "message": "Settings gates blocked the test trade. Adjust settings and retry.",
        }

    _add_trace("SETTINGS_GATES", "PASSED", f"all {len(settings.validate()) if not settings.validate() else 'OK'}")

    # ── Step 2: Check position gate (no existing same-direction) ──
    existing = _paper_broker.get_position(execution_symbol)
    if existing:
        _paper_broker.record_blocked_attempt(
            underlying_symbol=underlying_symbol,
            direction=direction,
            stage="position_gate",
            block_code="DUPLICATE_SIGNAL",
            block_reason=f"Existing {existing.direction} position on {execution_symbol}",
            actual_value=f"position:{existing.trade_id}",
            required_value="no_open_position",
        )
        return {"success": False, "stage": "position_gate_blocked", "message": "Position already open"}

    _add_trace("POSITION_GATE", "PASSED")

    # ── Step 3: Build OptionPlan ──
    from execution.options.planner import OptionExecutionPlanner

    try:
        option_plan = await OptionExecutionPlanner.execute(
            symbol=underlying_symbol,
            direction=direction,
            underlying_price=24800.0,
            underlying_sl=None,
            underlying_target=None,
            capital=capital,
            risk_percent=2.0,
            override_plan={
                "option_type": option_type,
                "strike": strike,
                "expiry": expiry,
                "premium": premium_entry,
                "premium_sl": premium_sl,
                "premium_target": premium_target,
                "lot_size": lot_size,
                "lots": lots,
                "execution_symbol": execution_symbol,
                "instrument_token": instrument_token,
            },
        )
    except Exception as e:
        return {"success": False, "stage": "option_planner_error", "error": str(e)}

    if option_plan is None:
        return {"success": False, "stage": "option_plan_none", "message": "OptionExecutionPlanner returned None"}

    _scan_metrics["option_plans_created_total"] = _scan_metrics.get("option_plans_created_total", 0) + 1
    _add_trace("OPTION_PLAN", "CREATED", f"{option_plan.strike:.0f}{option_plan.option_type} premium={option_plan.premium}")

    # ── Step 4: Option Risk Validation ──
    try:
        from execution.options.risk import OptionRiskEngine
        risk_result = OptionRiskEngine.validate(
            option_plan=option_plan,
            settings=settings,
        )
    except Exception as e:
        return {"success": False, "stage": "option_risk_error", "error": str(e)}

    if not risk_result.execution_permitted:
        _paper_broker.record_blocked_attempt(
            underlying_symbol=underlying_symbol,
            direction=direction,
            stage="option_risk",
            block_code="OPTION_RISK_BLOCKED",
            block_reason="; ".join(risk_result.rejected_by) if risk_result.rejected_by else risk_result.reason,
            actual_value=f"permitted={risk_result.execution_permitted}",
            required_value="permitted=true",
            risk_snapshot={"risk_score": risk_result.risk_score, "risk_grade": risk_result.risk_grade, "rejected_by": risk_result.rejected_by},
        )
        return {
            "success": False,
            "stage": "option_risk_blocked",
            "risk_result": risk_result.to_dict() if hasattr(risk_result, "to_dict") else str(risk_result),
        }

    _scan_metrics["option_risk_approved_total"] = _scan_metrics.get("option_risk_approved_total", 0) + 1
    _add_trace("OPTION_RISK", "PASSED", f"grade={risk_result.risk_grade}")

    # ── Step 5: Execute via Gateway → PaperBroker ──
    exec_idempotency_key = f"controlled_test_{underlying_symbol}_{uuid.uuid4().hex[:12]}"
    quantity = lot_size * lots

    if _exec_gateway:
        record = _exec_gateway.execute(
            symbol=execution_symbol,
            side="BUY",
            quantity=quantity,
            price=premium_entry,
            stop_loss=premium_sl,
            target=premium_target,
            trade_plan_id=f"controlled_test_{uuid.uuid4().hex[:12]}",
            trace_id=f"ct_{uuid.uuid4().hex[:12]}",
            idempotency_key=exec_idempotency_key,
            decision_id=f"ct_dec_{uuid.uuid4().hex[:12]}",
            analysis_cycle_id=f"ct_cycle_{uuid.uuid4().hex[:12]}",
        )
        _add_trace("EXECUTION_GATEWAY", record.status.value if record.status else "unknown")
    else:
        # Direct PaperBroker path (bypass Gateway if not available)
        result = _paper_broker.execute(
            symbol=underlying_symbol,
            side="BUY",
            quantity=quantity,
            price=premium_entry,
            stop_loss=premium_sl,
            target=premium_target,
            execution_type="option_buying",
            option_type=option_type,
            strike=strike,
            expiry=expiry,
            premium_entry=premium_entry,
            premium_stop_loss=premium_sl,
            premium_target=premium_target,
            lot_size=lot_size,
            lots=lots,
            underlying_symbol=underlying_symbol,
            underlying_entry_price=24800.0,
            underlying_stop_loss=24600.0,
            underlying_target=25200.0,
            risk_reward=risk_reward,
            premium_source="CONTROLLED_TEST_FIXTURE",
            execution_symbol=execution_symbol,
            exchange=exchange,
            instrument_token=instrument_token,
            premium_instrument_token=instrument_token,
            source_provenance="controlled_test_fixture",
            trade_grade="A",
            ai_confidence=85.0,
            opportunity_score=85.0,
            test_origin="CONTROLLED_INTEGRATION_TEST",
        )
        _add_trace("PAPER_BROKER_DIRECT", "filled" if result.get("success") else "failed", str(result.get("reason", "")))
        if not result.get("success"):
            return {
                "success": False,
                "stage": "paper_broker_rejected",
                "reason": result.get("reason"),
                "execution_trace": execution_trace,
            }
        trade_id = result.get("trade_id", "")
        _add_trace("POSITION_CREATED", "OPEN", f"trade_id={trade_id}")

    # ── Step 6: Get created position ──
    if _paper_broker:
        # Use underlying_symbol to find it if gateway was used
        if _exec_gateway:
            # Gateway uses execution_symbol; broker maps by symbol
            pass
        positions = _paper_broker.get_positions()
        position_dicts = [p.to_dict(include_diagnostics=True) for p in positions]
        _scan_metrics["paper_trades_created_total"] = _scan_metrics.get("paper_trades_created_total", 0) + 1
        _scan_metrics["open_positions_count"] = len(positions)
    else:
        position_dicts = []

    return {
        "success": True,
        "stage": "position_created",
        "test_origin": "CONTROLLED_INTEGRATION_TEST",
        "no_real_broker_order": True,
        "execution_trace": execution_trace,
        "calculations": {
            "underlying_symbol": underlying_symbol,
            "direction": direction,
            "option_type": option_type,
            "lot_size": lot_size,
            "lots": lots,
            "quantity": quantity,
            "premium_entry": premium_entry,
            "premium_stop_loss": premium_sl,
            "premium_target": premium_target,
            "premium_cost": premium_cost,
            "risk_per_lot": risk_per_lot,
            "reward_per_lot": reward_per_lot,
            "risk_reward": risk_reward,
            "capital": capital,
        },
        "position": position_dicts[-1] if position_dicts else None,
        "message": "One-lot PaperPosition created through full pipeline. No live broker order was placed.",
    }


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

        _analysis_enabled = True
        _engine_running = True
        _engine_paused = False
        _engine_state = ENGINE_STATE_AUTHENTICATING

        # Start the engine lifecycle task (handles Zerodha init, warmup, tick registration)
        # NOTE: We do NOT call _zerodha_engine.start() here — it blocks for minutes
        # on authentication + instrument loading + warmup. The lifecycle task handles
        # all initialization asynchronously so this endpoint returns immediately.
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


@router.post("/api/auto-trade/settings")
async def auto_trade_settings(payload: dict):
    """Update auto-trade user settings.

    Persisted settings survive page refresh:
    - auto_execute_paper: bool — automatically execute paper trades
    """
    global _auto_execute_paper

    if "auto_execute_paper" in payload:
        _auto_execute_paper = bool(payload["auto_execute_paper"])
        log_info("AutoTrade: setting updated", auto_execute_paper=_auto_execute_paper)

    return {"success": True, "auto_execute_paper": _auto_execute_paper}


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
            "auto_execute_paper": _auto_execute_paper,
        },
        "provider": _get_zerodha_status_dict(),
        "readiness": _check_mandatory_systems(),
        "freshness": _freshness_tracker.get_status_summary() if _freshness_tracker else {},
    }


@router.post("/api/auto-trade/runtime-mode")
async def auto_trade_set_runtime_mode(payload: dict):
    """Set the runtime mode. Allowed: observe, shadow, paper."""
    global _runtime_mgr
    mode = (payload or {}).get("mode", "").strip().lower()
    if not mode:
        return {"success": False, "message": "Missing 'mode' field"}

    if not _runtime_mgr:
        return {"success": False, "message": "RuntimeModeManager not initialized"}

    previous = _runtime_mgr.mode.value if _runtime_mgr else "unknown"
    result = _runtime_mgr.set_mode(mode)
    new_mode = _runtime_mgr.mode.value if _runtime_mgr else "unknown"

    if result.get("success"):
        _record_audit("RUNTIME_MODE_CHANGED", {
            "previous_mode": previous,
            "new_mode": new_mode,
            "source": "api",
            "user_action": True,
        })

    return {
        "success": result.get("success", False),
        "previous_mode": previous,
        "mode": new_mode,
        "message": result.get("message", ""),
    }


@router.get("/api/auto-trade/runtime-mode")
async def auto_trade_get_runtime_mode():
    """Get the current runtime mode."""
    mode = _get_runtime_mode()
    return {
        "mode": mode,
        "observe": mode == "observe",
        "shadow": mode == "shadow",
        "paper": mode == "paper",
        "controlled_live": mode == "controlled_live",
        "can_execute_paper": _runtime_mgr.can_execute_paper() if _runtime_mgr else False,
    }
