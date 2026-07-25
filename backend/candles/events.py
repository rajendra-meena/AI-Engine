"""
MarketMind AI — Candle Engine Event Types
"""

CANDLE_STARTED = "candle_started"  # A new candle began forming
CANDLE_UPDATED = "candle_updated"  # An active candle was updated by a tick
CANDLE_CLOSED = "candle_closed"  # A candle closed at timeframe boundary
TIMEFRAME_UPDATED = "timeframe_updated"  # All timeframes updated for a symbol
