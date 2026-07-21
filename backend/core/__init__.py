"""
MarketMind AI — Core Configuration Layer

All configuration, settings, constants, enums, events, intervals, symbols,
market calendar, and validators. The single source of truth for the app.

For convenience, the most commonly used items are re-exported here.
Explicit imports from submodules are also fine.
"""

from core.settings import (
    APP_NAME,
    APP_VERSION,
    DEBUG,
    ENVIRONMENT,
    TIMEZONE,
    DB_PATH,
    CACHE_DIR,
)
from core.constants import (
    DEFAULT_API_LIMIT,
    ORB_MINUTES,
    CACHE_FLUSH_BUFFER_SEC,
)
from core.enums import (
    Direction,
    Bias,
    SignalState,
    Outcome,
    MarketSession,
    TrendDirection,
    TrendStrength,
    Decision,
    ConfidenceGrade,
)
from core.symbols import DEFAULT_SYMBOL
from core.intervals import DEFAULT_INTERVAL
