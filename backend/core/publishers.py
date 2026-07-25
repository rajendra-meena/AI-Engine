"""
MarketMind AI — Publisher Helpers

Convenience functions for publishing common event types.
Future modules should use these instead of constructing Event objects manually.

Each function enriches the event with the caller's module name as the source
and sensible default priority for the event type.

Usage:
    from core.publishers import publish_candle_closed
    await publish_candle_closed(bus, symbol="NIFTY 50", interval="15m", ...)
"""

from core.event_model import Event, EventPriority
from core.event_bus import EventBus
from core.events import *


async def publish_candle_closed(
    bus: EventBus,
    symbol: str,
    interval: str,
    open: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    time: str,
    **extra,
) -> bool:
    """Publish a NEW_CANDLE event when a candle closes."""
    return await bus.publish(
        Event(
            type=NEW_CANDLE,
            source="candle_builder",
            priority=EventPriority.HIGH,
            payload={
                "symbol": symbol,
                "interval": interval,
                "open": open,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "time": time,
                **extra,
            },
        )
    )


async def publish_price_update(
    bus: EventBus, symbol: str, price: float, volume: float = 0
) -> bool:
    """Publish a PRICE_UPDATE event (future use with live ticks)."""
    return await bus.publish(
        Event(
            type=PRICE_UPDATE,
            source="tick_provider",
            priority=EventPriority.NORMAL,
            payload={"symbol": symbol, "price": price, "volume": volume},
        )
    )


async def publish_breakout(
    bus: EventBus,
    symbol: str,
    direction: str,
    level: float,
    reason: str,
    **extra,
) -> bool:
    """Publish a BREAKOUT or BREAKDOWN event."""
    event_type = BREAKOUT if direction.upper() == "BULLISH" else BREAKDOWN
    return await bus.publish(
        Event(
            type=event_type,
            source="pattern_engine",
            priority=EventPriority.HIGH,
            payload={
                "symbol": symbol,
                "direction": direction,
                "level": level,
                "reason": reason,
                **extra,
            },
        )
    )


async def publish_market_state(bus: EventBus, state: str) -> bool:
    """Publish MARKET_OPEN, MARKET_CLOSE, or NEW_SESSION event."""
    event_map = {
        "open": MARKET_OPEN,
        "close": MARKET_CLOSE,
        "session": NEW_SESSION,
    }
    event_type = event_map.get(state.lower(), NEW_SESSION)
    return await bus.publish(
        Event(
            type=event_type,
            source="market_calendar",
            priority=EventPriority.NORMAL,
            payload={"state": state},
        )
    )


async def publish_indicator_event(
    bus: EventBus,
    event_type: str,
    symbol: str,
    indicator: str,
    value: float,
    **extra,
) -> bool:
    """Publish a generic indicator event (RSI_SIGNAL, MACD_SIGNAL, VWAP_CROSS, etc.)."""
    return await bus.publish(
        Event(
            type=event_type,
            source="indicator_engine",
            priority=EventPriority.NORMAL,
            payload={
                "symbol": symbol,
                "indicator": indicator,
                "value": value,
                **extra,
            },
        )
    )


async def publish_signal_event(
    bus: EventBus,
    event_type: str,
    signal_id: str,
    symbol: str,
    direction: str,
    confidence: float,
    **extra,
) -> bool:
    """Publish a signal lifecycle event (SIGNAL_CREATED, SIGNAL_UPDATED, etc.)."""
    return await bus.publish(
        Event(
            type=event_type,
            source="signal_engine",
            priority=EventPriority.HIGH,
            payload={
                "signal_id": signal_id,
                "symbol": symbol,
                "direction": direction,
                "confidence": confidence,
                **extra,
            },
        )
    )
