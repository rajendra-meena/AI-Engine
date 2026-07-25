"""
MarketMind AI — Backend Server Entry Point

Assembles the FastAPI application from modular route files, creates the
global Event Bus, and initializes services on startup.

Phase 4 architecture:
  main.py           — app assembly, middleware, startup, Event Bus lifecycle
  api/              — route handlers (market, prediction, health)
  services/         — business logic layer
  cache/            — CSV disk cache
  core/             — configuration, enums, events, event_bus
  database.py       — SQLite layer
"""

from contextlib import asynccontextmanager
import asyncio
from dotenv import load_dotenv
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from api.market import router as market_router
from api.prediction import router as prediction_router
from api.health import router as health_router
from api.replay import router as replay_router, set_replay_engine
from api.candles import router as candle_router, set_candle_engine
from api.indicators import router as indicator_router, set_indicator_engine
from api.market_structure import router as structure_router, set_market_structure_engine
from api.patterns import router as pattern_router, set_pattern_engine
from api.multi_timeframe import router as mtf_router, set_mtf_engine
from api.ai_decision import router as ai_router, set_ai_decision_engine
from api.support_resistance import router as sr_router, set_sr_engine
from api.trading_context import router as context_router, set_trading_context_engine
from api.ticks import router as tick_router, set_tick_engine
from api.strategy.routes import router as strategy_router
from api.market_intelligence import router as market_intelligence_router
from api.ml_routes import router as ml_router
from api.ai_orchestrator import router as ai_orchestrator_router
from api.research.routes import router as research_router
from api.risk import router as risk_router, set_risk_engine
from api.learning import router as learning_router
from api.orchestrator import router as orchestrator_router, set_orchestrator
from api.trades import router as trades_router
from api.live import router as live_router
from api.market_stream import router as market_stream_router
from api.ai_analyze import router as ai_analyze_router, set_decision_service
from api.trade_plans import router as trade_plans_router, set_trade_planner
from api.execution import router as execution_router, set_execution_gateway
from api.paper import router as paper_router
from api.performance import router as performance_router
from api.backtest import router as backtest_router, set_backtest_runner
from api.kite import router as kite_router, set_provider_factory, set_kite_risk_engine
from services.prediction_service import initialize as init_prediction_service
from services.live_market_engine import LiveMarketDataEngine
from websocket.gateway import WebSocketGateway
from stream.router import StreamRouter
from candles.engine import CandleEngine
from indicators.engine import IndicatorEngine
from market_structure.engine import MarketStructureEngine
from patterns.engine import PatternEngine
from trading_context.engine import TradingContextEngine
from support_resistance.engine import SREngine
from ai_decision.engine import AIDecisionEngine
from multi_timeframe.engine import MTFEngine
from tick.engine import TickEngine
from replay.engine import ReplayEngine
from core.event_bus import EventBus
from core.symbols import list_canonical_names
from core import service_locator
from utils.logger import log_info, log_warn

# Load .env from project root (parent of backend/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── Global services ──

event_bus = EventBus(max_queue_size=1000)
live_engine: LiveMarketDataEngine | None = None
websocket_gateway: WebSocketGateway | None = None
replay_engine: ReplayEngine | None = None
tick_engine: TickEngine | None = None
stream_router: StreamRouter | None = None
candle_engine: CandleEngine | None = None
indicator_engine: IndicatorEngine | None = None
market_structure_engine: MarketStructureEngine | None = None
pattern_engine: PatternEngine | None = None
trading_context_engine: TradingContextEngine | None = None
sr_engine: SREngine | None = None
ai_decision_engine: AIDecisionEngine | None = None
mtf_engine: MTFEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup + shutdown."""
    global live_engine, websocket_gateway, replay_engine, tick_engine
    global stream_router, candle_engine, indicator_engine, market_structure_engine
    global pattern_engine, trading_context_engine, sr_engine, ai_decision_engine, mtf_engine

    # ── Startup ──
    log_info("Application starting", title="MarketMind AI Backend")
    init_prediction_service()
    await event_bus.start()

    # Start the Market Data Service
    from services.market_data_service import MarketDataService

    market_service = MarketDataService()

    # Initialize the ProviderFactory and wire Kite router
    from data.provider_factory import ProviderFactory

    provider_factory = ProviderFactory()
    set_provider_factory(provider_factory)

    # Initialize the Risk Firewall
    from risk.risk_engine import RiskEngine
    from risk.risk_logger import init_risk_tables

    risk_engine = RiskEngine()
    set_risk_engine(risk_engine)
    set_kite_risk_engine(risk_engine)
    init_risk_tables()

    # Initialize learning database tables
    from learning.database import init_learning_tables

    init_learning_tables()

    # Initialize the Trading Orchestrator
    from orchestrator.trading_orchestrator import TradingOrchestrator

    orchestrator = TradingOrchestrator()
    set_orchestrator(orchestrator)

    # Initialize the Trade Lifecycle Manager
    from trading.trade_lifecycle import init_lifecycle
    from api.trades import set_trade_lifecycle

    trade_lifecycle = init_lifecycle()
    set_trade_lifecycle(trade_lifecycle)

    # Initialize the P&L Engine
    from trading.pnl_engine import init_pnl_engine

    pnl_engine = init_pnl_engine()
    from api.live import set_pnl_engine

    set_pnl_engine(pnl_engine)

    # Initialize the Market Subscription Manager
    # Wire P&L engine to trade lifecycle updates
    pnl_engine.on_callback(lambda p: None)

    # Initialize the Market Stream Manager
    from trading.market_stream import init_stream_manager

    stream_manager = init_stream_manager()
    stream_manager.set_pnl_engine(pnl_engine)

    # Start the Tick Engine
    tick_engine = TickEngine(event_bus)
    set_tick_engine(tick_engine)
    await tick_engine.start()

    # Wire MarketStreamManager to forward ticks to TickEngine
    stream_manager.set_tick_callback(lambda tick: asyncio.ensure_future(tick_engine.publish_tick(tick)))

    # Start the Market Stream Router
    stream_router = StreamRouter(event_bus)
    await stream_router.start()

    # Start the Candle Aggregation Engine
    candle_engine = CandleEngine(stream_router, event_bus)
    set_candle_engine(candle_engine)
    await candle_engine.start()

    # Start the Indicator Engine
    indicator_engine = IndicatorEngine(event_bus)
    set_indicator_engine(indicator_engine)
    await indicator_engine.start()

    # Start the Market Structure Engine
    market_structure_engine = MarketStructureEngine(event_bus)
    set_market_structure_engine(market_structure_engine)
    await market_structure_engine.start()

    # Start the Pattern Recognition Engine
    pattern_engine = PatternEngine(event_bus)
    set_pattern_engine(pattern_engine)
    await pattern_engine.start()

    # Start the Trading Context Engine
    trading_context_engine = TradingContextEngine(event_bus)
    set_trading_context_engine(trading_context_engine)
    await trading_context_engine.start()

    # Start the SR Engine
    sr_engine = SREngine(event_bus)
    set_sr_engine(sr_engine)
    await sr_engine.start()

    # Start the AI Decision Engine (capstone)
    ai_decision_engine = AIDecisionEngine(event_bus)
    set_ai_decision_engine(ai_decision_engine)
    await ai_decision_engine.start()

    # Initialize the AI Decision Service
    from ai_decision.decision_service import DecisionService

    decision_service = DecisionService(ai_decision_engine)
    set_decision_service(decision_service)

    # Initialize the Trade Planner with Risk Engine
    from trading.trade_plan import TradePlanner

    trade_planner = TradePlanner(risk_engine)
    set_trade_planner(trade_planner)

    # Initialize the Backtest Runner
    from backtest.backtest_runner import BacktestRunner

    backtest_runner = BacktestRunner()
    set_backtest_runner(backtest_runner)

    # Initialize the Execution Gateway
    from execution.gateway import ExecutionGateway

    exec_gateway = ExecutionGateway(trade_lifecycle, risk_engine)
    set_execution_gateway(exec_gateway)

    # Initialize the Paper Broker
    from execution.paper_broker import init_paper_broker
    from trading.event_service import LifecycleEventService

    paper_broker = init_paper_broker(trade_lifecycle, pnl_engine, LifecycleEventService(event_bus))
    paper_broker.start()

    # Start the Multi-Timeframe Engine
    mtf_engine = MTFEngine(event_bus)
    set_mtf_engine(mtf_engine)
    await mtf_engine.start()

    # Start the Live Market Data Engine
    live_engine = LiveMarketDataEngine(event_bus, market_service)
    service_locator.live_engine = live_engine
    await live_engine.start()

    # Start the Tick Engine (already set above)
    service_locator.tick_engine = tick_engine

    # Start the Stream Router (already set above)
    service_locator.stream_router = stream_router

    # Start the WebSocket Gateway
    websocket_gateway = WebSocketGateway(event_bus)
    service_locator.websocket_gateway = websocket_gateway
    await websocket_gateway.start()

    # Create the Replay Engine
    from replay.engine import ReplayEngine

    replay_engine = ReplayEngine(market_service, event_bus)
    service_locator.replay_engine = replay_engine
    set_replay_engine(replay_engine)

    # Seed engines with recent candle data so they produce initial snapshots
    # for every canonical symbol (prevents 404 on first API call).
    # Note: we feed engines directly rather than via Event Bus to ensure
    # synchronous processing before the first API request arrives.
    for seed_symbol in list_canonical_names():
        try:
            data = await market_service.get_intraday(seed_symbol, "15m", 5)
            seed_candles = data.get("candles", [])
            if seed_candles:
                from core.event_model import Event as BusEvent

                for sc in seed_candles:
                    candle_payload = {
                        "symbol": seed_symbol,
                        "interval": "15m",
                        "candle": {
                            "symbol": seed_symbol,
                            "interval": "15m",
                            "time": sc.get("time", ""),
                            "open": sc.get("open", 0),
                            "high": sc.get("high", 0),
                            "low": sc.get("low", 0),
                            "close": sc.get("close", 0),
                            "volume": sc.get("volume", 0),
                            "is_closed": True,
                        },
                    }
                    ev = BusEvent(
                        type="candle_closed", source="bootstrap", payload=candle_payload
                    )
                    if indicator_engine and indicator_engine._running:
                        await indicator_engine._on_candle_closed(ev)
                    if market_structure_engine and market_structure_engine._running:
                        await market_structure_engine._on_candle_closed(ev)
                    if pattern_engine and pattern_engine._running:
                        await pattern_engine._on_candle_closed(ev)

                # Feed SR engine with latest results from the 3 upstream engines
                if sr_engine and sr_engine._running:
                    ind_snap = (
                        indicator_engine.latest_snapshot(seed_symbol, "15m")
                        if indicator_engine
                        else None
                    )
                    struct_snap = (
                        market_structure_engine.latest_snapshot(seed_symbol, "15m")
                        if market_structure_engine
                        else None
                    )
                    if ind_snap:
                        payload = {"symbol": seed_symbol, **ind_snap}
                        await sr_engine._on_indicator(
                            BusEvent(
                                type="indicators_updated",
                                source="bootstrap",
                                payload=payload,
                            )
                        )
                    if struct_snap:
                        payload = {"symbol": seed_symbol, **struct_snap}
                        await sr_engine._on_structure(
                            BusEvent(
                                type="structure_updated",
                                source="bootstrap",
                                payload=payload,
                            )
                        )
                    await sr_engine._on_candle(ev)

                log_info("Engines seeded", symbol=seed_symbol, count=len(seed_candles))
        except Exception as e:
            log_warn("Engine seeding skipped", error=str(e))

    yield  # Application runs here

    # ── Shutdown ──
    if replay_engine:
        await replay_engine.stop()
    if candle_engine:
        await candle_engine.stop()
    if indicator_engine:
        await indicator_engine.stop()
    if market_structure_engine:
        await market_structure_engine.stop()
    if pattern_engine:
        await pattern_engine.stop()
    if trading_context_engine:
        await trading_context_engine.stop()
    if sr_engine:
        await sr_engine.stop()
    if ai_decision_engine:
        await ai_decision_engine.stop()
    if mtf_engine:
        await mtf_engine.stop()
    await tick_engine.stop()
    if stream_router:
        await stream_router.stop()

    await websocket_gateway.stop()
    log_info("WebSocket gateway stopped")

    await live_engine.stop()
    metrics = live_engine.get_engine_metrics()
    log_info("Live engine stopped", **metrics)

    await event_bus.stop()
    stats = event_bus.get_stats()
    log_info("EventBus stopped", **stats)


app = FastAPI(
    title="MarketMind AI Backend",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routers
app.include_router(market_router)
app.include_router(prediction_router)
app.include_router(health_router)
app.include_router(replay_router)
app.include_router(candle_router)
app.include_router(indicator_router)
app.include_router(structure_router)
app.include_router(pattern_router)
app.include_router(context_router)
app.include_router(sr_router)
app.include_router(ai_router)
app.include_router(ai_analyze_router)
app.include_router(trade_plans_router)
app.include_router(execution_router)
app.include_router(paper_router)
app.include_router(performance_router)
app.include_router(backtest_router)
app.include_router(mtf_router)
app.include_router(tick_router)
app.include_router(strategy_router)
app.include_router(research_router)
app.include_router(ai_orchestrator_router)
app.include_router(market_intelligence_router)
app.include_router(ml_router)
app.include_router(kite_router)
app.include_router(risk_router)
app.include_router(learning_router)
app.include_router(orchestrator_router)
app.include_router(trades_router)
app.include_router(live_router)
app.include_router(market_stream_router)


# ── WebSocket endpoint ──


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time market data streaming."""
    assert websocket_gateway is not None, "WebSocket gateway not initialized"
    await websocket_gateway.handle_connection(websocket)


# ── Expose global services for future modules ──


def get_event_bus() -> EventBus:
    """Return the global Event Bus instance. Used by future modules."""
    return event_bus


def get_live_engine() -> LiveMarketDataEngine:
    """Return the global Live Market Data Engine instance."""
    assert live_engine is not None, "Live engine not initialized"
    return live_engine


def get_tick_engine() -> TickEngine:
    """Return the global Tick Engine instance."""
    assert tick_engine is not None, "Tick engine not initialized"
    return tick_engine


def get_replay_engine():
    """Return the global Replay Engine instance."""
    assert replay_engine is not None, "Replay engine not initialized"
    return replay_engine


def get_websocket_gateway() -> WebSocketGateway:
    """Return the global WebSocket Gateway instance."""
    assert websocket_gateway is not None, "WebSocket gateway not initialized"
    return websocket_gateway


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


