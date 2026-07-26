"""
MarketMind AI — Symbol Freshness Tracker

Tracks per-symbol data freshness across all stages of the market-data pipeline.
Every derived object in the Auto Trade system references a freshness status
so stale data can be identified and blocked before execution.

Status values:
  LIVE          — Tick received within strict threshold (default 5s)
  FRESH         — Data is recent but outside the LIVE window (default 30s)
  DELAYED       — Data is older than expected but not yet critical
  STALE         — Data exceeds the stale threshold (default 30s for ticks)
  DISCONNECTED  — No data for a prolonged period (default 120s)
  WARMING_UP   — Initial data loading or indicator warm-up in progress
  GAP_DETECTED — A gap exists between historical and live candle data
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ── Default thresholds (milliseconds) ──
TICK_FRESHNESS_MS: int = 5_000          # 5s — tick is considered LIVE
STALE_THRESHOLD_MS: int = 30_000        # 30s — tick is STALE
DISCONNECTED_THRESHOLD_MS: int = 120_000  # 2m — tick is DISCONNECTED
CANDLE_FRESHNESS_MS: int = 120_000      # 2m — completed candle still fresh
INDICATOR_FRESHNESS_MS: int = 180_000   # 3m — indicator snapshot still fresh
REGIME_FRESHNESS_MS: int = 300_000      # 5m — regime snapshot still fresh
AI_DECISION_FRESHNESS_MS: int = 300_000 # 5m — AI decision still fresh

FRESHNESS_LIVE = "LIVE"
FRESHNESS_FRESH = "FRESH"
FRESHNESS_DELAYED = "DELAYED"
FRESHNESS_STALE = "STALE"
FRESHNESS_DISCONNECTED = "DISCONNECTED"
FRESHNESS_WARMING_UP = "WARMING_UP"
FRESHNESS_GAP_DETECTED = "GAP_DETECTED"


@dataclass
class SymbolFreshness:
    """Freshness state for one symbol."""
    symbol: str = ""
    instrument_token: int = 0
    exchange: str = "NSE"
    tradingsymbol: str = ""

    # Timestamps (ISO strings or None)
    last_tick_receipt: str | None = None
    last_tick_exchange: str | None = None
    last_completed_candle: str | None = None
    last_indicator_calculation: str | None = None
    last_context_update: str | None = None
    last_regime_update: str | None = None
    last_ai_decision: str | None = None
    last_quote_reconciliation: str | None = None

    # Derived status
    tick_freshness: str = FRESHNESS_WARMING_UP
    candle_freshness: str = FRESHNESS_WARMING_UP
    indicator_freshness: str = FRESHNESS_WARMING_UP
    regime_freshness: str = FRESHNESS_WARMING_UP
    ai_freshness: str = FRESHNESS_WARMING_UP

    # Provider metadata (attached to all derived objects)
    source_provider: str = "ZERODHA_KITE"
    data_version: str = ""
    gap_detected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "source_provider": self.source_provider,
            "instrument_token": self.instrument_token,
            "exchange": self.exchange,
            "tradingsymbol": self.tradingsymbol,
            "last_tick_receipt": self.last_tick_receipt,
            "last_tick_exchange": self.last_tick_exchange,
            "last_completed_candle": self.last_completed_candle,
            "last_indicator_calculation": self.last_indicator_calculation,
            "last_context_update": self.last_context_update,
            "last_regime_update": self.last_regime_update,
            "last_ai_decision": self.last_ai_decision,
            "tick_freshness": self.tick_freshness,
            "candle_freshness": self.candle_freshness,
            "indicator_freshness": self.indicator_freshness,
            "regime_freshness": self.regime_freshness,
            "ai_freshness": self.ai_freshness,
            "gap_detected": self.gap_detected,
        }

    @property
    def overall_freshness(self) -> str:
        """Worst-case freshness across all tracked categories."""
        order = [
            FRESHNESS_DISCONNECTED,
            FRESHNESS_GAP_DETECTED,
            FRESHNESS_STALE,
            FRESHNESS_DELAYED,
            FRESHNESS_WARMING_UP,
            FRESHNESS_FRESH,
            FRESHNESS_LIVE,
        ]
        current = FRESHNESS_LIVE
        statuses = [
            self.tick_freshness,
            self.candle_freshness,
            self.indicator_freshness,
            self.regime_freshness,
            self.ai_freshness,
        ]
        for s in statuses:
            if s in order and order.index(s) < order.index(current):
                current = s
        return current


class SymbolFreshnessTracker:
    """
    Tracks freshness for all symbols in the Auto Trade universe.
    Thread-safe single-symbol updates.
    """

    def __init__(self):
        self._symbols: dict[str, SymbolFreshness] = {}

    def get_or_create(self, symbol: str) -> SymbolFreshness:
        if symbol not in self._symbols:
            self._symbols[symbol] = SymbolFreshness(symbol=symbol)
        return self._symbols[symbol]

    def get(self, symbol: str) -> SymbolFreshness | None:
        return self._symbols.get(symbol)

    def update_tick(self, symbol: str, instrument_token: int, exchange: str,
                    tradingsymbol: str, receipt_time: str,
                    exchange_time: str | None = None):
        sf = self.get_or_create(symbol)
        sf.instrument_token = instrument_token
        sf.exchange = exchange
        sf.tradingsymbol = tradingsymbol
        sf.last_tick_receipt = receipt_time
        sf.last_tick_exchange = exchange_time or receipt_time
        sf.tick_freshness = self._compute_tick_freshness(receipt_time)
        return sf

    def update_candle(self, symbol: str, candle_time: str):
        sf = self.get_or_create(symbol)
        sf.last_completed_candle = candle_time
        sf.candle_freshness = self._compute_candle_freshness(candle_time)
        return sf

    def update_indicator(self, symbol: str):
        sf = self.get_or_create(symbol)
        sf.last_indicator_calculation = _now_str()
        sf.indicator_freshness = FRESHNESS_LIVE
        return sf

    def update_context(self, symbol: str):
        sf = self.get_or_create(symbol)
        sf.last_context_update = _now_str()
        return sf

    def update_regime(self, symbol: str):
        sf = self.get_or_create(symbol)
        sf.last_regime_update = _now_str()
        sf.regime_freshness = FRESHNESS_LIVE
        return sf

    def update_ai(self, symbol: str):
        sf = self.get_or_create(symbol)
        sf.last_ai_decision = _now_str()
        sf.ai_freshness = FRESHNESS_LIVE
        return sf

    def mark_warming(self, symbol: str):
        sf = self.get_or_create(symbol)
        sf.tick_freshness = FRESHNESS_WARMING_UP
        sf.candle_freshness = FRESHNESS_WARMING_UP
        sf.indicator_freshness = FRESHNESS_WARMING_UP
        sf.regime_freshness = FRESHNESS_WARMING_UP
        sf.ai_freshness = FRESHNESS_WARMING_UP

    def mark_gap(self, symbol: str, detected: bool = True):
        sf = self.get_or_create(symbol)
        sf.gap_detected = detected
        if detected:
            sf.candle_freshness = FRESHNESS_GAP_DETECTED

    def mark_disconnected(self, symbol: str):
        sf = self.get_or_create(symbol)
        sf.tick_freshness = FRESHNESS_DISCONNECTED
        sf.candle_freshness = FRESHNESS_DISCONNECTED
        sf.indicator_freshness = FRESHNESS_DISCONNECTED
        sf.regime_freshness = FRESHNESS_DISCONNECTED
        sf.ai_freshness = FRESHNESS_DISCONNECTED

    def refresh_all(self):
        """Recompute freshness for all symbols based on current timestamps."""
        now = _now_dt()
        for sf in self._symbols.values():
            sf.tick_freshness = self._compute_tick_freshness(sf.last_tick_receipt, now)
            sf.candle_freshness = self._compute_candle_freshness(sf.last_completed_candle, now)
            if not sf.gap_detected and sf.candle_freshness == FRESHNESS_WARMING_UP and sf.last_completed_candle:
                sf.candle_freshness = FRESHNESS_FRESH

    def all_freshness(self) -> dict[str, dict[str, Any]]:
        return {sym: sf.to_dict() for sym, sf in self._symbols.items()}

    def all_data_safe(self) -> bool:
        """All tracked symbols have safe data (not STALE/DISCONNECTED)."""
        for sf in self._symbols.values():
            if sf.tick_freshness in (FRESHNESS_STALE, FRESHNESS_DISCONNECTED):
                return False
            if sf.gap_detected:
                return False
        return True

    def is_data_safe(self, symbol: str) -> tuple[bool, str]:
        """Check if a specific symbol's data is safe for execution."""
        sf = self._symbols.get(symbol)
        if not sf:
            return False, f"No freshness data for {symbol}"
        if sf.tick_freshness in (FRESHNESS_STALE, FRESHNESS_DISCONNECTED):
            return False, f"Tick data is {sf.tick_freshness} for {symbol}"
        if sf.candle_freshness in (FRESHNESS_STALE, FRESHNESS_DISCONNECTED):
            return False, f"Candle data is {sf.candle_freshness} for {symbol}"
        if sf.gap_detected:
            return False, f"Candle gap detected for {symbol}"
        if sf.indicator_freshness in (FRESHNESS_STALE, FRESHNESS_DISCONNECTED):
            return False, f"Indicator data is {sf.indicator_freshness} for {symbol}"
        if sf.regime_freshness in (FRESHNESS_STALE, FRESHNESS_DISCONNECTED):
            return False, f"Regime data is {sf.regime_freshness} for {symbol}"
        if sf.ai_freshness in (FRESHNESS_STALE, FRESHNESS_DISCONNECTED):
            return False, f"AI decision is {sf.ai_freshness} for {symbol}"
        return True, "OK"

    def _compute_tick_freshness(self, ts_str: str | None, now: datetime | None = None) -> str:
        if not ts_str:
            return FRESHNESS_WARMING_UP
        age_ms = _age_ms(ts_str, now)
        if age_ms < 0:
            return FRESHNESS_WARMING_UP
        if age_ms <= TICK_FRESHNESS_MS:
            return FRESHNESS_LIVE
        if age_ms <= STALE_THRESHOLD_MS:
            return FRESHNESS_FRESH
        if age_ms <= DISCONNECTED_THRESHOLD_MS:
            return FRESHNESS_DELAYED
        return FRESHNESS_DISCONNECTED

    def _compute_candle_freshness(self, ts_str: str | None, now: datetime | None = None) -> str:
        if not ts_str:
            return FRESHNESS_WARMING_UP
        age_ms = _age_ms(ts_str, now)
        if age_ms < 0:
            return FRESHNESS_WARMING_UP
        if age_ms <= CANDLE_FRESHNESS_MS:
            return FRESHNESS_FRESH
        if age_ms <= CANDLE_FRESHNESS_MS * 2:
            return FRESHNESS_DELAYED
        return FRESHNESS_STALE

    def get_status_summary(self) -> dict[str, Any]:
        """Summary of all tracked symbols for the workspace endpoint."""
        total = len(self._symbols)
        live = sum(1 for s in self._symbols.values() if s.tick_freshness == FRESHNESS_LIVE)
        stale = sum(1 for s in self._symbols.values() if s.tick_freshness == FRESHNESS_STALE)
        disconnected = sum(1 for s in self._symbols.values() if s.tick_freshness == FRESHNESS_DISCONNECTED)
        warming = sum(1 for s in self._symbols.values() if s.tick_freshness == FRESHNESS_WARMING_UP)
        gaps = sum(1 for s in self._symbols.values() if s.gap_detected)
        return {
            "total_symbols": total,
            "live": live,
            "stale": stale,
            "disconnected": disconnected,
            "warming_up": warming,
            "gaps_detected": gaps,
        }


# ── Metadata helpers for derived objects ──

def freshness_metadata(
    symbol: str,
    instrument_token: int = 0,
    exchange: str = "NSE",
    tradingsymbol: str = "",
    freshness_status: str = FRESHNESS_LIVE,
    data_version: str = "",
    candle_version: str = "",
) -> dict[str, Any]:
    """Return the standard freshness metadata block attached to every derived object."""
    return {
        "source_provider": "ZERODHA_KITE",
        "instrument_token": instrument_token,
        "exchange": exchange,
        "tradingsymbol": tradingsymbol,
        "source_timestamp": _now_str(),
        "calculated_at": _now_str(),
        "data_version": data_version,
        "candle_version": candle_version,
        "freshness_status": freshness_status,
    }


# ── Internal helpers ──

def _now_str() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _age_ms(ts_str: str | None, now: datetime | None = None) -> float:
    """Age of timestamp in milliseconds from now (or provided reference)."""
    if not ts_str:
        return -1.0
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ref = now or _now_dt()
        return (ref - dt).total_seconds() * 1000
    except (ValueError, TypeError):
        return -1.0
