"""
Market Data Subscription Manager

Centralized manager for Zerodha Kite WebSocket subscriptions.
Tracks which symbols are required by which consumers,
deduplicates subscriptions, and handles reconnect recovery.

Usage:
    manager = MarketSubscriptionManager(kite_ws_client)
    manager.subscribe("candle_engine", ["NIFTY 50", "BANKNIFTY"])
    manager.subscribe("live_control", ["NIFTY 50"])
    # Only one Kite subscription for NIFTY 50 despite two consumers
    manager.unsubscribe("candle_engine", ["BANKNIFTY"])
"""

from __future__ import annotations

from typing import Any

from utils.logger import log_info, log_warn


class MarketSubscriptionManager:
    """
    Manages Zerodha WebSocket subscriptions with reference counting.

    Multiple internal consumers can request the same symbol without
    creating duplicate broker subscriptions.
    """

    def __init__(self, kite_ws=None, instrument_manager=None):
        self._kite_ws = kite_ws
        self._instrument_manager = instrument_manager
        # consumer_name -> set of symbols
        self._consumer_symbols: dict[str, set[str]] = {}
        # symbol -> reference count
        self._symbol_refs: dict[str, int] = {}
        # symbol -> instrument_token
        self._token_cache: dict[str, int] = {}

    def set_kite_ws(self, ws):
        self._kite_ws = ws

    def set_instrument_manager(self, mgr):
        self._instrument_manager = mgr

    # ── Subscription management ──

    def subscribe(self, consumer: str, symbols: list[str]) -> list[str]:
        """
        Subscribe a consumer to symbols. Returns newly subscribed symbols.
        """
        if consumer not in self._consumer_symbols:
            self._consumer_symbols[consumer] = set()

        new_subs = []
        for sym in symbols:
            if sym not in self._consumer_symbols[consumer]:
                self._consumer_symbols[consumer].add(sym)
                prev = self._symbol_refs.get(sym, 0)
                self._symbol_refs[sym] = prev + 1
                if prev == 0:
                    # First reference — need broker subscription
                    new_subs.append(sym)

        if new_subs and self._kite_ws:
            self._broker_subscribe(new_subs)

        return new_subs

    def unsubscribe(self, consumer: str, symbols: list[str] | None = None) -> list[str]:
        """
        Unsubscribe a consumer from symbols. Returns symbols that were freed.
        """
        if consumer not in self._consumer_symbols:
            return []

        if symbols is None:
            symbols = list(self._consumer_symbols[consumer])

        freed = []
        for sym in symbols:
            self._consumer_symbols[consumer].discard(sym)
            prev = self._symbol_refs.get(sym, 0)
            if prev <= 1:
                self._symbol_refs.pop(sym, None)
                freed.append(sym)
            else:
                self._symbol_refs[sym] = prev - 1

        if freed and self._kite_ws:
            self._broker_unsubscribe(freed)

        return freed

    def get_consumers_for_symbol(self, symbol: str) -> list[str]:
        """Get all consumers subscribed to a symbol."""
        return [
            name
            for name, syms in self._consumer_symbols.items()
            if symbol in syms
        ]

    def get_all_subscribed_symbols(self) -> list[str]:
        """Get all currently subscribed symbols."""
        return list(self._symbol_refs.keys())

    def get_consumer_symbols(self, consumer: str) -> list[str]:
        """Get symbols for a specific consumer."""
        return list(self._consumer_symbols.get(consumer, set()))

    def consumer_count(self) -> int:
        return len(self._consumer_symbols)

    # ── Broker integration ──

    def _broker_subscribe(self, symbols: list[str]):
        """Subscribe to symbols on the Kite WebSocket."""
        tokens = []
        for sym in symbols:
            token = self._resolve_token(sym)
            if token:
                tokens.append(token)
        if tokens and self._kite_ws:
            try:
                self._kite_ws.subscribe(tokens)
                log_info("MarketSub: subscribed to broker", symbols=symbols, tokens=len(tokens))
            except Exception as e:
                log_warn("MarketSub: broker subscribe failed", error=str(e))

    def _broker_unsubscribe(self, symbols: list[str]):
        """Unsubscribe from symbols on the Kite WebSocket."""
        tokens = []
        for sym in symbols:
            token = self._token_cache.get(sym)
            if token:
                tokens.append(token)
        if tokens and self._kite_ws:
            try:
                self._kite_ws.unsubscribe(tokens)
                log_info("MarketSub: unsubscribed from broker", symbols=symbols)
            except Exception as e:
                log_warn("MarketSub: broker unsubscribe failed", error=str(e))

    def _resolve_token(self, symbol: str) -> int | None:
        """Resolve a symbol to an instrument token."""
        if symbol in self._token_cache:
            return self._token_cache[symbol]
        if self._instrument_manager:
            token = self._instrument_manager.map_to_kite_token(symbol)
            if token:
                self._token_cache[symbol] = token
                return token
        return None

    # ── Reconnect recovery ──

    def on_reconnect(self):
        """Resubscribe all symbols after broker WebSocket reconnection."""
        if not self._kite_ws:
            return
        symbols = self.get_all_subscribed_symbols()
        if symbols:
            self._broker_subscribe(symbols)
            log_info("MarketSub: resubscribed all symbols after reconnect", count=len(symbols))

    def restore_consumer(self, consumer: str, symbols: list[str]):
        """Restore a consumer's subscriptions (e.g. after backend restart)."""
        self._consumer_symbols[consumer] = set(symbols)
        for sym in symbols:
            self._symbol_refs[sym] = self._symbol_refs.get(sym, 0) + 1
        # Don't re-subscribe on restore — broker state is handled separately

    # ── Stats ──

    def get_stats(self) -> dict[str, Any]:
        return {
            "consumers": len(self._consumer_symbols),
            "unique_symbols": len(self._symbol_refs),
            "subscribed_symbols": self.get_all_subscribed_symbols(),
            "consumer_details": {
                name: list(syms)
                for name, syms in self._consumer_symbols.items()
            },
        }


# Singleton
_instance: MarketSubscriptionManager | None = None


def get_subscription_manager() -> MarketSubscriptionManager:
    assert _instance is not None, "MarketSubscriptionManager not initialized"
    return _instance


def init_subscription_manager(kite_ws=None, instrument_manager=None) -> MarketSubscriptionManager:
    global _instance
    _instance = MarketSubscriptionManager(kite_ws, instrument_manager)
    return _instance
