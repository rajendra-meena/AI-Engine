"""
MarketMind AI — Central Configuration (Static)

Legacy flat-config module for backward compatibility during migration.
New code should import from the specific submodules:

  core/settings.py     — env-var-backed settings
  core/constants.py    — magic numbers & thresholds
  core/enums.py        — shared enum types
  core/events.py       — event type definitions
  core/intervals.py    — interval registry
  core/market_calendar.py — market timing helpers
  core/symbols.py      — symbol registry
  core/validators.py   — validation functions
"""

# Re-export from submodules
from core.constants import *
from core.intervals import *
from core.symbols import SYMBOL_MAP, DISPLAY_NAMES
from core.enums import Outcome

# ── Paths (derived, not env-overridable) ──

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_CACHE_DIR = os.path.join(BACKEND_DIR, "data_cache")
DB_PATH = os.path.join(BACKEND_DIR, "marketmind.db")

os.makedirs(DATA_CACHE_DIR, exist_ok=True)

# ── Market hours (IST) — moved to core/market_calendar.py ──

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30

# ── API defaults ──

DEFAULT_SYMBOL = "NIFTY 50"
DEFAULT_INTERVAL = "15m"
DEFAULT_INTRADAY_DAYS = 3
PREDICTION_LIST_LIMIT = 50

# ── Backtesting outcome labels — moved to core/enums.py as Outcome enum ──

OUTCOME_HIT_TARGET = "HIT_TARGET"
OUTCOME_HIT_STOPLOSS = "HIT_STOPLOSS"
OUTCOME_NO_TRADE = "NO_TRADE"
OUTCOME_UNCHECKED = "UNCHECKED"
OUTCOME_PENDING = "PENDING"
