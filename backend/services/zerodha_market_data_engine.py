"""
MarketMind AI — Zerodha Market Data Engine

Centralized coordinator for all Zerodha Kite Connect market data operations
used by the Auto Trade pipeline.

Responsibilities:
  - Authenticate Kite Connect via env vars
  - Load and validate instrument master
  - Create and manage KiteTicker WebSocket
  - Subscribe / unsubscribe instrument tokens
  - Process live ticks, forward to TickEngine
  - Track freshness per symbol
  - Detect stale instruments
  - Handle reconnection with subscription restoration
  - Detect and fill data gaps
  - Trigger quote reconciliation before orders
  - Publish health events
  - Block execution when data is unsafe

Flow:
    Engine.start()
        → Authenticate
        → Load instruments
        → Create KiteTicker
        → Subscribe universe
        → Wait for live ticks
        → Publish ready

    On tick:
        → Normalize
        → Forward to TickEngine
        → Update freshness tracker
        → Publish LIVE_TICK_RECEIVED

    On disconnect:
        → Block signals
        → Attempt reconnect
        → Restore subscriptions
        → Reconcile gaps
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Callable

from kiteconnect import KiteTicker

from core.event_bus import EventBus
from core.event_model import Event
from core.freshness import (
    SymbolFreshnessTracker,
    SymbolFreshness,
    freshness_metadata,
    FRESHNESS_LIVE,
    FRESHNESS_STALE,
    FRESHNESS_DISCONNECTED,
    FRESHNESS_WARMING_UP,
    TICK_FRESHNESS_MS,
    STALE_THRESHOLD_MS,
    DISCONNECTED_THRESHOLD_MS,
)
from core.zerodha_events import (
    ZERODHA_AUTHENTICATED,
    ZERODHA_AUTH_FAILED,
    ZERODHA_TOKEN_EXPIRED,
    INSTRUMENTS_LOADING,
    INSTRUMENTS_LOADED,
    INSTRUMENTS_LOAD_FAILED,
    KITE_WS_CONNECTING,
    KITE_WS_CONNECTED,
    KITE_WS_DISCONNECTED,
    KITE_WS_RECONNECTING,
    KITE_WS_ERROR,
    KITE_WS_NORECONNECT,
    SYMBOL_SUBSCRIBED,
    SYMBOL_UNSUBSCRIBED,
    LIVE_TICK_RECEIVED,
    MARKET_DATA_STALE,
    MARKET_DATA_RECOVERED,
    CANDLE_CONTINUITY_LOST,
    DATA_GAP_DETECTED,
    DATA_GAP_FILLED,
    QUOTE_RECONCILIATION_TRIGGERED,
    QUOTE_RECONCILIATION_PASSED,
    QUOTE_RECONCILIATION_FAILED,
    MARKET_DATA_ENGINE_STARTED,
    MARKET_DATA_ENGINE_STOPPED,
    MARKET_DATA_ENGINE_ERROR,
    RECONNECTION_STARTED,
    RECONNECTION_COMPLETED,
    RECONNECTION_FAILED,
)
from models.tick import Tick
from providers.zerodha.kite_provider import KiteProvider
from providers.zerodha.websocket import KiteWebSocketClient
from core.symbols import list_canonical_names
from utils.logger import log_info, log_warn, log_error

# Lazy import to avoid circular dependency at module level
_HISTORICAL_WARMUP_IMPORTED = False

def _import_warmup():
    global _HISTORICAL_WARMUP_IMPORTED
    if not _HISTORICAL_WARMUP_IMPORTED:
        from services.historical_warmup import HistoricalWarmupEngine as _hwe
        globals()["HistoricalWarmupEngine"] = _hwe
        _HISTORICAL_WARMUP_IMPORTED = True

# ── Constants ──

UNIVERSE_LIMIT = 50  # Max instruments to subscribe
SUBSCRIBE_BATCH_SIZE = 10  # Tokens per batch
WS_HEALTH_CHECK_INTERVAL = 30  # Seconds between health checks
FRESHNESS_REFRESH_INTERVAL = 15  # Seconds between freshness recomputation
RECONNECT_MAX_ATTEMPTS = 10
QUOTE_RECONCILE_THRESHOLD_PCT = 0.1  # Max allowed WS/REST LTP diff

EngineState = str

STATE_OFF = "OFF"
STATE_AUTHENTICATING = "AUTHENTICATING"
STATE_LOADING_INSTRUMENTS = "LOADING_INSTRUMENTS"
STATE_LOADING_HISTORY = "LOADING_HISTORY"
STATE_SUBSCRIBING = "SUBSCRIBING"
STATE_WARMING_INDICATORS = "WARMING_INDICATORS"
STATE_CONNECTED = "CONNECTED"  # Auth + WS + subscription + warmup succeeded
STATE_WAITING_FOR_LIVE_TICKS = "WAITING_FOR_LIVE_TICKS"  # Connected, waiting for exchange tick
STATE_RECEIVING_LIVE_TICKS = "RECEIVING_LIVE_TICKS"  # At least one live tick received
STATE_DATA_READY = "DATA_READY"  # Ticks + candles + indicators all fresh
STATE_SCANNING = "SCANNING"  # Full pipeline active, analysis allowed
STATE_DISCONNECTED = "DISCONNECTED"
STATE_RECONNECTING = "RECONNECTING"
STATE_MARKET_CLOSED = "MARKET_CLOSED"
STATE_BLOCKED = "BLOCKED"
STATE_ERROR = "ERROR"

# Transition guard: states where trade analysis is prohibited
ANALYSIS_BLOCKED_STATES = frozenset({
    STATE_OFF, STATE_ERROR, STATE_BLOCKED, STATE_DISCONNECTED,
    STATE_RECONNECTING, STATE_CONNECTED, STATE_WAITING_FOR_LIVE_TICKS,
    STATE_RECEIVING_LIVE_TICKS, STATE_MARKET_CLOSED,
})


class ZerodhaMarketDataEngine:
    """
    Central coordinator for Zerodha Kite market data in the Auto Trade pipeline.

    Singleton-like instance created at startup and injected into services.
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        kite_provider: KiteProvider | None = None,
        freshness_tracker: SymbolFreshnessTracker | None = None,
    ):
        self._event_bus = event_bus
        self._kite_provider = kite_provider
        self._freshness = freshness_tracker or SymbolFreshnessTracker()

        # WebSocket
        self._ws_client: KiteWebSocketClient | None = None
        self._ws_connected = False
        self._subscribed_tokens: list[int] = []

        # Engine state
        self._state: EngineState = STATE_OFF
        self._running = False
        self._tick_callback: Callable | None = None

        # Historical warmup
        self._warmup_engine: HistoricalWarmupEngine | None = None
        self._warmup_feed_callback: Callable | None = None

        # Readiness flags — separate from single state enum for fine-grained checks
        self._readiness: dict[str, bool] = {
            "authenticated": False,
            "websocket_connected": False,
            "subscriptions_active": False,
            "historical_ready": False,
            "indicators_ready": False,
            "receiving_live_ticks": False,
            "data_fresh": False,
            "analysis_ready": False,
            "execution_ready": False,
        }

        # Background tasks
        self._health_task: asyncio.Task | None = None
        self._freshness_task: asyncio.Task | None = None

        # Stats
        self._stats = {
            "total_ticks_received": 0,
            "total_events_published": 0,
            "total_reconnects": 0,
            "start_time": None,
            "last_tick_time": None,
            "last_tick_symbol": "",
        }

        # Token → symbol cache
        self._token_to_symbol: dict[int, str] = {}

        # Market closed tracking
        self._market_open: bool = True

    # ── Properties ──

    @property
    def state(self) -> EngineState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_ws_connected(self) -> bool:
        return self._ws_connected

    @property
    def kite_provider(self) -> KiteProvider | None:
        return self._kite_provider

    @property
    def freshness_tracker(self) -> SymbolFreshnessTracker:
        return self._freshness

    def set_event_bus(self, event_bus: EventBus):
        self._event_bus = event_bus

    def set_kite_provider(self, provider: KiteProvider):
        self._kite_provider = provider

    def set_tick_callback(self, callback: Callable):
        """Set callback for normalized ticks (TickEngine.publish_tick)."""
        self._tick_callback = callback

    def set_warmup_engine(self, engine: HistoricalWarmupEngine):
        """Set historical warmup engine for pre-market indicator warmup."""
        self._warmup_engine = engine

    def set_warmup_feed_callback(self, callback: Callable):
        """Set callback invoked after warmup to feed candles into downstream engines.

        Signature: async callback(warmup_results: dict) -> None
        The callback receives the output of HistoricalWarmupEngine.warmup_all().
        """
        self._warmup_feed_callback = callback

    # ── Lifecycle ──

    async def start(self):
        """Start the engine: authenticate, load instruments, init WebSocket."""
        if self._running:
            log_warn("ZerodhaMarketDataEngine already running")
            return

        self._running = True
        self._stats["start_time"] = _now_str()

        try:
            # Step 1: Authenticate
            self._set_state(STATE_AUTHENTICATING)
            if not await self._authenticate():
                self._set_state(STATE_ERROR)
                await self._publish_event(MARKET_DATA_ENGINE_ERROR, {"error": "Authentication failed"})
                return

            # Step 2: Load instruments
            self._set_state(STATE_LOADING_INSTRUMENTS)
            if not await self._load_instruments():
                self._set_state(STATE_ERROR)
                return

            # Step 3: Initialize WebSocket
            if not await self._init_websocket():
                self._set_state(STATE_ERROR)
                return

            # Step 4: Subscribe default universe
            self._set_state(STATE_SUBSCRIBING)
            await self._subscribe_default_universe()

            # Step 4b: Historical indicator warmup (pre-fetch via Kite API)
            # Uses the states LOADING_HISTORY and WARMING_INDICATORS.
            # If Kite historical data is unavailable, transition to BLOCKED — never use Yahoo fallback.
            if self._warmup_engine and self._warmup_engine.is_kite_available():
                await self._run_warmup_after_subscribe()
            else:
                log_error("ZerodhaMarketDataEngine: Kite historical data unavailable — Auto Trade cannot warm up")
                self._set_state(STATE_BLOCKED)
                await self._publish_event(MARKET_DATA_ENGINE_ERROR, {
                    "error": "Kite historical data unavailable, warmup required. Auto Trade blocked."
                })
                return  # Exit — engine cannot proceed without warmup

            # Step 5: After warmup, transition to WAITING_FOR_LIVE_TICKS (NOT CONNECTED as analysis-ready)
            # warmup completed to CONNECTED; now wait for first exchange tick
            self._set_state(STATE_WAITING_FOR_LIVE_TICKS)

            # Step 6: Start background tasks
            self._health_task = asyncio.create_task(
                self._health_check_loop(), name="zd_market_data_health"
            )
            self._freshness_task = asyncio.create_task(
                self._freshness_loop(), name="zd_freshness_check"
            )

            await self._publish_event(MARKET_DATA_ENGINE_STARTED, {
                "state": self._state,
                "subscribed_tokens": len(self._subscribed_tokens),
            })
            log_info("ZerodhaMarketDataEngine started", state=self._state)

        except Exception as e:
            self._set_state(STATE_ERROR)
            log_error("ZerodhaMarketDataEngine start failed", error=str(e))
            await self._publish_event(MARKET_DATA_ENGINE_ERROR, {"error": str(e)})

    async def stop(self):
        """Stop the engine, disconnect WebSocket, clean up."""
        self._running = False

        # Cancel background tasks
        for task in [self._health_task, self._freshness_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Disconnect WebSocket
        if self._ws_client:
            try:
                self._ws_client.disconnect()
            except Exception:
                pass
            self._ws_client = None

        # Disconnect provider
        if self._kite_provider:
            try:
                await self._kite_provider.disconnect()
            except Exception:
                pass

        self._ws_connected = False
        self._subscribed_tokens = []
        self._set_state(STATE_OFF)
        await self._publish_event(MARKET_DATA_ENGINE_STOPPED, {})
        log_info("ZerodhaMarketDataEngine stopped")

    # ── Authentication ──

    async def _authenticate(self) -> bool:
        """Authenticate with Zerodha Kite using env credentials.

        If the provider is already connected (e.g. via API), reuses the
        existing session instead of creating a new one.
        """
        api_key = os.getenv("KITE_API_KEY", "")
        access_token = os.getenv("KITE_ACCESS_TOKEN", "")

        if not self._kite_provider:
            log_error("ZerodhaMarketDataEngine: no KiteProvider available")
            return False

        if not api_key or not access_token:
            log_error("ZerodhaMarketDataEngine: KITE_API_KEY or KITE_ACCESS_TOKEN not set")
            await self._publish_event(ZERODHA_AUTH_FAILED, {
                "error": "Missing KITE_API_KEY or KITE_ACCESS_TOKEN"
            })
            return False

        try:
            # If already authenticated and connected, skip re-connect
            if self._kite_provider.auth.is_authenticated and self._kite_provider._connected:
                await self._publish_event(ZERODHA_AUTHENTICATED, {
                    "user_id": self._kite_provider.auth.user_id,
                    "exchange": "NSE",
                })
                log_info(
                    "ZerodhaMarketDataEngine: using existing session",
                    user_id=self._kite_provider.auth.user_id,
                )
                return True

            # Connect provider (authenticates + loads instruments)
            success = await self._kite_provider.connect()
            if not success:
                log_error("ZerodhaMarketDataEngine: provider connect failed")
                await self._publish_event(ZERODHA_AUTH_FAILED, {
                    "error": "Provider connect returned False"
                })
                return False

            await self._publish_event(ZERODHA_AUTHENTICATED, {
                "user_id": self._kite_provider.auth.user_id,
                "exchange": "NSE",
            })
            log_info(
                "ZerodhaMarketDataEngine: authenticated",
                user_id=self._kite_provider.auth.user_id,
            )
            return True

        except Exception as e:
            log_error("ZerodhaMarketDataEngine: auth error", error=str(e))
            await self._publish_event(ZERODHA_AUTH_FAILED, {"error": str(e)})
            return False

    # ── Instrument loading ──

    async def _load_instruments(self) -> bool:
        """Load instrument master and build token→symbol mapping."""
        try:
            await self._publish_event(INSTRUMENTS_LOADING, {})

            if not self._kite_provider:
                log_error("ZerodhaMarketDataEngine: no kite provider")
                await self._publish_event(INSTRUMENTS_LOAD_FAILED, {"error": "No provider"})
                return False

            # If instruments are not yet loaded, try to load them
            if not self._kite_provider.instruments.is_loaded:
                await self._kite_provider.instruments.load()
                if not self._kite_provider.instruments.is_loaded:
                    log_error("ZerodhaMarketDataEngine: instruments failed to load")
                    await self._publish_event(INSTRUMENTS_LOAD_FAILED, {"error": "Not loaded"})
                    return False

            # Build token→symbol mapping
            self._token_to_symbol.clear()
            canonical = list_canonical_names()
            for name in canonical:
                token = self._kite_provider.instruments.map_to_kite_token(name)
                if token:
                    self._token_to_symbol[token] = name

            # Init freshness for all canonical symbols
            for name in canonical:
                sf = self._freshness.get_or_create(name)
                token = self._kite_provider.instruments.map_to_kite_token(name)
                kite_sym = self._kite_provider.instruments.map_to_kite_symbol(name)
                if token:
                    sf.instrument_token = token
                if kite_sym:
                    sf.tradingsymbol = kite_sym
                sf.exchange = "NSE"

            await self._publish_event(INSTRUMENTS_LOADED, {
                "count": len(self._token_to_symbol),
                "symbols": canonical,
            })
            log_info(
                "ZerodhaMarketDataEngine: instruments loaded",
                count=len(self._token_to_symbol),
            )
            return True

        except Exception as e:
            log_error("ZerodhaMarketDataEngine: instrument loading error", error=str(e))
            await self._publish_event(INSTRUMENTS_LOAD_FAILED, {"error": str(e)})
            return False

    # ── WebSocket ──

    async def _init_websocket(self) -> bool:
        """Initialize and connect the KiteTicker WebSocket.

        If the kite_provider already has an active WebSocket client,
        reuse it instead of creating a new one.
        """
        if not self._kite_provider or not self._kite_provider.auth.is_authenticated:
            log_error("ZerodhaMarketDataEngine: cannot init WS, not authenticated")
            return False

        api_key = self._kite_provider.auth.api_key
        # Use the KiteProvider's resolved access token (env var → file restore → auth)
        kite = self._kite_provider.auth.kite
        access_token = kite.access_token if kite else os.getenv("KITE_ACCESS_TOKEN", "")

        if not api_key or not access_token:
            log_error("ZerodhaMarketDataEngine: missing credentials for WS")
            return False

        try:
            # Check if the provider already has a connected WebSocket
            if self._kite_provider.ws_client and self._kite_provider.ws_client.is_connected():
                self._ws_client = self._kite_provider.ws_client
                self._ws_connected = True
                self._subscribed_tokens = list(self._ws_client._subscribed_tokens)
                log_info("ZerodhaMarketDataEngine: reusing existing WebSocket",
                         tokens=len(self._subscribed_tokens))
                await self._publish_event(KITE_WS_CONNECTED, {})
                return True

            await self._publish_event(KITE_WS_CONNECTING, {})

            self._ws_client = KiteWebSocketClient(
                api_key=api_key,
                access_token=access_token,
                tick_callback=self._on_incoming_tick,
            )

            await self._ws_client.connect()
            self._ws_connected = True

            await self._publish_event(KITE_WS_CONNECTED, {})
            log_info("ZerodhaMarketDataEngine: WebSocket connected")
            return True

        except Exception as e:
            self._ws_connected = False
            log_error("ZerodhaMarketDataEngine: WS init failed", error=str(e))
            await self._publish_event(KITE_WS_ERROR, {"error": str(e)})
            return False

    # ── Subscriptions ──

    async def _subscribe_default_universe(self):
        """Subscribe to all canonical symbols."""
        if not self._ws_client or not self._ws_connected:
            log_warn("ZerodhaMarketDataEngine: WS not connected, cannot subscribe")
            return

        tokens = []
        for name in list_canonical_names():
            token = self._kite_provider.instruments.map_to_kite_token(name)
            if token and token not in tokens:
                tokens.append(token)

        if not tokens:
            log_warn("ZerodhaMarketDataEngine: no tokens to subscribe")
            return

        # Batch subscribe
        for i in range(0, len(tokens), SUBSCRIBE_BATCH_SIZE):
            batch = tokens[i:i + SUBSCRIBE_BATCH_SIZE]
            self._ws_client.subscribe(batch)
            self._subscribed_tokens.extend(batch)
            for token in batch:
                sym = self._token_to_symbol.get(token, str(token))
                await self._publish_event(SYMBOL_SUBSCRIBED, {
                    "token": token,
                    "symbol": sym,
                })

        log_info(
            "ZerodhaMarketDataEngine: subscribed",
            total=len(self._subscribed_tokens),
            batches=(len(tokens) // SUBSCRIBE_BATCH_SIZE) + 1,
        )

    async def _run_warmup_after_subscribe(self):
        """Run historical indicator warmup using Kite API data.

        Called after WebSocket subscription, before waiting for live ticks.
        Fetches enough historical candles to prime all indicators (including
        EMA 200), feeds them into downstream engines via callback, then
        transitions to CONNECTED state.

        Uses the dead states STATE_LOADING_HISTORY and STATE_WARMING_INDICATORS
        which were reserved for this purpose.
        """
        _import_warmup()
        from indicators.engine import IndicatorComputeUnit

        self._set_state(STATE_LOADING_HISTORY)
        canonical = list_canonical_names()
        warmup_intervals = ["1m", "3m", "5m", "15m"]
        min_candles = IndicatorComputeUnit.compute_max_warmup_needed() + 50

        log_info(
            "ZerodhaMarketDataEngine: starting historical warmup",
            symbols=canonical,
            intervals=warmup_intervals,
            min_candles=min_candles,
        )

        results = await self._warmup_engine.warmup_all(
            symbols=canonical,
            intervals=warmup_intervals,
            min_candles=min_candles,
        )

        self._set_state(STATE_WARMING_INDICATORS)

        # Feed warmup candles into downstream engines via callback
        if self._warmup_feed_callback:
            try:
                if asyncio.iscoroutinefunction(self._warmup_feed_callback):
                    await self._warmup_feed_callback(results)
                else:
                    self._warmup_feed_callback(results)
            except Exception as e:
                log_error("ZerodhaMarketDataEngine: warmup feed callback failed", error=str(e))

        # Note: freshness tracker is NOT updated here for candles/indicators — those
        # were fed through the feed callback which already updated engines.
        # Mark only that warmup is structurally complete.
        # LIVE tick freshness will be set when the first exchange tick arrives.

        # Mark engine as CONNECTED (warmup completed structurally)
        # The engine does NOT enter DATA_READY or SCANNING until a live tick arrives.
        self._set_state(STATE_CONNECTED)
        log_info("ZerodhaMarketDataEngine: warmup complete, engine CONNECTED (awaiting live ticks)")

    async def subscribe_symbol(self, symbol: str) -> bool:
        """Subscribe a single symbol."""
        if not self._ws_client or not self._ws_connected:
            return False

        token = self._kite_provider.instruments.map_to_kite_token(symbol)
        if not token:
            log_warn("ZerodhaMarketDataEngine: cannot subscribe, unknown symbol", symbol=symbol)
            return False

        if token in self._subscribed_tokens:
            return True  # Already subscribed

        self._ws_client.subscribe([token])
        self._subscribed_tokens.append(token)
        self._token_to_symbol[token] = symbol

        await self._publish_event(SYMBOL_SUBSCRIBED, {"token": token, "symbol": symbol})
        return True

    async def unsubscribe_symbol(self, symbol: str) -> bool:
        """Unsubscribe a single symbol."""
        if not self._ws_client or not self._ws_connected:
            return False

        token = self._kite_provider.instruments.map_to_kite_token(symbol)
        if not token or token not in self._subscribed_tokens:
            return False

        self._ws_client.unsubscribe([token])
        self._subscribed_tokens = [t for t in self._subscribed_tokens if t != token]

        await self._publish_event(SYMBOL_UNSUBSCRIBED, {"token": token, "symbol": symbol})
        return True

    # ── Tick handling ──

    def _on_incoming_tick(self, tick: Tick):
        """Called by KiteWebSocketClient for each normalized tick."""
        try:
            self._stats["total_ticks_received"] += 1
            self._stats["last_tick_time"] = _now_str()
            self._stats["last_tick_symbol"] = tick.symbol

            # Update freshness tracker
            instrument_token = 0
            tradingsymbol = tick.symbol
            exchange = getattr(tick, "exchange", "NSE") or "NSE"

            # Resolve token:XXX prefix
            symbol_name = tick.symbol
            if tick.symbol.startswith("token:"):
                try:
                    token = int(tick.symbol.replace("token:", ""))
                    instrument_token = token
                    symbol_name = self._token_to_symbol.get(token, tick.symbol)
                except (ValueError, TypeError):
                    pass

            self._freshness.update_tick(
                symbol=symbol_name,
                instrument_token=instrument_token,
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                receipt_time=_now_str(),
                exchange_time=tick.timestamp.isoformat() if hasattr(tick.timestamp, "isoformat") else str(tick.timestamp),
            )

            # Forward to TickEngine
            if self._tick_callback:
                # Create resolved tick with correct symbol name
                resolved_tick = Tick(
                    symbol=symbol_name,
                    price=tick.price,
                    timestamp=tick.timestamp,
                    volume=tick.volume,
                    bid=tick.bid,
                    ask=tick.ask,
                    provider="zerodha",
                    exchange=exchange,
                )
                self._tick_callback(resolved_tick)

            # Publish live tick event
            asyncio.ensure_future(
                self._publish_event(LIVE_TICK_RECEIVED, {
                    "symbol": symbol_name,
                    "instrument_token": instrument_token,
                    "price": tick.price,
                    "timestamp": _now_str(),
                })
            )

            # Transition through state machine on first live tick
            # CONNECTED → WAITING_FOR_LIVE_TICKS → RECEIVING_LIVE_TICKS → DATA_READY
            if self._state in (STATE_CONNECTED, STATE_WAITING_FOR_LIVE_TICKS):
                self._set_state(STATE_RECEIVING_LIVE_TICKS)
                log_info("ZerodhaMarketDataEngine: first live tick received, transitioning to RECEIVING_LIVE_TICKS")
            elif self._state == STATE_RECEIVING_LIVE_TICKS:
                # After enough ticks confirm data flow, move to DATA_READY
                # Check: at least 3 ticks and candle data flowing
                if self._stats["total_ticks_received"] >= 3:
                    self._set_state(STATE_DATA_READY)
                    log_info("ZerodhaMarketDataEngine: sufficient ticks received, DATA_READY")

        except Exception as e:
            log_error("ZerodhaMarketDataEngine: tick processing error", error=str(e))

    # ── Data safety checks ──

    def is_data_safe(self, symbol: str) -> tuple[bool, str]:
        """
        Verify all freshness checks pass for a symbol.
        Returns (safe: bool, reason: str).
        """
        return self._freshness.is_data_safe(symbol)

    def is_any_data_safe(self) -> bool:
        """Check if the engine overall has safe data."""
        if not self._ws_connected:
            return False
        if self._state in (STATE_ERROR, STATE_DISCONNECTED, STATE_OFF):
            return False
        return self._freshness.all_data_safe()

    def check_pre_execution_safety(self, symbol: str) -> dict[str, Any]:
        """
        Run all pre-execution safety checks.
        Returns dict with check results and blocking reasons.
        """
        checks = {}
        all_pass = True
        blocking = []

        # 1. WebSocket connected
        ws_ok = self._ws_connected
        checks["websocket_connected"] = ws_ok
        if not ws_ok:
            all_pass = False
            blocking.append("WebSocket market data is disconnected")

        # 2. Engine state
        state_ok = self._state not in (STATE_ERROR, STATE_DISCONNECTED, STATE_OFF, STATE_RECONNECTING)
        checks["engine_state"] = state_ok
        if not state_ok:
            all_pass = False
            blocking.append(f"Engine state is {self._state}")

        # 3. Instrument subscribed
        sf = self._freshness.get(symbol)
        subscribed = sf is not None and sf.last_tick_receipt is not None
        checks["instrument_subscribed"] = subscribed
        if not subscribed:
            all_pass = False
            blocking.append(f"No live tick has been received for {symbol}")

        # 4. Tick freshness
        if sf:
            tick_ok = sf.tick_freshness not in (FRESHNESS_STALE, FRESHNESS_DISCONNECTED)
            checks["tick_freshness"] = tick_ok
            if not tick_ok:
                all_pass = False
                blocking.append(f"Tick data is {sf.tick_freshness} for {symbol}")

            # 5. Candle continuity
            checks["candle_gap"] = not sf.gap_detected
            if sf.gap_detected:
                all_pass = False
                blocking.append(f"Candle gap detected for {symbol}")

            # 6. Indicator freshness
            ind_ok = sf.indicator_freshness not in (FRESHNESS_STALE, FRESHNESS_DISCONNECTED)
            checks["indicator_freshness"] = ind_ok
            if not ind_ok:
                all_pass = False
                blocking.append(f"Indicator data is {sf.indicator_freshness} for {symbol}")

            # 7. Regime freshness
            reg_ok = sf.regime_freshness not in (FRESHNESS_STALE, FRESHNESS_DISCONNECTED)
            checks["regime_freshness"] = reg_ok
            if not reg_ok:
                all_pass = False
                blocking.append(f"Regime data is {sf.regime_freshness} for {symbol}")

            # 8. AI decision freshness
            ai_ok = sf.ai_freshness not in (FRESHNESS_STALE, FRESHNESS_DISCONNECTED)
            checks["ai_freshness"] = ai_ok
            if not ai_ok:
                all_pass = False
                blocking.append(f"AI decision is {sf.ai_freshness} for {symbol}")

        # 9. Market open
        checks["market_open"] = self._market_open
        if not self._market_open:
            all_pass = False
            blocking.append("Market is closed")

        checks["all_pass"] = all_pass
        checks["blocking_reasons"] = blocking
        return checks

    # ── Quote reconciliation ──

    async def reconcile_quote(self, symbol: str, latest_ws_price: float) -> dict[str, Any]:
        """
        Compare WebSocket LTP with REST quote. Returns reconciliation result.
        Used before order submission as a safety check.
        """
        await self._publish_event(QUOTE_RECONCILIATION_TRIGGERED, {"symbol": symbol})

        if not self._kite_provider or not self._kite_provider.market_data.is_ready:
            return {"passed": False, "reason": "Kite market data not ready"}

        try:
            quote = await self._kite_provider.market_data.fetch_quote(symbol)
            if not quote:
                return {"passed": False, "reason": "No REST quote available"}

            rest_ltp = quote.get("last_price")
            if rest_ltp is None or rest_ltp <= 0:
                return {"passed": False, "reason": "Invalid REST quote LTP"}

            diff_pct = abs(rest_ltp - latest_ws_price) / max(rest_ltp, 0.01) * 100
            passed = diff_pct <= QUOTE_RECONCILE_THRESHOLD_PCT

            # Update freshness
            sf = self._freshness.get(symbol)
            if sf:
                sf.last_quote_reconciliation = _now_str()

            if passed:
                await self._publish_event(QUOTE_RECONCILIATION_PASSED, {
                    "symbol": symbol,
                    "ws_ltp": latest_ws_price,
                    "rest_ltp": rest_ltp,
                    "diff_pct": round(diff_pct, 2),
                })
            else:
                await self._publish_event(QUOTE_RECONCILIATION_FAILED, {
                    "symbol": symbol,
                    "ws_ltp": latest_ws_price,
                    "rest_ltp": rest_ltp,
                    "diff_pct": round(diff_pct, 2),
                })

            return {
                "passed": passed,
                "ws_ltp": latest_ws_price,
                "rest_ltp": rest_ltp,
                "diff_pct": round(diff_pct, 2),
                "threshold_pct": QUOTE_RECONCILE_THRESHOLD_PCT,
            }

        except Exception as e:
            log_warn("Quote reconciliation failed", symbol=symbol, error=str(e))
            await self._publish_event(QUOTE_RECONCILIATION_FAILED, {
                "symbol": symbol,
                "error": str(e),
            })
            return {"passed": False, "reason": str(e)}

    # ── Reconnection handling ──

    async def _handle_disconnect(self):
        """Handle WebSocket disconnection."""
        self._ws_connected = False
        self._set_state(STATE_DISCONNECTED)

        # Mark all symbols as disconnected
        for sym in list_canonical_names():
            self._freshness.mark_disconnected(sym)

        await self._publish_event(KITE_WS_DISCONNECTED, {
            "subscribed_tokens": len(self._subscribed_tokens),
        })
        log_warn("ZerodhaMarketDataEngine: WebSocket disconnected")

    async def _attempt_reconnect(self) -> bool:
        """Attempt to reconnect the WebSocket."""
        self._set_state(STATE_RECONNECTING)
        await self._publish_event(RECONNECTION_STARTED, {})

        for attempt in range(RECONNECT_MAX_ATTEMPTS):
            if not self._running:
                return False

            log_info("ZerodhaMarketDataEngine: reconnection attempt", attempt=attempt + 1)
            await self._publish_event(KITE_WS_RECONNECTING, {"attempt": attempt + 1})

            try:
                if self._ws_client:
                    self._ws_client.disconnect()

                ws_api_key = os.getenv("KITE_API_KEY", "")
                kite = self._kite_provider.auth.kite if self._kite_provider else None
                ws_token = kite.access_token if kite else os.getenv("KITE_ACCESS_TOKEN", "")
                self._ws_client = KiteWebSocketClient(
                    api_key=ws_api_key,
                    access_token=ws_token,
                    tick_callback=self._on_incoming_tick,
                )
                await self._ws_client.connect()
                self._ws_connected = True

                # Restore subscriptions
                if self._subscribed_tokens:
                    for i in range(0, len(self._subscribed_tokens), SUBSCRIBE_BATCH_SIZE):
                        batch = self._subscribed_tokens[i:i + SUBSCRIBE_BATCH_SIZE]
                        self._ws_client.subscribe(batch)

                await self._publish_event(RECONNECTION_COMPLETED, {
                    "attempts": attempt + 1,
                    "subscribed_tokens": len(self._subscribed_tokens),
                })
                await self._publish_event(KITE_WS_CONNECTED, {})

                self._stats["total_reconnects"] += 1
                self._set_state(STATE_CONNECTED)
                log_info("ZerodhaMarketDataEngine: reconnected", attempts=attempt + 1)
                return True

            except Exception as e:
                log_warn("Reconnect attempt failed", attempt=attempt + 1, error=str(e))
                await asyncio.sleep(1.0 * (2 ** min(attempt, 4)))  # exponential backoff, max 16s

        # Max attempts exceeded
        self._set_state(STATE_ERROR)
        await self._publish_event(RECONNECTION_FAILED, {"max_attempts": RECONNECT_MAX_ATTEMPTS})
        await self._publish_event(KITE_WS_NORECONNECT, {})
        log_error("ZerodhaMarketDataEngine: max reconnection attempts exceeded")
        return False

    # ── Background loops ──

    async def _health_check_loop(self):
        """Periodic health check on the WebSocket connection."""
        while self._running:
            await asyncio.sleep(WS_HEALTH_CHECK_INTERVAL)

            try:
                if self._ws_client:
                    is_connected = self._ws_client.is_connected()
                    if not is_connected and self._ws_connected:
                        # Unexpected disconnect
                        await self._handle_disconnect()
                        asyncio.ensure_future(self._attempt_reconnect())
                    elif is_connected and not self._ws_connected:
                        self._ws_connected = True
                        await self._publish_event(KITE_WS_CONNECTED, {})
            except Exception as e:
                log_warn("Health check error", error=str(e))

    async def _freshness_loop(self):
        """Periodic freshness recomputation."""
        while self._running:
            await asyncio.sleep(FRESHNESS_REFRESH_INTERVAL)
            try:
                self._freshness.refresh_all()

                # Check for stale data state transitions
                for sym in list_canonical_names():
                    sf = self._freshness.get(sym)
                    if sf and sf.tick_freshness == FRESHNESS_STALE:
                        await self._publish_event(MARKET_DATA_STALE, {
                            "symbol": sym,
                            "tick_freshness": sf.tick_freshness,
                        })
            except Exception as e:
                log_warn("Freshness loop error", error=str(e))

    # ── State management ──

    def _set_state(self, state: EngineState):
        old = self._state
        self._state = state
        if old != state:
            log_info("ZerodhaMarketDataEngine state", from_state=old, to_state=state)
        # Update readiness flags in sync with state transitions
        self._refresh_readiness()

    def _refresh_readiness(self):
        """Derive all readiness flags from current state, freshness, and WS status."""
        self._readiness["authenticated"] = bool(
            self._kite_provider and self._kite_provider.auth.is_authenticated
        )
        self._readiness["websocket_connected"] = self._ws_connected
        self._readiness["subscriptions_active"] = len(self._subscribed_tokens) > 0
        self._readiness["historical_ready"] = bool(
            self._state not in (STATE_OFF, STATE_AUTHENTICATING, STATE_LOADING_INSTRUMENTS,
                                 STATE_LOADING_HISTORY, STATE_SUBSCRIBING, STATE_BLOCKED, STATE_ERROR)
        )
        self._readiness["indicators_ready"] = self._state in (
            STATE_CONNECTED, STATE_WAITING_FOR_LIVE_TICKS, STATE_RECEIVING_LIVE_TICKS,
            STATE_DATA_READY, STATE_SCANNING,
        )
        self._readiness["receiving_live_ticks"] = self._state in (
            STATE_RECEIVING_LIVE_TICKS, STATE_DATA_READY, STATE_SCANNING,
        )
        self._readiness["data_fresh"] = self._state in (STATE_DATA_READY, STATE_SCANNING)
        self._readiness["analysis_ready"] = self._state == STATE_SCANNING
        self._readiness["execution_ready"] = False  # Controlled by LiveExecutionGate

    def get_readiness(self) -> dict[str, bool]:
        """Return all separate readiness flags."""
        self._refresh_readiness()
        return dict(self._readiness)

    # ── Status ──

    def get_status(self) -> dict[str, Any]:
        """Comprehensive engine status for API responses."""
        return {
            "provider": {
                "name": "ZERODHA_KITE",
                "authenticated": self._kite_provider.auth.is_authenticated if self._kite_provider else False,
                "user_id": self._kite_provider.auth.user_id if self._kite_provider else "",
            },
            "websocket": {
                "status": self._state,
                "connected": self._ws_connected,
                "subscribed_tokens": len(self._subscribed_tokens),
                "ticks_received": self._stats["total_ticks_received"],
                "last_tick_time": self._stats["last_tick_time"],
                "last_tick_symbol": self._stats["last_tick_symbol"],
                "total_reconnects": self._stats["total_reconnects"],
            },
            "instruments": {
                "mapped": len(self._token_to_symbol),
                "subscribed": len(self._subscribed_tokens),
            },
            "freshness": self._freshness.get_status_summary(),
            "state": self._state,
            "running": self._running,
            "market_open": self._market_open,
            "age_seconds": _age_seconds(self._stats.get("start_time")),
            "readiness": self.get_readiness(),
        }

    def get_freshness_detail(self) -> dict[str, Any]:
        """Per-symbol freshness details."""
        return self._freshness.all_freshness()

    def get_data_freshness_status(self, symbol: str) -> dict[str, Any] | None:
        """Get freshness status for a specific symbol."""
        sf = self._freshness.get(symbol)
        if not sf:
            return None
        return sf.to_dict()

    # ── Events ──

    async def _publish_event(self, event_type: str, payload: dict):
        if not self._event_bus:
            return
        try:
            event = Event(type=event_type, source="zerodha_market_data_engine", payload=payload)
            await self._event_bus.publish(event)
            self._stats["total_events_published"] += 1
        except Exception as e:
            log_warn("Event publish error", event_type=event_type, error=str(e))


def _now_str() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _age_seconds(start_str: str | None) -> float:
    if not start_str:
        return 0.0
    try:
        start = datetime.fromisoformat(start_str)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - start).total_seconds()
    except (ValueError, TypeError):
        return 0.0
