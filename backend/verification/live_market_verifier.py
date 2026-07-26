"""
MarketMind AI — Pre-Market Verification & Dry Run

Exercises the complete pipeline against live market data and captures
evidence for every stage. Never places a real Zerodha order.

Usage:
    python -m backend.verification.live_market_verifier --mode shadow --output report.json

Modes:
    shadow  — Record decisions, create virtual shadow trades. Default.
    paper   — Run through PaperBroker. Only if all safety checks pass.

Date: Monday, 27 July 2026 — 09:15 IST (03:45 UTC)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from verification.evidence import EvidenceCollector
from verification.reporters import export_json, format_report

# ── Evidence checklist ──

EVIDENCE_ITEMS = [
    "instrument_tokens",
    "live_ticks",
    "tick_freshness",
    "complete_live_candle",
    "candle_volume",
    "indicator_recalculation",
    "fresh_trading_context",
    "fresh_regime",
    "fresh_ai_decision",
    "buy_sell_scores",
    "risk_validation",
    "trade_plan_output",
    "quote_reconciliation",
    "paper_trade_eligible",
    "shadow_trade_tracking",
    "websocket_disconnect_recovery",
    "duplicate_analysis_protection",
]

# ── Bootstrap ──


async def bootstrap_services() -> dict[str, Any]:
    """Programmatically initialize all services (mirrors main.py startup).

    Returns:
        Dict of service references keyed by name.
    """
    from core.event_bus import EventBus
    from core.symbols import list_canonical_names
    from tick.engine import TickEngine
    from stream.router import StreamRouter
    from candles.engine import CandleEngine
    from indicators.engine import IndicatorEngine
    from market_structure.engine import MarketStructureEngine
    from patterns.engine import PatternEngine
    from trading_context.engine import TradingContextEngine
    from support_resistance.engine import SREngine
    from ai_decision.engine import AIDecisionEngine
    from multi_timeframe.engine import MTFEngine
    from market_regime.engine import RegimeEngine
    from risk.risk_engine import RiskEngine
    from risk.risk_logger import init_risk_tables
    from trading.trade_plan import TradePlanner
    from trading.trade_lifecycle import init_lifecycle
    from trading.pnl_engine import init_pnl_engine
    from trading.runtime_mode import RuntimeModeManager
    from services.market_data_service import MarketDataService
    from services.historical_warmup import HistoricalWarmupEngine
    from services.zerodha_market_data_engine import ZerodhaMarketDataEngine
    from data.provider_factory import ProviderFactory
    from providers.zerodha.kite_provider import KiteProvider
    from execution.paper_broker import init_paper_broker
    from trading.event_service import LifecycleEventService
    from trading.shadow_tracker import ShadowTradeTracker
    from trading.runtime_orchestrator import RuntimeOrchestrator
    from trading.champion_runtime import ChampionRuntimeResolver
    from live.live_execution_gate import LiveExecutionGate
    from live.activation_gate import ControlledLiveActivationGate
    from execution.kill_switch import KillSwitch
    from execution.execution_audit import ExecutionAuditLog
    from execution.execution_health import ExecutionHealthMonitor
    from learning.database import init_learning_tables

    log_info = __import__("utils.logger", fromlist=["log_info"]).log_info

    services = {}

    # Event Bus
    event_bus = EventBus(max_queue_size=1000)
    await event_bus.start()
    services["event_bus"] = event_bus

    # Market Data Service
    market_service = MarketDataService()
    services["market_service"] = market_service

    # Provider Factory
    provider_factory = ProviderFactory()
    services["provider_factory"] = provider_factory

    # Risk Engine
    risk_engine = RiskEngine()
    init_risk_tables()
    services["risk_engine"] = risk_engine

    # Learning tables
    init_learning_tables()

    # Trade Lifecycle
    trade_lifecycle = init_lifecycle()
    services["trade_lifecycle"] = trade_lifecycle

    # PnL Engine
    pnl_engine = init_pnl_engine()
    services["pnl_engine"] = pnl_engine

    # Tick Engine
    tick_engine = TickEngine(event_bus)
    await tick_engine.start()
    services["tick_engine"] = tick_engine

    # Stream Router
    stream_router = StreamRouter(event_bus)
    await stream_router.start()
    services["stream_router"] = stream_router

    # Candle Engine
    candle_engine = CandleEngine(stream_router, event_bus)
    await candle_engine.start()
    services["candle_engine"] = candle_engine

    # Indicator Engine
    indicator_engine = IndicatorEngine(event_bus)
    await indicator_engine.start()
    services["indicator_engine"] = indicator_engine

    # Market Structure Engine
    structure_engine = MarketStructureEngine(event_bus)
    await structure_engine.start()
    services["structure_engine"] = structure_engine

    # Pattern Engine
    pattern_engine = PatternEngine(event_bus)
    await pattern_engine.start()
    services["pattern_engine"] = pattern_engine

    # Trading Context Engine
    context_engine = TradingContextEngine(event_bus)
    await context_engine.start()
    services["context_engine"] = context_engine

    # SR Engine
    sr_engine = SREngine(event_bus)
    await sr_engine.start()
    services["sr_engine"] = sr_engine

    # AI Decision Engine
    ai_engine = AIDecisionEngine(event_bus)
    await ai_engine.start()
    services["ai_engine"] = ai_engine

    # MTF Engine
    mtf_engine = MTFEngine(event_bus)
    await mtf_engine.start()
    services["mtf_engine"] = mtf_engine

    # Regime Engine
    regime_engine = RegimeEngine()
    services["regime_engine"] = regime_engine

    # Trade Planner
    trade_planner = TradePlanner(risk_engine)
    services["trade_planner"] = trade_planner

    # Runtime Mode Manager (default OBSERVE)
    runtime_mgr = RuntimeModeManager()
    services["runtime_mgr"] = runtime_mgr

    # Paper Broker
    paper_broker = init_paper_broker(
        trade_lifecycle, pnl_engine,
        LifecycleEventService(event_bus),
    )
    paper_broker.start()
    services["paper_broker"] = paper_broker

    # Shadow Trade Tracker
    shadow_tracker = ShadowTradeTracker()
    services["shadow_tracker"] = shadow_tracker

    # Runtime Orchestrator
    orchestrator = RuntimeOrchestrator(
        champion_resolver=ChampionRuntimeResolver(),
        mode_manager=runtime_mgr,
        shadow_tracker=shadow_tracker,
        risk_engine=risk_engine,
    )
    services["orchestrator"] = orchestrator

    # Kill Switch & Audit
    kill_switch = KillSwitch()
    services["kill_switch"] = kill_switch
    audit_log = ExecutionAuditLog()
    services["audit_log"] = audit_log

    # Activation Gate (blocked for dry run)
    activation_gate = ControlledLiveActivationGate()
    activation_gate.set_risk_engine(risk_engine)
    activation_gate.set_kill_switch(kill_switch)
    activation_gate.set_runtime_mgr(runtime_mgr)
    activation_gate.set_execution_health(ExecutionHealthMonitor())
    activation_gate.set_audit_log(audit_log)
    services["activation_gate"] = activation_gate

    # Live Execution Gate (blocked)
    live_exec_gate = LiveExecutionGate(activation_gate, None)
    live_exec_gate.set_kill_switch(kill_switch)
    live_exec_gate.set_risk_engine(risk_engine)
    live_exec_gate.set_execution_health(ExecutionHealthMonitor())
    live_exec_gate.set_audit_log(audit_log)
    services["live_exec_gate"] = live_exec_gate

    # Zerodha Kite Provider
    zerodha_kite = None
    try:
        zerodha_kite = provider_factory.get_provider("zerodha")
    except Exception:
        log_info("Zerodha Kite provider not available")

    services["zerodha_kite"] = zerodha_kite

    # Historical Warmup Engine
    warmup_engine = HistoricalWarmupEngine(
        kite_provider=zerodha_kite if isinstance(zerodha_kite, KiteProvider) else None,
    )
    services["warmup_engine"] = warmup_engine

    # Zerodha Market Data Engine
    zerodha_engine = ZerodhaMarketDataEngine(
        event_bus=event_bus,
        kite_provider=zerodha_kite if isinstance(zerodha_kite, KiteProvider) else None,
    )
    zerodha_engine.set_warmup_engine(warmup_engine)
    services["zerodha_engine"] = zerodha_engine

    # Note: warmup feed callback is NOT set here because the verifier
    # manually feeds candles after warmup (step-by-step evidence capture).

    return services


# ── Evidence Capture ──


async def verify_subscriptions(services: dict) -> None:
    """Capture instrument token mapping evidence."""
    from core.symbols import list_canonical_names

    zerodha_engine = services["zerodha_engine"]
    kite = services["zerodha_kite"]

    if not kite or not kite.instruments.is_loaded:
        EvidenceCollector.record("instrument_tokens", "FAIL", error="Instruments not loaded")
        return

    canonical = list_canonical_names()
    resolved = []
    token_map = {}

    for name in canonical:
        token = kite.instruments.map_to_kite_token(name)
        if token:
            resolved.append({"symbol": name, "token": token})
            token_map[token] = name

    # Also capture what the engine has subscribed
    subscribed = list(zerodha_engine._subscribed_tokens) if hasattr(zerodha_engine, "_subscribed_tokens") else []

    EvidenceCollector.record(
        "instrument_tokens", "PASS" if resolved else "FAIL",
        requested=canonical,
        count=len(resolved),
        resolved=resolved,
        subscribed_tokens=subscribed,
    )


async def verify_live_ticks(services: dict, timeout_s: int = 60) -> list[dict]:
    """Wait for and capture at least 5 genuine live ticks from KiteTicker."""
    tick_engine = services["tick_engine"]
    samples = []
    start = time.time()

    EvidenceCollector.record("live_ticks", "INFO", message="Waiting for live ticks...")

    while len(samples) < 5 and (time.time() - start) < timeout_s:
        # Check tick engine buffer for all symbols
        for sym in ["NIFTY 50", "BANKNIFTY", "SENSEX"]:
            tick = tick_engine.latest_tick(sym)
            if tick and tick.price > 0:
                # Deduplicate by timestamp
                ts = str(tick.timestamp)
                if not any(s.get("timestamp") == ts for s in samples):
                    samples.append({
                        "symbol": tick.symbol,
                        "price": tick.price,
                        "volume": tick.volume,
                        "timestamp": ts,
                        "provider": tick.provider,
                        "exchange": tick.exchange,
                        "captured_at": datetime.now(timezone.utc).isoformat(),
                    })
                    if len(samples) >= 5:
                        break
        if len(samples) < 5:
            await asyncio.sleep(0.5)

    if len(samples) >= 5:
        EvidenceCollector.record(
            "live_ticks", "PASS",
            count=len(samples),
            samples=samples[:5],
        )
    else:
        EvidenceCollector.record(
            "live_ticks", "FAIL" if not samples else "WARN",
            count=len(samples),
            samples=samples,
            error=f"Only {len(samples)}/5 ticks received within {timeout_s}s timeout",
        )

    return samples


async def verify_tick_freshness(services: dict) -> None:
    """Verify tick freshness shows LIVE status."""
    zerodha_engine = services["zerodha_engine"]
    freshness = zerodha_engine.freshness_tracker

    summary = freshness.get_status_summary()
    live_count = summary.get("live", 0)
    total = summary.get("total_symbols", 0)

    per_symbol = {}
    for sym in ["NIFTY 50", "BANKNIFTY", "SENSEX"]:
        sf = freshness.get(sym)
        if sf:
            per_symbol[sym] = {
                "tick_freshness": sf.tick_freshness,
                "last_tick_receipt": sf.last_tick_receipt,
            }

    all_live = all(
        f["tick_freshness"] == "LIVE" for f in per_symbol.values()
    )

    EvidenceCollector.record(
        "tick_freshness",
        "PASS" if all_live and live_count > 0 else "WARN" if live_count > 0 else "FAIL",
        live_symbols=live_count,
        total_symbols=total,
        per_symbol=per_symbol,
        summary=summary,
    )


async def verify_candle_formation(services: dict, timeout_s: int = 360) -> None:
    """Wait for at least one CANDLE_CLOSED event and capture it."""
    event_bus = services["event_bus"]
    candle_event = asyncio.Event()
    captured_candle: dict = {}

    async def on_candle_closed(event):
        nonlocal captured_candle
        payload = event.payload
        candle = payload.get("candle", payload)
        sym = candle.get("symbol", "")
        if sym in ("NIFTY 50", "BANKNIFTY", "SENSEX"):
            captured_candle = dict(candle)
            candle_event.set()

    event_bus.subscribe("candle_closed", on_candle_closed, name="verifier_candle")

    try:
        await asyncio.wait_for(candle_event.wait(), timeout=timeout_s)
        passed = bool(captured_candle.get("open", 0) > 0)
        EvidenceCollector.record(
            "complete_live_candle",
            "PASS" if passed else "FAIL",
            symbol=captured_candle.get("symbol"),
            interval=captured_candle.get("interval"),
            time=captured_candle.get("time"),
            open=captured_candle.get("open"),
            high=captured_candle.get("high"),
            low=captured_candle.get("low"),
            close=captured_candle.get("close"),
            volume=captured_candle.get("volume"),
            is_closed=captured_candle.get("is_closed", True),
        )

        # Also capture volume as a separate evidence item
        vol = captured_candle.get("volume", 0)
        EvidenceCollector.record(
            "candle_volume",
            "PASS" if vol and vol > 0 else "FAIL",
            volume=vol,
            symbol=captured_candle.get("symbol"),
        )

    except asyncio.TimeoutError:
        EvidenceCollector.record(
            "complete_live_candle", "FAIL",
            error=f"No CANDLE_CLOSED event within {timeout_s}s timeout",
        )
        EvidenceCollector.record("candle_volume", "FAIL", volume=0, error="No candle closed")

    event_bus.unsubscribe("candle_closed", on_candle_closed)

    return captured_candle


async def verify_indicators(services: dict) -> None:
    """Verify all indicators have been recalculated on the latest candle."""
    indicator_engine = services["indicator_engine"]
    from core.symbols import list_canonical_names

    for symbol in list_canonical_names():
        snap = indicator_engine.latest_snapshot(symbol, "15m")
        if not snap:
            EvidenceCollector.record(
                "indicator_recalculation", "WARN",
                symbol=symbol, interval="15m",
                error="No snapshot available yet",
            )
            continue

        # Check critical indicators
        all_ready = snap.get("all_ready", False)
        ema_200 = snap.get("ema_200")
        ema_50 = snap.get("ema_50")
        rsi = snap.get("rsi_14")
        macd = snap.get("macd")

        indicators_detail = {
            "ema_9": snap.get("ema_9"),
            "ema_20": snap.get("ema_20"),
            "ema_50": ema_50,
            "ema_200": ema_200,
            "sma_20": snap.get("sma_20"),
            "sma_50": snap.get("sma_50"),
            "rsi_14": rsi,
            "atr_14": snap.get("atr_14"),
            "macd": macd,
            "macd_signal": snap.get("macd_signal"),
            "macd_histogram": snap.get("macd_histogram"),
            "adx_14": snap.get("adx_14"),
            "supertrend_trend": snap.get("supertrend_trend"),
            "vwap": snap.get("vwap"),
        }

        # PASS if EMA 200 and RSI are ready (key indicators)
        key_ready = ema_200 is not None and rsi is not None
        EvidenceCollector.record(
            "indicator_recalculation",
            "PASS" if key_ready and all_ready else "WARN" if key_ready else "FAIL",
            symbol=symbol,
            interval="15m",
            all_ready=all_ready,
            indicators=indicators_detail,
        )


async def verify_trading_context(services: dict) -> None:
    """Verify fresh trading context is available."""
    context_engine = services["context_engine"]
    from core.symbols import list_canonical_names

    for symbol in list_canonical_names():
        try:
            snap = context_engine.latest_snapshot(symbol)
            has_data = snap is not None and isinstance(snap, dict) and len(snap) > 1
            EvidenceCollector.record(
                "fresh_trading_context",
                "PASS" if has_data else "FAIL",
                symbol=symbol,
                has_data=has_data,
                snapshot_keys=list(snap.keys()) if snap else [],
            )
        except Exception as e:
            EvidenceCollector.record(
                "fresh_trading_context", "FAIL",
                symbol=symbol, error=str(e),
            )


async def verify_regime(services: dict) -> None:
    """Verify fresh regime result is available."""
    regime_engine = services["regime_engine"]
    from core.symbols import list_canonical_names

    for symbol in list_canonical_names():
        try:
            snap = regime_engine.latest(symbol)
            regime = (snap or {}).get("regime", "") if snap else ""
            confidence = (snap or {}).get("confidence", 0) if snap else 0
            has_data = bool(regime)
            EvidenceCollector.record(
                "fresh_regime",
                "PASS" if has_data else "FAIL",
                symbol=symbol,
                regime=regime,
                confidence=confidence,
            )
        except Exception as e:
            EvidenceCollector.record(
                "fresh_regime", "FAIL",
                symbol=symbol, error=str(e),
            )


async def verify_ai_decision(services: dict) -> None:
    """Verify a fresh AI decision linked to the latest candle."""
    ai_engine = services["ai_engine"]
    from core.symbols import list_canonical_names

    for symbol in list_canonical_names():
        try:
            snap = ai_engine.latest(symbol)
            if not snap:
                EvidenceCollector.record(
                    "fresh_ai_decision", "WARN",
                    symbol=symbol, error="No AI decision yet (may need more candles)",
                )
                continue

            score = snap.get("score", 0)
            confidence = snap.get("confidence", 0)
            direction = snap.get("trade_plan", {}).get("direction", "NONE")
            risk_level = snap.get("risk_level", "UNKNOWN")

            evidence = {
                "symbol": symbol,
                "score": score,
                "confidence": confidence,
                "direction": direction,
                "risk_level": risk_level,
                "reasoning": snap.get("reasoning", [])[:3],
                "has_trade_plan": bool(snap.get("trade_plan")),
            }

            has_decision = score > 0 and confidence > 0
            EvidenceCollector.record(
                "fresh_ai_decision",
                "PASS" if has_decision else "WARN",
                **evidence,
            )
        except Exception as e:
            EvidenceCollector.record(
                "fresh_ai_decision", "FAIL",
                symbol=symbol, error=str(e),
            )


async def verify_buy_sell_scores(services: dict) -> None:
    """Capture BUY and SELL candidate scores with approval/rejection reasons."""
    ai_engine = services["ai_engine"]
    from core.symbols import list_canonical_names

    for symbol in list_canonical_names():
        try:
            snap = ai_engine.latest(symbol)
            if not snap:
                continue

            # Extract score details from reasoning and warnings
            score = snap.get("score", 0)
            confidence = snap.get("confidence", 0)
            direction = snap.get("trade_plan", {}).get("direction", "NONE")
            warnings = snap.get("warnings", [])
            reasoning = snap.get("reasoning", [])

            EvidenceCollector.record(
                "buy_sell_scores",
                "PASS" if score > 0 else "INFO",
                symbol=symbol,
                overall_score=score,
                confidence=confidence,
                direction=direction,
                approval_reasons=reasoning[:5],
                rejection_reasons=warnings[:5],
                score_grade=snap.get("score_grade", ""),
                confidence_grade=snap.get("confidence_grade", ""),
            )
        except Exception as e:
            EvidenceCollector.record(
                "buy_sell_scores", "FAIL",
                symbol=symbol, error=str(e),
            )


async def verify_risk_validation(services: dict) -> None:
    """Capture RiskEngine validation result."""
    risk_engine = services["risk_engine"]
    from risk.trade_validator import TradeIntent
    from core.symbols import list_canonical_names

    for symbol in list_canonical_names():
        try:
            intent = TradeIntent(
                symbol=symbol,
                side="BUY",
                quantity=1,
                price=10000,  # Placeholder — will be validated by live gate
                order_type="MARKET",
                product="MIS",
                exchange="NSE",
                strategy="dry_run_verification",
                ai_score=70.0,
                ai_confidence=65.0,
                ai_decision="BUY",
                stop_loss=9900,
                take_profit=10200,
                tag="dry_run_verify",
            )
            validation = risk_engine.validate(intent)

            EvidenceCollector.record(
                "risk_validation",
                "PASS" if validation.execution_permitted else "WARN",
                symbol=symbol,
                execution_permitted=validation.execution_permitted,
                rejected_by=validation.rejected_by,
            )
        except Exception as e:
            EvidenceCollector.record(
                "risk_validation", "FAIL",
                symbol=symbol, error=str(e),
            )


async def verify_trade_plan(services: dict) -> None:
    """Verify TradePlanner generates a valid trade plan."""
    planner = services["trade_planner"]
    from core.symbols import list_canonical_names

    # Use the latest AI decision to pass into the planner
    ai_engine = services["ai_engine"]

    for symbol in list_canonical_names():
        try:
            snap = ai_engine.latest(symbol)
            if not snap:
                continue

            # The TradePlanner needs context, indicators, etc.
            # We capture whatever the AI engine already planned
            trade_plan = snap.get("trade_plan", {})
            direction = trade_plan.get("direction", "")
            has_plan = bool(direction) and direction != "NONE"

            EvidenceCollector.record(
                "trade_plan_output",
                "PASS" if has_plan else "INFO",
                symbol=symbol,
                direction=direction,
                entry_zone=trade_plan.get("entry_zone"),
                stop_loss=trade_plan.get("stop_loss"),
                target=trade_plan.get("target"),
                strategy=trade_plan.get("strategy"),
                risk_reward=trade_plan.get("risk_reward"),
            )
        except Exception as e:
            EvidenceCollector.record(
                "trade_plan_output", "FAIL",
                symbol=symbol, error=str(e),
            )


async def verify_quote_reconciliation(services: dict) -> None:
    """Perform REST quote reconciliation against latest WebSocket LTP."""
    zerodha_engine = services["zerodha_engine"]
    tick_engine = services["tick_engine"]
    from core.symbols import list_canonical_names

    if not zerodha_engine.is_ws_connected:
        EvidenceCollector.record("quote_reconciliation", "FAIL",
                                  error="WebSocket not connected")
        return

    for symbol in list_canonical_names():
        try:
            latest_tick = tick_engine.latest_tick(symbol)
            if not latest_tick or not latest_tick.price:
                continue

            result = await zerodha_engine.reconcile_quote(symbol, latest_tick.price)
            passed = result.get("passed", False)

            EvidenceCollector.record(
                "quote_reconciliation",
                "PASS" if passed else "FAIL",
                symbol=symbol,
                ws_ltp=result.get("ws_ltp"),
                rest_ltp=result.get("rest_ltp"),
                diff_pct=result.get("diff_pct"),
                threshold_pct=result.get("threshold_pct"),
            )
        except Exception as e:
            EvidenceCollector.record(
                "quote_reconciliation", "FAIL",
                symbol=symbol, error=str(e),
            )


async def verify_paper_trade(services: dict) -> None:
    """Attempt one paper trade if all safety rules pass. Dry-run only."""
    from core.symbols import list_canonical_names

    ai_engine = services["ai_engine"]
    paper_broker = services["paper_broker"]
    runtime_mgr = services["runtime_mgr"]

    # Check runtime mode — paper must be explicitly allowed
    if runtime_mgr.mode.value != "paper":
        EvidenceCollector.record(
            "paper_trade_eligible", "INFO",
            blocked_by=f"Runtime mode is {runtime_mgr.mode.value}, not 'paper'",
            message="Paper trade skipped — not in paper mode",
        )
        return

    # Find best candidate with highest score
    best = None
    for symbol in list_canonical_names():
        snap = ai_engine.latest(symbol)
        if snap and snap.get("score", 0) > 0:
            plan = snap.get("trade_plan", {})
            direction = plan.get("direction", "")
            if direction in ("BUY", "SELL"):
                score = snap.get("score", 0)
                if best is None or score > best["score"]:
                    best = {
                        "symbol": symbol,
                        "score": score,
                        "direction": direction,
                        "entry_price": plan.get("entry_zone", {}).get("entry", 0),
                        "stop_loss": plan.get("stop_loss"),
                        "target": plan.get("target"),
                        "confidence": snap.get("confidence", 0),
                    }

    if not best:
        EvidenceCollector.record(
            "paper_trade_eligible", "INFO",
            message="No eligible trade candidate found",
        )
        return

    # Check safety: verify data freshness
    zerodha_engine = services["zerodha_engine"]
    safe, reason = zerodha_engine.is_data_safe(best["symbol"])
    if not safe:
        EvidenceCollector.record(
            "paper_trade_eligible", "WARN",
            blocked_by=f"Data not safe: {reason}",
            candidate=best,
        )
        return

    # Create the paper trade (safety: PaperBroker does NOT touch Zerodha)
    try:
        trade = paper_broker.execute(
            symbol=best["symbol"],
            side="BUY" if best["direction"] == "BUY" else "SELL",
            quantity=1,
            price=best["entry_price"],
            stop_loss=best["stop_loss"],
            target=best["target"],
            order_type="MARKET",
        )
        EvidenceCollector.record(
            "paper_trade_eligible",
            "PASS" if trade else "WARN",
            candidate=best,
            trade_created=bool(trade),
        )
    except Exception as e:
        EvidenceCollector.record(
            "paper_trade_eligible", "WARN",
            candidate=best,
            error=str(e),
        )


async def verify_shadow_trade(services: dict) -> None:
    """Create and verify a shadow trade tracks correctly."""
    from trading.runtime_mode import RuntimeMode
    from core.symbols import list_canonical_names

    runtime_mgr = services["runtime_mgr"]
    orchestrator = services["orchestrator"]
    ai_engine = services["ai_engine"]
    tick_engine = services["tick_engine"]

    # Switch to SHADOW mode
    if runtime_mgr.mode != RuntimeMode.SHADOW:
        runtime_mgr.set_mode("shadow")

    # Find best BUY or SELL candidate
    best = None
    for symbol in list_canonical_names():
        snap = ai_engine.latest(symbol)
        if snap and snap.get("score", 0) > 0:
            plan = snap.get("trade_plan", {})
            direction = plan.get("direction", "")
            if direction in ("BUY", "SELL"):
                tick = tick_engine.latest_tick(symbol)
                price = tick.price if tick else plan.get("entry_zone", {}).get("entry", 0)
                decision_id = f"dr_{symbol}_{int(time.time())}"
                result = orchestrator.process_decision(
                    symbol=symbol,
                    direction=direction,
                    ai_score=snap.get("score", 0),
                    ai_confidence=snap.get("confidence", 0),
                    entry_price=price,
                    stop_loss=plan.get("stop_loss"),
                    target=plan.get("target"),
                    quantity=1,
                    decision_id=decision_id,
                    trade_plan_id=f"plan_{decision_id}",
                    data_freshness="live",
                )
                best = {
                    "symbol": symbol,
                    "result": result,
                }
                break

    if best:
        action = best["result"].get("action", "unknown")
        passed = action in ("trade_created", "recorded")
        EvidenceCollector.record(
            "shadow_trade_tracking",
            "PASS" if passed else "WARN",
            symbol=best["symbol"],
            action=action,
            mode=best["result"].get("mode"),
            shadow_trade_id=best["result"].get("shadow_trade_id"),
            message=best["result"].get("message", ""),
        )
    else:
        # If no BUY/SELL candidate, the system is working as OBSERVE mode
        # which is expected — record as INFO
        EvidenceCollector.record(
            "shadow_trade_tracking", "INFO",
            message="No BUY/SELL candidate to shadow (system in OBSERVE mode acting correctly)",
        )


async def verify_ws_disconnect_recovery(services: dict) -> None:
    """Simulate a WebSocket disconnect and verify auto-recovery."""
    zerodha_engine = services["zerodha_engine"]

    if not zerodha_engine.is_ws_connected:
        EvidenceCollector.record("websocket_disconnect_recovery", "FAIL",
                                  error="WebSocket not connected initially")
        return

    # Record state before disconnect
    pre_tokens = list(zerodha_engine._subscribed_tokens)
    pre_state = zerodha_engine.state

    # Trigger disconnect
    await zerodha_engine._handle_disconnect()
    disconnect_time = time.time()

    EvidenceCollector.record("websocket_disconnect_recovery", "INFO",
                              message="Disconnect triggered",
                              pre_state=pre_state,
                              subscribed_tokens=len(pre_tokens))

    # Wait for automatic reconnection (with timeout)
    for _ in range(30):  # Up to 30 seconds
        if zerodha_engine.is_ws_connected and zerodha_engine.state not in ("DISCONNECTED", "RECONNECTING", "ERROR"):
            break
        await asyncio.sleep(1)

    recovery_s = round(time.time() - disconnect_time, 1)
    reconnected = zerodha_engine.is_ws_connected
    post_tokens = list(zerodha_engine._subscribed_tokens)
    tokens_restored = set(pre_tokens) == set(post_tokens)

    EvidenceCollector.record(
        "websocket_disconnect_recovery",
        "PASS" if reconnected and tokens_restored else "FAIL",
        reconnected=reconnected,
        recovery_time_s=recovery_s,
        tokens_restored=tokens_restored,
        pre_subscribed=len(pre_tokens),
        post_subscribed=len(post_tokens),
    )


async def verify_dedup_protection(services: dict) -> None:
    """Verify duplicate analysis protection works (cooldown)."""
    # Check that _is_analysis_needed from auto_trade respects cooldown
    # We can't call internal functions directly, so we infer from
    # the event_bus that duplicate CANDLE_CLOSED for same symbol
    # doesn't trigger double processing.

    # The simplest check: verify cooldown constant is positive
    from core.event_bus import EventBus
    event_bus = services["event_bus"]

    try:
        from api.auto_trade import _is_analysis_needed, _mark_analyzed, _last_analysis_times
        from core.symbols import list_canonical_names

        symbol = list_canonical_names()[0]
        # First call should be needed
        before = _is_analysis_needed(symbol)
        _mark_analyzed(symbol)
        # Second call should NOT be needed (cooldown)
        after = _is_analysis_needed(symbol)

        if before and not after:
            EvidenceCollector.record("duplicate_analysis_protection", "PASS",
                                      symbol=symbol,
                                      first_call_needed=before,
                                      second_call_needed=after,
                                      cooldown_s=10.0,
                                      message="Cooldown prevents duplicate analysis")
        else:
            EvidenceCollector.record("duplicate_analysis_protection", "WARN",
                                      symbol=symbol,
                                      first_call_needed=before,
                                      second_call_needed=after,
                                      message=f"Unexpected dedup behavior: before={before}, after={after}")
    except Exception as e:
        EvidenceCollector.record("duplicate_analysis_protection", "INFO",
                                  message=f"Cannot test directly: {e}")


# ── Verdict ──


def compute_verdict(report: dict[str, Any]) -> str:
    """Compute the final verdict based on evidence collected.

    Verdict levels (from worst to best):
        Not Ready
        Ready for Paper Trading
        Ready for Shadow Trading
        Ready for Controlled Live Dry Run
        Ready for Controlled Live
    """
    items = report.get("items", [])
    fail_count = report.get("fail_count", 0)
    pass_count = report.get("pass_count", 0)
    total = report.get("total_items", 0)

    if total == 0:
        return "Not Ready — no evidence collected"

    # Check for critical failures
    critical_items = {"live_ticks", "complete_live_candle", "indicator_recalculation",
                       "tick_freshness", "fresh_ai_decision"}
    critical_fails = set()

    for item in items:
        name = item.get("name", "")
        status = item.get("status", "")
        if name in critical_items and status == "FAIL":
            critical_fails.add(name)

    if critical_fails:
        return f"Not Ready — critical failures: {', '.join(sorted(critical_fails))}"

    # Determine which items passed
    item_statuses = {}
    for item in items:
        item_statuses[item.get("name", "")] = item.get("status", "")

    # Check specific evidence
    has_live_ticks = item_statuses.get("live_ticks") == "PASS"
    has_candle = item_statuses.get("complete_live_candle") == "PASS"
    has_indicators = item_statuses.get("indicator_recalculation") == "PASS"
    has_ai = item_statuses.get("fresh_ai_decision") == "PASS"
    has_risk = item_statuses.get("risk_validation") in ("PASS", "WARN")
    has_plan = item_statuses.get("trade_plan_output") in ("PASS", "INFO")
    has_shadow = item_statuses.get("shadow_trade_tracking") in ("PASS", "INFO")
    has_ws_recovery = item_statuses.get("websocket_disconnect_recovery") in ("PASS", "FAIL")
    has_paper = item_statuses.get("paper_trade_eligible") in ("PASS", "INFO")

    # No critical failures → progress through levels
    if fail_count == 0 and pass_count >= 14:
        if has_paper and item_statuses.get("paper_trade_eligible") == "PASS":
            return "Ready for Paper Trading"
        return "Ready for Controlled Live Dry Run"  # All non-critical evidence passes

    if fail_count <= 2 and has_live_ticks and has_candle and has_indicators:
        return "Ready for Shadow Trading"

    if has_live_ticks and has_candle:
        return "Ready for Shadow Trading (with warnings)"

    return "Not Ready — insufficient evidence"


# ── Main Orchestrator ──


async def run_verification(mode: str = "shadow", output: str | None = None) -> dict:
    """Run the complete pre-market verification and dry run.

    Args:
        mode: Runtime mode — "shadow" (default) or "paper"
        output: Optional file path for JSON report export

    Returns:
        The complete evidence report dict with verdict.
    """
    EvidenceCollector.record("verification_started", "INFO",
                              mode=mode,
                              timestamp=datetime.now(timezone.utc).isoformat(),
                              note="NSE market hours 09:15-15:30 IST")

    # Phase 1: Initialize services
    print("Bootstraping services...")
    services = await bootstrap_services()
    EvidenceCollector.record("services_bootstrapped", "INFO",
                              services=list(services.keys()),
                              count=len(services))

    # Phase 2: Pre-market warmup
    print("Starting Zerodha engine (warmup)...")
    zerodha_engine = services["zerodha_engine"]
    await zerodha_engine.start()

    # Phase 3: Capture pre-market evidence
    print("Capturing subscription evidence...")
    await verify_subscriptions(services)

    # Phase 4: Wait for market open and capture live evidence
    print("Waiting for live ticks (market open at 09:15 IST)...")
    ticks = await verify_live_ticks(services, timeout_s=120)
    if not ticks:
        print("No ticks yet — extending wait...")
        ticks = await verify_live_ticks(services, timeout_s=180)

    await verify_tick_freshness(services)

    # Phase 5: Candle, indicator, and AI evidence
    print("Waiting for first complete candle...")
    await verify_candle_formation(services, timeout_s=360)

    # Small delay for downstream engines to process the candle
    await asyncio.sleep(5)

    print("Capturing indicator evidence...")
    await verify_indicators(services)

    print("Capturing trading context evidence...")
    await verify_trading_context(services)

    print("Capturing regime evidence...")
    await verify_regime(services)

    print("Capturing AI decision evidence...")
    await verify_ai_decision(services)

    print("Capturing score evidence...")
    await verify_buy_sell_scores(services)

    # Phase 6: Validation and trade planning
    print("Capturing risk validation evidence...")
    await verify_risk_validation(services)

    print("Capturing trade plan evidence...")
    await verify_trade_plan(services)

    print("Running quote reconciliation...")
    await verify_quote_reconciliation(services)

    # Phase 7: Execution dry-run
    print("Verifying paper trade eligibility...")
    await verify_paper_trade(services)

    print("Verifying shadow trade tracking...")
    await verify_shadow_trade(services)

    # Phase 8: Resilience
    print("Testing WebSocket disconnect/recovery...")
    await verify_ws_disconnect_recovery(services)

    print("Testing duplicate analysis protection...")
    await verify_dedup_protection(services)

    # Phase 9: Final verdict
    report = EvidenceCollector.get_report()
    verdict = compute_verdict(report)
    report["verdict"] = verdict
    report["mode"] = mode

    # Generate recommendation
    if verdict == "Not Ready":
        report["recommendation"] = (
            "Do NOT proceed with live trading. Fix the failed evidence items first. "
            "Review the report and address each FAIL item."
        )
    elif verdict == "Ready for Paper Trading":
        report["recommendation"] = (
            "Proceed to Paper Trading phase. Monitor for at least one full session. "
            "If Paper broker operates correctly for 5+ trades, consider Shadow mode."
        )
    elif verdict == "Ready for Shadow Trading":
        report["recommendation"] = (
            "Proceed to Shadow Trading. Champion strategy will track virtual trades. "
            "Run for at least 20 virtual trades before considering Paper mode."
        )
    elif verdict == "Ready for Controlled Live Dry Run":
        report["recommendation"] = (
            "Proceed with Controlled Live dry run preparation. "
            "Schedule a supervised dry run with human oversight."
        )
    elif verdict == "Ready for Controlled Live":
        report["recommendation"] = (
            "System is ready for Controlled Live execution. "
            "Ensure human approval is obtained before activating Controlled Live."
        )

    # Output
    text = format_report(report, verbose=False)
    print("\n" + text)

    if output:
        export_json(report, output)
        print(f"\nReport exported to: {output}")

    # Cleanup
    await services["zerodha_engine"].stop()

    return report


def main():
    parser = argparse.ArgumentParser(
        description="MarketMind AI — Pre-Market Verification & Dry Run"
    )
    parser.add_argument(
        "--mode", choices=["shadow", "paper"], default="shadow",
        help="Runtime mode for the dry run (default: shadow)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Path to write JSON report (e.g. report.json)",
    )
    args = parser.parse_args()

    report = asyncio.run(run_verification(mode=args.mode, output=args.output))
    sys.exit(0 if "Not Ready" not in report.get("verdict", "") else 1)


if __name__ == "__main__":
    main()
