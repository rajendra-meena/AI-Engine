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
from services.prediction_service import initialize as init_prediction_service
from services.live_market_engine import LiveMarketDataEngine
from websocket.gateway import WebSocketGateway
from core.event_bus import EventBus
from utils.logger import log_info

# ── Global services ──

event_bus = EventBus(max_queue_size=1000)
live_engine: LiveMarketDataEngine | None = None
websocket_gateway: WebSocketGateway | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup + shutdown."""
    global live_engine, websocket_gateway

    # ── Startup ──
    log_info("Application starting", title="MarketMind AI Backend")
    init_prediction_service()
    await event_bus.start()

    # Start the Live Market Data Engine
    from services.market_data_service import MarketDataService
    market_service = MarketDataService()
    live_engine = LiveMarketDataEngine(event_bus, market_service)
    await live_engine.start()

    # Start the WebSocket Gateway
    websocket_gateway = WebSocketGateway(event_bus)
    await websocket_gateway.start()

    yield  # Application runs here

    # ── Shutdown ──
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


def get_websocket_gateway() -> WebSocketGateway:
    """Return the global WebSocket Gateway instance."""
    assert websocket_gateway is not None, "WebSocket gateway not initialized"
    return websocket_gateway


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
