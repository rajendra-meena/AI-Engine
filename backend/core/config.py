"""
MarketMind AI — Central Configuration

All constants, paths, symbol maps, and environment settings.
Centralized here so individual modules don't hard-code values.
"""

import os
from pathlib import Path

# ── Paths ──

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_CACHE_DIR = os.path.join(BACKEND_DIR, "data_cache")
DB_PATH = os.path.join(BACKEND_DIR, "marketmind.db")

os.makedirs(DATA_CACHE_DIR, exist_ok=True)

# ── Yahoo Finance tickers for Indian indices ──

SYMBOL_MAP = {
    "NIFTY 50": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
}

# Reverse lookup: ticker → display name
DISPLAY_NAMES = {v: k for k, v in SYMBOL_MAP.items()}

# ── Market hours (IST) ──

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30

# ── Intraday intervals ──

INTRADAY_INTERVALS = ("1m", "2m", "5m", "15m", "30m", "60m")
ORB_MINUTES = 15  # Opening Range Breakout window

# ── Cache defaults ──

DAILY_LOOKBACK_DAYS = 365        # Default fetch range for daily data
DAILY_OVERLAP_DAYS = 5           # Overlap when refreshing daily cache
INTRADAY_MAX_DAYS_FAST = 2       # Max history for 1m/2m intervals
INTRADAY_MAX_DAYS_DEFAULT = 60   # Max history for other intervals
DAILY_REFS_PERIOD = "10d"        # Period for daily reference data
CACHE_FLUSH_BUFFER_SEC = 30      # Buffer before considering a candle closed

# ── API defaults ──

DEFAULT_SYMBOL = "NIFTY 50"
DEFAULT_INTERVAL = "15m"
DEFAULT_INTRADAY_DAYS = 3
PREDICTION_LIST_LIMIT = 50

# ── Backtesting outcome labels ──

OUTCOME_HIT_TARGET = "HIT_TARGET"
OUTCOME_HIT_STOPLOSS = "HIT_STOPLOSS"
OUTCOME_NO_TRADE = "NO_TRADE"
OUTCOME_UNCHECKED = "UNCHECKED"
OUTCOME_PENDING = "PENDING"
