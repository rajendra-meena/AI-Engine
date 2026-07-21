"""
MarketMind AI — Constants

Every "magic number" that was previously hardcoded across the codebase.
Extracted here so future phases have one source of truth.

Grouped by domain for clarity. Add new constants to the appropriate section.
"""

# ── Cache defaults ──

DAILY_LOOKBACK_DEFAULT_DAYS = 365       # Default fetch range for daily data
DAILY_LOOKBACK_MIN_DAYS = 200           # Minimum lookback for indicators
DAILY_OVERLAP_DAYS = 5                  # Overlap when refreshing daily cache
INTRADAY_MAX_DAYS_FAST = 2              # Max history for 1m/2m intervals
INTRADAY_MAX_DAYS_DEFAULT = 60          # Max history for other intervals
DAILY_REFS_LOOKBACK_DAYS = 10           # Days of daily data for reference levels
DAILY_REFS_WEEKLY_WINDOW = 5            # Candles to compute weekly high/low
DAILY_REFS_MIN_CANDLES = 2              # Minimum candles needed for ref levels

# ── In-memory cache TTLs (seconds) ──

MEMORY_CACHE_TTL_INTRADAY = 30           # Intraday candles: 30s
MEMORY_CACHE_TTL_DAILY = 300             # Daily candles: 5 min
MEMORY_CACHE_TTL_REFERENCE = 300         # Reference levels: 5 min
MEMORY_CACHE_TTL_PROVIDER_STATUS = 60    # Provider health: 1 min
MEMORY_CACHE_TTL_DEFAULT = 60            # Default for uncategorized items
MEMORY_CACHE_MAX_ITEMS = 500             # Maximum cached entries

# ── Cache flush timing ──

CACHE_FLUSH_BUFFER_SEC = 30             # Buffer before considering a candle closed

# ── Intraday ──

ORB_MINUTES = 15                        # Opening Range Breakout window
ORB_MIN_CANDLES_RATIO = 1               # Minimum candles for ORB calculation

# ── Interval parsing ──

MINUTE_SUFFIX = "m"
HOUR_SUFFIX = "h"
FAST_INTERVALS = ("1m", "2m")

# ── Backtesting ──

BACKTEST_BUFFER_DAYS_INTRADAY = 5       # Extra days to fetch for intraday backtest
BACKTEST_BUFFER_DAYS_DAILY = 5          # Extra days to fetch for daily backtest
BACKTEST_INTRADAY_INTERVAL = "15m"      # Interval used for intraday backtesting
BACKTEST_DAILY_INTERVAL = "1d"          # Interval used for daily backtesting

# ── Default API values ──

DEFAULT_API_LIMIT = 50
MAX_API_LIMIT = 500

# ── Daily reference labels ──

REF_DAYS_BACK = 2                       # Index for "previous day" (0=latest, 1=prev)

# ── Confidence thresholds (future AI use) ──

CONFIDENCE_VERY_HIGH = 85
CONFIDENCE_HIGH = 70
CONFIDENCE_MODERATE = 50
CONFIDENCE_LOW = 30

# ── Risk constants (future use) ──

RISK_MIN_RATIO = 2.0                    # Minimum risk-reward ratio
ATR_SL_MULTIPLIER_DEFAULT = 2.0         # Default ATR multiplier for stop loss
ATR_TARGET_MULTIPLIER_MIN = 1.0         # Minimum ATR multiplier for target
