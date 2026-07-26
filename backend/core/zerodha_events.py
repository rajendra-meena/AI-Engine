"""
MarketMind AI — Zerodha Kite Connect Event Type Definitions

All Zerodha/Kite-specific event types for the Auto Trade system.
These supplement the core event types in core/events.py.
"""

# ── Authentication ──

ZERODHA_AUTHENTICATED = "zerodha_authenticated"
ZERODHA_AUTH_FAILED = "zerodha_auth_failed"
ZERODHA_TOKEN_EXPIRED = "zerodha_token_expired"

# ── Instrument Master ──

INSTRUMENTS_LOADING = "instruments_loading"
INSTRUMENTS_LOADED = "instruments_loaded"
INSTRUMENTS_LOAD_FAILED = "instruments_load_failed"

# ── WebSocket ──

KITE_WS_CONNECTING = "kite_ws_connecting"
KITE_WS_CONNECTED = "kite_ws_connected"
KITE_WS_DISCONNECTED = "kite_ws_disconnected"
KITE_WS_RECONNECTING = "kite_ws_reconnecting"
KITE_WS_ERROR = "kite_ws_error"
KITE_WS_NORECONNECT = "kite_ws_noreconnect"

# ── Subscriptions ──

SYMBOL_SUBSCRIBED = "symbol_subscribed"
SYMBOL_UNSUBSCRIBED = "symbol_unsubscribed"
SUBSCRIPTIONS_RESTORED = "subscriptions_restored"

# ── Live Ticks ──

LIVE_TICK_RECEIVED = "live_tick_received"
LIVE_TICK_STALE = "live_tick_stale"
LIVE_TICK_RECOVERED = "live_tick_recovered"
MARKET_DATA_STALE = "market_data_stale"
MARKET_DATA_RECOVERED = "market_data_recovered"

# ── Historical Data ──

HISTORICAL_WARMUP_STARTED = "historical_warmup_started"
HISTORICAL_WARMUP_PROGRESS = "historical_warmup_progress"
HISTORICAL_WARMUP_COMPLETED = "historical_warmup_completed"
HISTORICAL_WARMUP_FAILED = "historical_warmup_failed"

# ── Data Gaps ──

DATA_GAP_DETECTED = "data_gap_detected"
DATA_GAP_FILLED = "data_gap_filled"
CANDLE_CONTINUITY_LOST = "candle_continuity_lost"
CANDLE_CONTINUITY_RESTORED = "candle_continuity_restored"

# ── Quote Reconciliation ──

QUOTE_RECONCILIATION_TRIGGERED = "quote_reconciliation_triggered"
QUOTE_RECONCILIATION_PASSED = "quote_reconciliation_passed"
QUOTE_RECONCILIATION_FAILED = "quote_reconciliation_failed"

# ── Signals ──

SIGNAL_GENERATED = "signal_generated"
SIGNAL_REJECTED = "signal_rejected"
SIGNAL_EXPIRED = "signal_expired"

# ── Trade Plans ──

TRADE_PLAN_CREATED = "trade_plan_created"
TRADE_PLAN_EXPIRED = "trade_plan_expired"
TRADE_PLAN_INVALIDATED = "trade_plan_invalidated"

# ── Orders ──

ORDER_SUBMITTED = "order_submitted"
ORDER_UPDATED = "order_updated"
ORDER_FILLED = "order_filled"
ORDER_REJECTED = "order_rejected"
ORDER_CANCELLED = "order_cancelled"
ORDER_PARTIAL_FILL = "order_partial_fill"

# ── Positions ──

POSITION_OPENED = "position_opened"
POSITION_UPDATED = "position_updated"
POSITION_CLOSED = "position_closed"
TRADE_CLOSED = "trade_closed"

# ── Engine Lifecycle ──

MARKET_DATA_ENGINE_STARTED = "market_data_engine_started"
MARKET_DATA_ENGINE_STOPPED = "market_data_engine_stopped"
MARKET_DATA_ENGINE_ERROR = "market_data_engine_error"
RECONNECTION_STARTED = "reconnection_started"
RECONNECTION_COMPLETED = "reconnection_completed"
RECONNECTION_FAILED = "reconnection_failed"
