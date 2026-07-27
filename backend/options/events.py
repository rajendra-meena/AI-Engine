"""
MarketMind AI — Options Engine Event Types

Canonical event constants for the Options Buying Engine.
All events published via EventBus MUST use these constants.
"""

# ── Instrument Discovery ──

OPTION_INSTRUMENTS_REFRESH_STARTED = "option_instruments_refresh_started"
OPTION_INSTRUMENTS_LOADED = "option_instruments_loaded"
OPTION_INSTRUMENTS_REFRESH_FAILED = "option_instruments_refresh_failed"

# ── Chain Ingestion ──

OPTION_CHAIN_REFRESH_STARTED = "option_chain_refresh_started"
OPTION_CHAIN_RECEIVED = "option_chain_received"
OPTION_CHAIN_VALIDATED = "option_chain_validated"
OPTION_CHAIN_UPDATED = "option_chain_updated"
OPTION_CHAIN_AGING = "option_chain_aging"
OPTION_CHAIN_STALE = "option_chain_stale"
OPTION_CHAIN_REFRESH_FAILED = "option_chain_refresh_failed"

# ── Strike Analysis ──

OPTION_STRIKE_ANALYZED = "option_strike_analyzed"
OPTION_STRIKES_RANKED = "option_strikes_ranked"

# ── Decision ──

OPTION_DECISION_CREATED = "option_decision_created"
OPTION_DECISION_REJECTED = "option_decision_rejected"
OPTION_DECISION_EXPIRED = "option_decision_expired"

# ── Execution ──

OPTION_POSITION_OPENED = "option_position_opened"
OPTION_POSITION_UPDATED = "option_position_updated"
OPTION_POSITION_CLOSED = "option_position_closed"
OPTION_SL_HIT = "option_sl_hit"
OPTION_TARGET_HIT = "option_target_hit"
OPTION_TRAIL_TRIGGERED = "option_trail_triggered"
OPTION_DECAY_EXIT = "option_decay_exit"
OPTION_DUP_BLOCKED = "option_dup_blocked"
OPTION_REENTRY_BLOCKED = "option_reentry_blocked"

# ── Shadow Paper ──

OPTION_SHADOW_ORDER_PLACED = "option_shadow_order_placed"
OPTION_SHADOW_ORDER_FILLED = "option_shadow_order_filled"
OPTION_SHADOW_ORDER_CANCELLED = "option_shadow_order_cancelled"

# ── Provider Health ──

OPTION_PROVIDER_CONNECTED = "option_provider_connected"
OPTION_PROVIDER_DEGRADED = "option_provider_degraded"
OPTION_PROVIDER_DISCONNECTED = "option_provider_disconnected"

# ── Engine Lifecycle ──

OPTIONS_ENGINE_STARTED = "options_engine_started"
OPTIONS_ENGINE_STOPPED = "options_engine_stopped"
OPTIONS_ENGINE_ERROR = "options_engine_error"
OPTION_ENGINE_READY = "option_engine_ready"
OPTION_ENGINE_DEGRADED = "option_engine_degraded"
OPTION_ENGINE_NOT_READY = "option_engine_not_ready"
