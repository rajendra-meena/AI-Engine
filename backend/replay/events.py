"""
MarketMind AI — Replay Engine Event Types

Event constants specific to the Historical Replay Engine.
These are published on the main Event Bus during replay.
"""

REPLAY_STARTED = "replay_started"
REPLAY_STOPPED = "replay_stopped"
REPLAY_PAUSED = "replay_paused"
REPLAY_RESUMED = "replay_resumed"
REPLAY_FINISHED = "replay_finished"
REPLAY_SEEK = "replay_seek"
REPLAY_SPEED_CHANGED = "replay_speed_changed"
NEW_HISTORICAL_CANDLE = "new_historical_candle"

# Events that the WebSocket Gateway should forward
FORWARDED_REPLAY_EVENTS = {
    REPLAY_STARTED: "replay",
    REPLAY_STOPPED: "replay",
    REPLAY_PAUSED: "replay",
    REPLAY_RESUMED: "replay",
    REPLAY_FINISHED: "replay",
    REPLAY_SEEK: "replay",
    REPLAY_SPEED_CHANGED: "replay",
    NEW_HISTORICAL_CANDLE: "market_data",
}
