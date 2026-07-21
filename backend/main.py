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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import WebSocket

from api.market import router as market_router
from api.prediction import router as prediction_router
from api.health import router as health_router
from api.replay import router as replay_router, set_replay_engine
from api.candles import router as candle_router, set_candle_engine
from api.indicators import router as indicator_router, set_indicator_engine
from api.market_structure import router as structure_router, set_market_structure_engine
from api.patterns import router as pattern_router, set_pattern_engine
from api.multi_timeframe import router as mtf_router, set_mtf_engine
from api.support_resistance import router as sr_router, set_sr_engine
from api.trading_context import router as context_router, set_trading_context_engine
from api.ticks import router as tick_router, set_tick_engine
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
from multi_timeframe.engine import MTFEngine
from tick.engine import TickEngine
from core.event_bus import EventBus
from utils.logger import log_info

# ── Global services ──

event_bus = EventBus(max_queue_size=1000)
live_engine: LiveMarketDataEngine | None = None
websocket_gateway: WebSocketGateway | None = None
replay_engine: "ReplayEngine | None" = None
tick_engine: TickEngine | None = None
stream_router: StreamRouter | None = None
candle_engine: CandleEngine | None = None
indicator_engine: IndicatorEngine | None = None
market_structure_engine: MarketStructureEngine | None = None
pattern_engine: PatternEngine | None = None
trading_context_engine: TradingContextEngine | None = None
sr_engine: SREngine | None = None
mtf_engine: MTFEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup + shutdown."""
    global live_engine, websocket_gateway, replay_engine, tick_engine, stream_router, candle_engine, indicator_engine, market_structure_engine, pattern_engine, trading_context_engine, sr_engine, mtf_engine

    # ── Startup ──
    log_info("Application starting", title="MarketMind AI Backend")
    init_prediction_service()
    await event_bus.start()

    # Start the Market Data Service
    from services.market_data_service import MarketDataService
    market_service = MarketDataService()

    # Start the Tick Engine
    tick_engine = TickEngine(event_bus)
    set_tick_engine(tick_engine)
    await tick_engine.start()

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

    # Start the Multi-Timeframe Engine
    mtf_engine = MTFEngine(event_bus)
    set_mtf_engine(mtf_engine)
    await mtf_engine.start()

    # Start the Live Market Data Engine
    live_engine = LiveMarketDataEngine(event_bus, market_service)
    await live_engine.start()

    # Start the WebSocket Gateway
    websocket_gateway = WebSocketGateway(event_bus)
    await websocket_gateway.start()

    # Create the Replay Engine
    from replay.engine import ReplayEngine
    replay_engine = ReplayEngine(market_service, event_bus)
    set_replay_engine(replay_engine)

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
app.include_router(mtf_router)
app.include_router(tick_router)


# ── WebSocket endpoint ──

from fastapi import WebSocket


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
