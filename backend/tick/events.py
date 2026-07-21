"""
MarketMind AI — Tick Engine Event Types
"""

NEW_TICK = "new_tick"
TICK_UPDATED = "tick_updated"
SYMBOL_UPDATED = "symbol_updated"
STREAM_STARTED = "stream_started"
STREAM_STOPPED = "stream_stopped"

# These events should be forwarded to WebSocket clients
FORWARDED_TICK_EVENTS = {
    NEW_TICK: "market_data",
    TICK_UPDATED: "market_data",
    SYMBOL_UPDATED: "market_data",
    STREAM_STARTED: "system",
    STREAM_STOPPED: "system",
}
