"""
MarketMind AI — Event Registry

A static catalog of every known event type in the system.
This is NOT the runtime registry of active subscribers — that lives in EventBus.

Purpose:
  - Single source of truth for event type documentation
  - Maps event type strings to human-readable descriptions
  - Can be used by future modules to discover available events
  - Can validate event types at publish/subscribe time

All event type strings are defined in core.events — this registry adds
metadata on top of those definitions.
"""

from dataclasses import dataclass, field
from typing import Any

from core.events import *  # import all event type constants


@dataclass
class EventTypeInfo:
    """Metadata for a single event type."""

    type_key: str
    description: str
    category: str = "general"
    schema_hint: dict[str, Any] = field(default_factory=dict)


# ── Registry: built once on import ──

_EVENT_REGISTRY: dict[str, EventTypeInfo] = {
    # ── Candle & Price ──
    NEW_CANDLE: EventTypeInfo(
        NEW_CANDLE,
        "A new candle has closed for a given interval/symbol",
        category="market_data",
        schema_hint={
            "symbol": "str",
            "interval": "str",
            "open": "float",
            "high": "float",
            "low": "float",
            "close": "float",
            "volume": "float",
            "time": "str",
        },
    ),
    PRICE_UPDATE: EventTypeInfo(
        PRICE_UPDATE,
        "Real-time price tick update (future use)",
        category="market_data",
    ),
    VWAP_CROSS: EventTypeInfo(
        VWAP_CROSS,
        "Price crossed above or below VWAP",
        category="indicator",
    ),
    EMA_CROSS: EventTypeInfo(
        EMA_CROSS,
        "EMA crossover event (e.g. 9-period crossed 21-period)",
        category="indicator",
    ),
    # ── Indicator Events ──
    RSI_SIGNAL: EventTypeInfo(
        RSI_SIGNAL,
        "RSI crossed a threshold (overbought >70, oversold <30)",
        category="indicator",
    ),
    MACD_SIGNAL: EventTypeInfo(
        MACD_SIGNAL,
        "MACD line crossed above/below signal line",
        category="indicator",
    ),
    ATR_EXPANSION: EventTypeInfo(
        ATR_EXPANSION,
        "ATR expanded beyond a configured threshold",
        category="indicator",
    ),
    BOLLINGER_TOUCH: EventTypeInfo(
        BOLLINGER_TOUCH,
        "Price touched or exceeded the outer Bollinger Band",
        category="indicator",
    ),
    # ── Pattern Events ──
    PATTERN_DETECTED: EventTypeInfo(
        PATTERN_DETECTED,
        "A generic candlestick or chart pattern was detected",
        category="pattern",
    ),
    BREAKOUT: EventTypeInfo(
        BREAKOUT,
        "Price broke above a resistance level",
        category="pattern",
    ),
    BREAKDOWN: EventTypeInfo(
        BREAKDOWN,
        "Price broke below a support level",
        category="pattern",
    ),
    FAKE_BREAKOUT: EventTypeInfo(
        FAKE_BREAKOUT,
        "Price briefly broke a level then reversed — false breakout",
        category="pattern",
    ),
    RETEST: EventTypeInfo(
        RETEST,
        "Price returned to a previously broken level to test it",
        category="pattern",
    ),
    PULLBACK: EventTypeInfo(
        PULLBACK,
        "Price pulled back within the prevailing trend",
        category="pattern",
    ),
    # ── Structure Events ──
    SWING_HIGH: EventTypeInfo(
        SWING_HIGH,
        "A new swing high was formed in price action",
        category="structure",
    ),
    SWING_LOW: EventTypeInfo(
        SWING_LOW,
        "A new swing low was formed in price action",
        category="structure",
    ),
    TREND_CHANGED: EventTypeInfo(
        TREND_CHANGED,
        "The trend direction changed (e.g. HH/HL pattern broke)",
        category="structure",
    ),
    SUPPLY_ZONE: EventTypeInfo(
        SUPPLY_ZONE,
        "Price entered a supply (resistance) zone",
        category="structure",
    ),
    DEMAND_ZONE: EventTypeInfo(
        DEMAND_ZONE,
        "Price entered a demand (support) zone",
        category="structure",
    ),
    # ── Volume Events ──
    VOLUME_SPIKE: EventTypeInfo(
        VOLUME_SPIKE,
        "Volume exceeded the configured threshold above the rolling average",
        category="volume",
    ),
    LOW_VOLUME_TRAP: EventTypeInfo(
        LOW_VOLUME_TRAP,
        "A price move on significantly low volume — potentially a trap",
        category="volume",
    ),
    # ── Signal Events (future) ──
    SIGNAL_CREATED: EventTypeInfo(
        SIGNAL_CREATED,
        "A new trade signal was created by the AI engine",
        category="signal",
    ),
    SIGNAL_UPDATED: EventTypeInfo(
        SIGNAL_UPDATED,
        "An existing signal's state or confidence changed",
        category="signal",
    ),
    SIGNAL_CANCELLED: EventTypeInfo(
        SIGNAL_CANCELLED,
        "A signal was invalidated and cancelled",
        category="signal",
    ),
    SIGNAL_TARGET_HIT: EventTypeInfo(
        SIGNAL_TARGET_HIT,
        "A signal's price target was reached",
        category="signal",
    ),
    SIGNAL_STOP_HIT: EventTypeInfo(
        SIGNAL_STOP_HIT,
        "A signal's stop loss was triggered",
        category="signal",
    ),
    # ── AI Decision Events (future) ──
    AI_DECISION: EventTypeInfo(
        AI_DECISION,
        "The AI engine produced a BUY or SELL decision",
        category="ai",
    ),
    AI_WAIT: EventTypeInfo(
        AI_WAIT,
        "The AI engine decided to wait (not enough confluence)",
        category="ai",
    ),
    AI_NO_TRADE: EventTypeInfo(
        AI_NO_TRADE,
        "The AI engine rejected the setup (validation failed)",
        category="ai",
    ),
    # ── Market Events ──
    MARKET_OPEN: EventTypeInfo(
        MARKET_OPEN,
        "The market opened for trading",
        category="market",
    ),
    MARKET_CLOSE: EventTypeInfo(
        MARKET_CLOSE,
        "The market closed for trading",
        category="market",
    ),
    NEW_SESSION: EventTypeInfo(
        NEW_SESSION,
        "The market session phase changed (e.g. Opening → Mid)",
        category="market",
    ),
}


def get_event_info(event_type: str) -> EventTypeInfo | None:
    """Look up metadata for an event type. Returns None if unknown."""
    return _EVENT_REGISTRY.get(event_type)


def is_valid_event_type(event_type: str) -> bool:
    """Check if an event type string is registered."""
    return event_type in _EVENT_REGISTRY


def list_event_types() -> list[str]:
    """Return all registered event type keys."""
    return list(_EVENT_REGISTRY.keys())


def list_events_by_category(category: str) -> list[EventTypeInfo]:
    """Return all event types in a given category."""
    return [info for info in _EVENT_REGISTRY.values() if info.category == category]
