"""
MarketMind AI — Unified Domain Models

Standardized, immutable, serializable data models used across the entire application.
All future modules must use these models instead of raw dicts for internal data exchange.

External REST API responses are preserved via careful to_dict() mappings.

Model categories:
    Tick            — Single price tick (future real-time use)
    Candle          — OHLCV candle (intraday and daily)
    ReferenceLevels — Daily/weekly reference levels
    MarketSnapshot  — Complete view of a symbol at a point in time
    VolumeData      — Volume analysis data
    PriceLevel      — A price level (S/R, swing, etc.)
    TimeframeInfo   — Interval metadata
    MarketSession   — Current market session info
    ProviderStatus  — Provider health and capabilities
"""

from models.candle import Candle, DailyCandle
from models.tick import Tick
from models.snapshot import MarketSnapshot
from models.reference_levels import ReferenceLevels
from models.volume import VolumeData
from models.metadata import PriceLevel, TimeframeInfo, MarketSession, ProviderStatus
