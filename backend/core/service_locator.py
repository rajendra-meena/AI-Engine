"""
MarketMind AI — Service Locator

Breaks circular-import chains by providing a single module that holds
references to application-level service instances.  main.py sets these
during its lifespan; route handlers and other modules read them here
instead of re-importing main.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.live_market_engine import LiveMarketDataEngine
    from services.zerodha_market_data_engine import ZerodhaMarketDataEngine
    from stream.router import StreamRouter
    from tick.engine import TickEngine
    from websocket.gateway import WebSocketGateway
    from replay.engine import ReplayEngine


# ── Global references (set by main.py during lifespan) ──

live_engine: LiveMarketDataEngine | None = None
zerodha_engine: ZerodhaMarketDataEngine | None = None
stream_router: StreamRouter | None = None
tick_engine: TickEngine | None = None
websocket_gateway: WebSocketGateway | None = None
replay_engine: ReplayEngine | None = None


def ensure_gateway() -> WebSocketGateway:
    assert websocket_gateway is not None, "WebSocket gateway not initialized"
    return websocket_gateway


def ensure_live_engine() -> LiveMarketDataEngine:
    assert live_engine is not None, "Live engine not initialized"
    return live_engine


def ensure_zerodha_engine() -> ZerodhaMarketDataEngine:
    assert zerodha_engine is not None, "Zerodha market data engine not initialized"
    return zerodha_engine


def ensure_stream_router() -> StreamRouter:
    assert stream_router is not None, "Stream router not initialized"
    return stream_router


def ensure_tick_engine() -> TickEngine:
    assert tick_engine is not None, "Tick engine not initialized"
    return tick_engine
