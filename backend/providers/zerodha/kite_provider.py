"""
Zerodha Kite Connect — Market Data Provider

Implements the BaseProvider interface for Zerodha Kite Connect.
Sits alongside YahooProvider and is interchangeable via ProviderFactory.

Architecture:
    KiteProvider (implements BaseProvider)
        ├── KiteAuthentication  → OAuth flow, session management
        ├── KiteMarketData      → REST API data fetching
        ├── KiteWebSocketClient → Real-time tick streaming
        ├── InstrumentManager   → Instrument master download + search
        ├── OrderManager        → Order placement + management
        └── TokenManager        → Secure token storage
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Any

from data.base_provider import BaseProvider, ProviderCapabilities
from data.provider_types import (
    ProviderType,
    ProviderStatus,
    ProviderHealth,
    DailyOHLC,
    IntradayCandle,
    DailyReferenceLevels,
)
from data.exceptions import ProviderUnavailable

from providers.zerodha.authentication import KiteAuthentication, KiteAuthError
from providers.zerodha.market_data import KiteMarketData
from providers.zerodha.websocket import KiteWebSocketClient
from providers.zerodha.instrument_manager import InstrumentManager
from providers.zerodha.order_manager import OrderManager
from providers.zerodha.token_manager import TokenManager

from core.symbols import list_display_names, list_canonical_names
from core.intervals import INTERVAL_KEYS
from models.tick import Tick
from utils.logger import log_info, log_warn, log_error


class KiteProvider(BaseProvider):
    """
    Market data provider for Zerodha Kite Connect.

    Provides both REST API data (historical) and WebSocket streaming (real-time).
    Implements the full BaseProvider interface so it's a drop-in replacement
    for YahooProvider in all services.
    """

    def __init__(self):
        self._name = "zerodha"
        self._connected = False
        self._last_success: datetime | None = None

        # Sub-modules
        self.auth = KiteAuthentication()
        self.token_manager = TokenManager()
        self.instruments = InstrumentManager()
        self.market_data = KiteMarketData()
        self.orders = OrderManager()
        self.ws_client: KiteWebSocketClient | None = None

        # Restore persisted token from file if not already authenticated
        # (env var KITE_ACCESS_TOKEN takes priority; file is fallback)
        if not self.auth.is_authenticated:
            stored = self.token_manager.load_token_from_file()
            if stored:
                self.auth.restore_token(stored, self.token_manager.user_id)

        # Token-to-symbol mapping (set during instrument loading)
        self._token_map: dict[int, str] = {}

        # Tick callback (set by the engine that owns this provider)
        self._tick_callback: callable | None = None
        self._reconnect_task: asyncio.Task | None = None

    # ── Lifecycle ──

    async def connect(self) -> bool:
        """Establish connection to Zerodha Kite Connect."""
        try:
            # Try to restore token from env or file
            if not self.auth.is_authenticated:
                stored_token = self.token_manager.load_token_from_file()
                if stored_token:
                    # Re-init auth with stored token
                    pass  # Token is already loaded

            if not self.auth.is_authenticated:
                log_warn("KiteProvider: not authenticated, cannot connect")
                return False

            # Connect sub-modules
            kite = self.auth.kite
            if kite is None:
                return False

            self.market_data.set_kite(kite)
            self.orders.set_kite(kite)
            self.instruments.set_kite(kite)

            # Load instrument master
            await self.instruments.load()

            # Build token-to-symbol map
            self._build_token_map()

            self._connected = True
            self._last_success = datetime.now(timezone.utc)
            log_info("KiteProvider connected", user_id=self.auth.user_id)
            return True

        except Exception as e:
            log_error("KiteProvider: connection failed", error=str(e))
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from Kite and clean up resources."""
        # Stop WebSocket
        if self.ws_client:
            try:
                self.ws_client.disconnect()
            except Exception:
                pass
            self.ws_client = None

        # Cancel reconnect task
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()

        self._connected = False
        log_info("KiteProvider disconnected")

    # ── WebSocket tick streaming ──

    def set_tick_callback(self, callback: callable):
        """Set the callback for incoming ticks (called by TickEngine)."""
        self._tick_callback = callback

    async def start_websocket(self, tokens: list[int] | None = None):
        """
        Start the Kite WebSocket for real-time ticks.

        Args:
            tokens: Optional list of instrument tokens to subscribe.
                    If None, subscribes to all known index tokens.
        """
        if not self.auth.is_authenticated or not self.auth.kite:
            log_warn("KiteProvider: cannot start WebSocket, not authenticated")
            return False

        try:
            self.ws_client = KiteWebSocketClient(
                api_key=self.auth.api_key,
                access_token=self.token_manager.access_token or "",
                tick_callback=self._on_kite_tick,
            )
            await self.ws_client.connect()

            # Subscribe to default tokens
            if tokens is None:
                tokens = self._get_default_tokens()
            if tokens:
                self.ws_client.subscribe(tokens)

            log_info("KiteProvider: WebSocket started", tokens=len(tokens))
            return True

        except Exception as e:
            log_error("KiteProvider: WebSocket start failed", error=str(e))
            return False

    def stop_websocket(self):
        """Stop the Kite WebSocket."""
        if self.ws_client:
            self.ws_client.disconnect()
            self.ws_client = None
            log_info("KiteProvider: WebSocket stopped")

    def subscribe_ticks(self, symbols: list[str]):
        """
        Subscribe to real-time ticks for given internal symbols.

        Resolves symbols to instrument tokens and subscribes via WebSocket.
        """
        if not self.ws_client or not self.ws_client.is_connected():
            log_warn("KiteProvider: WebSocket not connected, cannot subscribe")
            return

        tokens = []
        for sym in symbols:
            token = self.instruments.map_to_kite_token(sym)
            if token:
                tokens.append(token)

        if tokens:
            self.ws_client.subscribe(tokens)

    def _on_kite_tick(self, tick: Tick):
        """
        Called by the WebSocket client for each incoming tick.

        Resolves token-based symbol to internal display name before forwarding.
        """
        # Resolve token:XXX to display name
        if tick.symbol.startswith("token:"):
            try:
                token = int(tick.symbol.replace("token:", ""))
                display_name = self._token_map.get(token)
                if display_name:
                    # Create a new Tick with the resolved symbol
                    tick = Tick(
                        symbol=display_name,
                        price=tick.price,
                        timestamp=tick.timestamp,
                        volume=tick.volume,
                        bid=tick.bid,
                        ask=tick.ask,
                        provider="zerodha",
                        exchange=tick.exchange,
                    )
            except (ValueError, TypeError):
                pass

        if self._tick_callback:
            self._tick_callback(tick)

    # ── Token management ──

    def _build_token_map(self):
        """Build the mapping from instrument token to internal display name."""
        self._token_map.clear()
        canonical = list_canonical_names()
        for name in canonical:
            token = self.instruments.map_to_kite_token(name)
            if token:
                self._token_map[token] = name

    def _get_default_tokens(self) -> list[int]:
        """Get instrument tokens for all canonical symbols."""
        tokens = []
        for name in list_canonical_names():
            token = self.instruments.map_to_kite_token(name)
            if token:
                tokens.append(token)
        return tokens

    # ── BaseProvider interface ──

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name=self._name,
            provider_type=ProviderType.BROKER,
            supports_daily=True,
            supports_intraday=True,
            supports_reference_levels=True,
            supports_symbol_discovery=True,
            symbols=list_display_names(),
            intervals=list(INTERVAL_KEYS),
        )

    async def health(self) -> ProviderHealth:
        """Check provider health — authenticated + connected check."""
        if not self.auth.is_authenticated:
            return ProviderHealth(
                status=ProviderStatus.NOT_CONFIGURED,
                provider_name=self._name,
                provider_type=ProviderType.BROKER,
                error_message="Not authenticated. Use /api/kite/login to authenticate.",
            )

        ws_ok = self.ws_client and self.ws_client.is_connected() if True else False

        try:
            # Check by fetching margin (lightweight check)
            if self.auth.kite:
                self.auth.kite.margins()
                self._last_success = datetime.now(timezone.utc)
                return ProviderHealth(
                    status=ProviderStatus.HEALTHY,
                    provider_name=self._name,
                    provider_type=ProviderType.BROKER,
                    last_success=self._last_success,
                    supported_symbols=len(list_display_names()),
                    supported_intervals=len(INTERVAL_KEYS),
                )
        except Exception as e:
            return ProviderHealth(
                status=ProviderStatus.UNAVAILABLE,
                provider_name=self._name,
                provider_type=ProviderType.BROKER,
                error_message=str(e),
            )

        return ProviderHealth(
            status=ProviderStatus.DEGRADED,
            provider_name=self._name,
            provider_type=ProviderType.BROKER,
            error_message="Kite connected but no KiteConnect instance",
        )

    async def validate_symbol(self, symbol: str) -> bool:
        """Check if a symbol is supported by Zerodha."""
        kite_sym = self.instruments.map_to_kite_symbol(symbol)
        if kite_sym:
            return True
        # Fallback: check symbol registry
        from core.symbols import is_valid_symbol
        return is_valid_symbol(symbol)

    async def get_provider_symbol(self, internal_symbol: str) -> str:
        """Convert internal display name to Kite trading symbol."""
        result = self.instruments.map_to_kite_symbol(internal_symbol)
        if result:
            return result
        return internal_symbol

    async def fetch_daily(
        self, symbol: str, start_date: date, end_date: date
    ) -> list[DailyOHLC]:
        return await self.market_data.fetch_daily(symbol, start_date, end_date)

    async def fetch_intraday(
        self, symbol: str, interval: str, days: int
    ) -> list[IntradayCandle]:
        return await self.market_data.fetch_intraday(symbol, interval, days)

    async def fetch_daily_reference_levels(
        self, symbol: str
    ) -> DailyReferenceLevels | None:
        """Compute daily reference levels from Kite daily data."""
        try:
            from datetime import timedelta
            end = date.today()
            start = end - timedelta(days=10)
            dailies = await self.fetch_daily(symbol, start, end)
            if len(dailies) < 2:
                return None

            prev = dailies[-2]
            weekly = dailies[-5:] if len(dailies) >= 5 else dailies
            weekly_high = max(d.high for d in weekly)
            weekly_low = min(d.low for d in weekly)

            return DailyReferenceLevels(
                prev_day_high=prev.high,
                prev_day_low=prev.low,
                prev_day_close=prev.close,
                prev_day_open=prev.open,
                weekly_high=weekly_high,
                weekly_low=weekly_low,
                prev_day_range=round(prev.high - prev.low, 2),
                prev_day_midpoint=round((prev.high + prev.low) / 2, 2),
                prev_day_vwap=round((prev.high + prev.low + prev.close) / 3, 2),
            )
        except Exception as e:
            log_warn("KiteProvider: reference levels failed", symbol=symbol, error=str(e))
            return None

    # ── Auth delegation ──

    def get_login_url(self) -> str:
        """Get Kite login URL for OAuth flow."""
        return self.auth.get_login_url()

    def create_session(self, request_token: str) -> dict[str, Any]:
        """
        Complete Kite OAuth login with request token.

        Args:
            request_token: Token from login redirect URL

        Returns:
            Session info including user_id
        """
        result = self.auth.create_session(request_token)
        if result.get("success"):
            # Save token
            self.token_manager.save_token(
                self.auth.kite.access_token if hasattr(self.auth.kite, "access_token") else "",
                self.auth.user_id,
            )
            # Reconnect with new session
            asyncio.ensure_future(self._reconnect())
        return result

    def logout(self):
        """Logout and clear session."""
        self.auth.logout()
        self.token_manager.clear_token()
        self.stop_websocket()
        self._connected = False

    async def _reconnect(self):
        """Reconnect after new authentication."""
        await self.disconnect()
        await self.connect()

    # ── Order delegation ──

    @property
    def order_manager(self) -> OrderManager:
        return self.orders

    # ── Status ──

    def get_status(self) -> dict[str, Any]:
        """Return comprehensive provider status."""
        ws_stats = self.ws_client.get_stats() if self.ws_client else {}
        return {
            "connected": self._connected,
            "authenticated": self.auth.is_authenticated,
            "user_id": self.auth.user_id,
            "broker": "ZERODHA",
            "exchange": "NSE",
            "instruments_loaded": self.instruments.is_loaded,
            "instruments_count": len(self._token_map),
            "websocket": {
                "connected": ws_stats.get("connected", False),
                "ticks_received": ws_stats.get("ticks_received", 0),
                "subscribed_tokens": ws_stats.get("subscribed_tokens", 0),
                "reconnect_attempts": ws_stats.get("reconnect_attempts", 0),
            },
            "last_success": self._last_success.isoformat() if self._last_success else None,
        }
