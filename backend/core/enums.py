"""
MarketMind AI — Shared Enums

Reusable enumeration types used across the entire application.
All future modules must import from here instead of defining local constants.
"""

from enum import Enum


class Direction(str, Enum):
    """Trade / trend direction."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"


class Bias(str, Enum):
    """Suggested trading bias."""

    BUY = "Buy"
    SELL = "Sell"
    WAIT = "Wait"


class SignalState(str, Enum):
    """Lifecycle state of a trading signal."""

    DETECTED = "DETECTED"
    CONFIRMED = "CONFIRMED"
    TRIGGERED = "TRIGGERED"
    TARGET_HIT = "TARGET_HIT"
    STOP_HIT = "STOP_HIT"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class Outcome(str, Enum):
    """Backtest result outcome."""

    HIT_TARGET = "HIT_TARGET"
    HIT_STOPLOSS = "HIT_STOPLOSS"
    NO_TRADE = "NO_TRADE"
    UNCHECKED = "UNCHECKED"
    PENDING = "PENDING"


class MarketSession(str, Enum):
    """Current market session."""

    PRE_MARKET = "PreMarket"
    OPENING = "Opening"
    MID = "Mid"
    CLOSING = "Closing"
    CLOSED = "Closed"


class TrendDirection(str, Enum):
    """Trend classification."""

    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    RANGING = "RANGING"
    TRANSITION_BULLISH = "TRANSITION_BULLISH"
    TRANSITION_BEARISH = "TRANSITION_BEARISH"


class TrendStrength(str, Enum):
    """Strength of a detected trend."""

    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    WEAKENING = "WEAKENING"


class ConfidenceGrade(str, Enum):
    """Confidence classification."""

    VERY_HIGH = "VERY_HIGH"  # >= 85
    HIGH = "HIGH"  # >= 70
    MODERATE = "MODERATE"  # >= 50
    LOW = "LOW"  # >= 30
    VERY_LOW = "VERY_LOW"  # < 30


class IntervalType(str, Enum):
    """Type of chart interval."""

    INTRADAY = "INTRADAY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class Decision(str, Enum):
    """AI decision output."""

    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"
    NO_TRADE = "NO_TRADE"


class TradeDirection(str, Enum):
    """
    Canonical internal trade direction.

    All backend code must use these values internally.
    Use normalize_direction() at external boundaries.
    """
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"

    @classmethod
    def values(cls) -> list[str]:
        return [m.value for m in cls]


def normalize_direction(value: str | None) -> TradeDirection:
    """
    Normalize legacy direction strings to canonical TradeDirection.

    External boundaries (API, broker adapters, display) convert to/from these.

    BUY       → LONG
    BULLISH   → LONG
    LONG      → LONG

    SELL      → SHORT
    BEARISH   → SHORT
    SHORT     → SHORT

    WAIT      → NONE
    NO_TRADE  → NONE
    NONE      → NONE

    Raises ValueError on unknown values — no silent fallback to NONE.
    """
    if value is None:
        return TradeDirection.NONE

    upper = value.strip().upper()

    mapping: dict[str, TradeDirection] = {
        "BUY": TradeDirection.LONG,
        "BULLISH": TradeDirection.LONG,
        "LONG": TradeDirection.LONG,
        "SELL": TradeDirection.SHORT,
        "BEARISH": TradeDirection.SHORT,
        "SHORT": TradeDirection.SHORT,
        "WAIT": TradeDirection.NONE,
        "NO_TRADE": TradeDirection.NONE,
        "NONE": TradeDirection.NONE,
        "": TradeDirection.NONE,
    }

    if upper in mapping:
        return mapping[upper]

    raise ValueError(
        f"Unknown direction value: '{value}'. "
        f"Valid values: {sorted(set(mapping.keys()) - {'',})}"
    )


def display_direction(direction: TradeDirection | str) -> str:
    """
    Convert canonical TradeDirection to UI display string.

    LONG  → "BUY"
    SHORT → "SELL"
    NONE  → "NO TRADE"
    """
    d = normalize_direction(direction) if isinstance(direction, str) else direction
    display_map = {
        TradeDirection.LONG: "BUY",
        TradeDirection.SHORT: "SELL",
        TradeDirection.NONE: "NO TRADE",
    }
    return display_map[d]
