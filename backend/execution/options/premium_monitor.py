"""
Option Premium Monitor — routes live premium ticks from WebSocket/KiteTicker
to PaperBroker by instrument_token.

Maintains canonical separation:
- Underlying ticks → CandleEngine, market analysis
- Option premium ticks → open PaperPosition P&L, SL/target monitoring

Uses instrument_token, execution_symbol, and trade_id as authoritative
option-position identifiers — NOT the underlying symbol.
"""

from __future__ import annotations

from typing import Any, Callable

from utils.logger import log_info, log_warn, log_error


class PremiumTickRouter:
    """
    Routes option premium ticks to the correct PaperBroker position.

    Maintains a token → trade_id mapping, supports reference-counted
    subscriptions for tokens shared across multiple positions.
    """

    def __init__(self):
        # token -> list of trade_ids
        self._token_positions: dict[int, list[str]] = {}
        # trade_id -> token
        self._position_tokens: dict[str, int] = {}
        # token -> reference count
        self._token_refs: dict[int, int] = {}
        # Callback: fn(trade_id, premium, token, timestamp)
        self._premium_callback: Callable[[str, float, int, str], None] | None = None

    def set_premium_callback(self, callback: Callable[[str, float, int, str], None]):
        """Set the callback invoked when a premium tick arrives."""
        self._premium_callback = callback

    def register_position(self, trade_id: str, instrument_token: int) -> bool:
        """
        Register a position's option instrument token.

        Returns True if this is a new token that needs subscription.
        """
        if instrument_token <= 0:
            log_warn("PremiumTickRouter: invalid instrument_token", trade_id=trade_id)
            return False

        self._position_tokens[trade_id] = instrument_token

        if instrument_token not in self._token_positions:
            self._token_positions[instrument_token] = []
            self._token_refs[instrument_token] = 0

        if trade_id not in self._token_positions[instrument_token]:
            self._token_positions[instrument_token].append(trade_id)

        prev = self._token_refs.get(instrument_token, 0)
        self._token_refs[instrument_token] = prev + 1
        is_first = (prev == 0)

        log_info("PremiumTickRouter: registered",
                 trade_id=trade_id, token=instrument_token,
                 is_first_subscription=is_first)
        return is_first

    def unregister_position(self, trade_id: str) -> int | None:
        """
        Unregister a position. Returns the token if it should be unsubscribed
        (no more positions reference it), or None if other positions still need it.
        """
        token = self._position_tokens.pop(trade_id, None)
        if token is None or token == 0:
            return None

        if token in self._token_positions:
            self._token_positions[token] = [
                t for t in self._token_positions[token] if t != trade_id
            ]

        prev = self._token_refs.get(token, 0)
        if prev <= 1:
            self._token_refs.pop(token, None)
            self._token_positions.pop(token, None)
            log_info("PremiumTickRouter: unregistered (last consumer)",
                     trade_id=trade_id, token=token)
            return token
        else:
            self._token_refs[token] = prev - 1
            log_info("PremiumTickRouter: unregistered (ref count)",
                     trade_id=trade_id, token=token, remaining_refs=prev - 1)
            return None

    def route_tick(self, instrument_token: int, premium: float, timestamp: str | None = None) -> list[str]:
        """
        Route a premium tick to all positions registered for this token.

        Returns list of trade_ids that were updated.
        """
        import datetime
        ts = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()

        if premium <= 0:
            return []

        trade_ids = self._token_positions.get(instrument_token, [])
        if not trade_ids:
            return []

        if self._premium_callback:
            for tid in trade_ids:
                try:
                    self._premium_callback(tid, premium, instrument_token, ts)
                except Exception as e:
                    log_error("PremiumTickRouter: callback failed",
                              trade_id=tid, error=str(e))

        return trade_ids

    def get_token_for_position(self, trade_id: str) -> int:
        """Get the instrument token registered for a position."""
        return self._position_tokens.get(trade_id, 0)

    def get_positions_for_token(self, token: int) -> list[str]:
        """Get all trade_ids registered for a token."""
        return self._token_positions.get(token, [])

    def get_all_tokens(self) -> list[int]:
        """Get all unique tokens with active positions."""
        return list(self._token_positions.keys())

    def position_count(self) -> int:
        return len(self._position_tokens)

    def reset(self):
        self._token_positions.clear()
        self._position_tokens.clear()
        self._token_refs.clear()


# Singleton
_router_instance: PremiumTickRouter | None = None


def get_premium_tick_router() -> PremiumTickRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = PremiumTickRouter()
    return _router_instance


def reset_premium_tick_router():
    global _router_instance
    _router_instance = None
