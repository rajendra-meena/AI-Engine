"""
MarketMind AI — Event Type Definitions

Defines every event that the system can emit or react to.
This is a *definition-only* module — no event bus, no dispatcher, no logic.

For future use: when the Event Bus is implemented, these event types will
be the canonical set. Every module should use these strings/constants.
"""

# ── Candle & Price Events ──

NEW_CANDLE = "new_candle"               # A new candle has closed (per interval)
PRICE_UPDATE = "price_update"           # Real-time price tick (future)
VWAP_CROSS = "vwap_cross"               # Price crossed VWAP
EMA_CROSS = "ema_cross"                 # EMA crossover (e.g. 9×21)

# ── Indicator Events ──

RSI_SIGNAL = "rsi_signal"              # RSI crossed a threshold (30/70)
MACD_SIGNAL = "macd_signal"            # MACD line crossed signal line
ATR_EXPANSION = "atr_expansion"        # ATR expanded beyond threshold
BOLLINGER_TOUCH = "bollinger_touch"    # Price touched outer Bollinger Band

# ── Pattern Events ──

PATTERN_DETECTED = "pattern_detected"   # Generic pattern detected
BREAKOUT = "breakout"                   # Price broke a level
BREAKDOWN = "breakdown"                 # Price broke down through a level
FAKE_BREAKOUT = "fake_breakout"        # Price faked a breakout and reversed
RETEST = "retest"                       # Price returned to a broken level
PULLBACK = "pullback"                   # Price pulled back within trend

# ── Structure Events ──

SWING_HIGH = "swing_high"              # New swing high formed
SWING_LOW = "swing_low"                # New swing low formed
TREND_CHANGED = "trend_changed"        # Trend direction changed (HH/HL etc.)
SUPPLY_ZONE = "supply_zone"           # Price entered a supply zone
DEMAND_ZONE = "demand_zone"           # Price entered a demand zone

# ── Volume Events ──

VOLUME_SPIKE = "volume_spike"          # Volume > threshold above average
LOW_VOLUME_TRAP = "low_volume_trap"   # Move on low volume (suspicious)

# ── Signal Events (future) ──

SIGNAL_CREATED = "signal_created"        # New trade signal created
SIGNAL_UPDATED = "signal_updated"        # Signal state changed
SIGNAL_CANCELLED = "signal_cancelled"    # Signal was invalidated
SIGNAL_TARGET_HIT = "signal_target_hit" # A target was reached
SIGNAL_STOP_HIT = "signal_stop_hit"     # Stop loss was triggered

# ── AI Decision Events (future) ──

AI_DECISION = "ai_decision"            # AI engine produced a decision
AI_WAIT = "ai_wait"                    # AI decided to wait
AI_NO_TRADE = "ai_no_trade"            # AI rejected the setup

# ── Market Events ──

MARKET_OPEN = "market_open"            # Market opened
MARKET_CLOSE = "market_close"          # Market closed
NEW_SESSION = "new_session"            # Market phase changed (e.g. Opening→Mid)
