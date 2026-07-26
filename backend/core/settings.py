"""
MarketMind AI — Environment Settings

Loads all configuration from environment variables with sensible defaults.
No hardcoded credentials. Every value can be overridden via .env or env vars.

For broker integration in future phases, add credentials here.
"""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


# ── Application ──

APP_NAME = os.getenv("MARKETMIND_APP_NAME", "MarketMind AI")
APP_VERSION = os.getenv("MARKETMIND_VERSION", "1.0.0")
DEBUG = os.getenv("MARKETMIND_DEBUG", "false").lower() == "true"
ENVIRONMENT = os.getenv("MARKETMIND_ENV", "development")

# ── Timezone ──

TIMEZONE = os.getenv("MARKETMIND_TIMEZONE", "Asia/Kolkata")
UTC_OFFSET_HOURS = float(os.getenv("MARKETMIND_UTC_OFFSET", "5.5"))

# ── Paths ──

DB_PATH = os.getenv("MARKETMIND_DB_PATH", os.path.join(BACKEND_DIR, "marketmind.db"))
CACHE_DIR = os.getenv("MARKETMIND_CACHE_DIR", os.path.join(BACKEND_DIR, "data_cache"))

# ── Server ──

HOST = os.getenv("MARKETMIND_HOST", "0.0.0.0")
PORT = int(os.getenv("MARKETMIND_PORT", "8000"))
CORS_ORIGINS = os.getenv("MARKETMIND_CORS_ORIGINS", "*")

# ── Logging ──

LOG_LEVEL = os.getenv("MARKETMIND_LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("MARKETMIND_LOG_FORMAT", "text")  # text or json

# ── Yahoo Finance (legacy / offline research only) ──

YAHOO_REQUEST_TIMEOUT = int(os.getenv("YAHOO_REQUEST_TIMEOUT", "30"))
YAHOO_MAX_RETRIES = int(os.getenv("YAHOO_MAX_RETRIES", "3"))

# ── Auto Trade Market Data Provider ──
# Controls which provider the Auto Trade pipeline uses.
# "ZERODHA_KITE" is the only supported provider for live Auto Trade.
AUTO_TRADE_MARKET_DATA_PROVIDER = os.getenv("AUTO_TRADE_MARKET_DATA_PROVIDER", "ZERODHA_KITE")

# ── Zerodha Kite Connect ──

ZERODHA_API_KEY = os.getenv("ZERODHA_API_KEY", "")
ZERODHA_API_SECRET = os.getenv("ZERODHA_API_SECRET", "")
ZERODHA_ACCESS_TOKEN = os.getenv("ZERODHA_ACCESS_TOKEN", "")

# ── Redis (future) ──

REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_TTL_SECONDS = int(os.getenv("REDIS_TTL_SECONDS", "3600"))

# ── WebSocket (future) ──

WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_PORT", "8001"))
WS_HEARTBEAT_INTERVAL = int(os.getenv("WS_HEARTBEAT_INTERVAL", "10"))

# ── Paper trading (future) ──

PAPER_TRADING_ENABLED = os.getenv("PAPER_TRADING_ENABLED", "false").lower() == "true"
PAPER_CAPITAL = float(os.getenv("PAPER_CAPITAL", "100000"))

# ── Risk defaults (future) ──

RISK_MAX_PER_TRADE_PERCENT = float(os.getenv("RISK_MAX_PER_TRADE_PERCENT", "1.0"))
RISK_MIN_RR = float(os.getenv("RISK_MIN_RR", "2.0"))
RISK_MAX_DAILY_LOSS_PERCENT = float(os.getenv("RISK_MAX_DAILY_LOSS_PERCENT", "3.0"))
