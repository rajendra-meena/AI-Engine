"""
Zerodha Kite Connect — Instrument Manager

Downloads and caches the Kite instrument master locally.
Provides searching/filtering by symbol, exchange, expiry, strike, etc.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from utils.logger import log_info, log_warn, log_error

INSTRUMENT_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "data_cache", "kite_instruments.json"
)


class InstrumentManager:
    """
    Manages the Kite instrument master.

    Downloads from Kite on first use or cache expiry, then provides
    fast local lookup by symbol, token, exchange, expiry, etc.
    """

    CACHE_TTL_SECONDS = 86400  # 24 hours

    def __init__(self, kite=None):
        self._kite = kite
        self._instruments: list[dict[str, Any]] = []
        self._by_token: dict[int, dict[str, Any]] = {}
        self._by_symbol: dict[str, list[dict[str, Any]]] = {}
        self._last_download: datetime | None = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def set_kite(self, kite):
        """Set or update the KiteConnect instance."""
        self._kite = kite

    # ── Loading ──

    async def load(self, force: bool = False) -> bool:
        """
        Load instruments from cache or download from Kite.

        Args:
            force: If True, always download fresh from Kite.

        Returns:
            True if loaded successfully.
        """
        if self._loaded and not force:
            return True

        # Try cache first
        if not force and self._load_from_cache():
            return True

        # Download from Kite
        if self._kite:
            return await self._download()

        log_warn("InstrumentManager: no Kite instance and no cache")
        return False

    def _load_from_cache(self) -> bool:
        """Load instruments from local cache file."""
        try:
            if not os.path.exists(INSTRUMENT_CACHE_FILE):
                return False

            cache_age = datetime.now().timestamp() - os.path.getmtime(INSTRUMENT_CACHE_FILE)
            if cache_age > self.CACHE_TTL_SECONDS:
                log_info("InstrumentManager: cache expired")
                os.remove(INSTRUMENT_CACHE_FILE)
                return False

            with open(INSTRUMENT_CACHE_FILE, "r") as f:
                data = json.load(f)

            self._instruments = data.get("instruments", [])
            self._last_download = datetime.fromisoformat(data["downloaded_at"]) if data.get("downloaded_at") else None
            self._build_index()
            self._loaded = True
            log_info(
                "InstrumentManager: loaded from cache",
                count=len(self._instruments),
                age_hours=round(cache_age / 3600, 1),
            )
            return True
        except Exception as e:
            log_warn("InstrumentManager: cache load failed, removing corrupt cache", error=str(e))
            try:
                os.remove(INSTRUMENT_CACHE_FILE)
            except Exception:
                pass
            return False

    async def _download(self) -> bool:
        """Download instrument master from Kite."""
        if not self._kite:
            log_error("InstrumentManager: no Kite instance for download")
            return False

        try:
            import asyncio
            # Increase timeout for large NFO instrument master (5MB+)
            instruments = await asyncio.wait_for(
                asyncio.to_thread(self._kite.instruments),
                timeout=120.0
            )
            self._instruments = instruments
            self._last_download = datetime.now(timezone.utc)
            self._build_index()
            self._loaded = True

            # Save to cache
            self._save_cache()

            log_info(
                "InstrumentManager: downloaded from Kite",
                count=len(self._instruments),
            )
            return True
        except asyncio.TimeoutError:
            log_error("InstrumentManager: download timed out (120s)")
            return False
        except Exception as e:
            log_error("InstrumentManager: download failed", error=str(e))
            return False

    def _build_index(self):
        """Build lookup indexes from the instrument list."""
        self._by_token.clear()
        self._by_symbol.clear()
        for inst in self._instruments:
            token = inst.get("instrument_token")
            if token:
                self._by_token[token] = inst
            symbol = inst.get("tradingsymbol", "")
            if symbol:
                if symbol not in self._by_symbol:
                    self._by_symbol[symbol] = []
                self._by_symbol[symbol].append(inst)

    def _save_cache(self):
        """Save instruments to local cache file atomically with validation."""
        try:
            os.makedirs(os.path.dirname(INSTRUMENT_CACHE_FILE), exist_ok=True)
            data = {
                "downloaded_at": self._last_download.isoformat() if self._last_download else "",
                "count": len(self._instruments),
                "instruments": self._instruments,
            }
            # Write to temp, validate, then atomically rename
            tmp_path = INSTRUMENT_CACHE_FILE + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(data, f)
            with open(tmp_path, "r") as f:
                json.load(f)  # validate
            os.replace(tmp_path, INSTRUMENT_CACHE_FILE)
            log_info("InstrumentManager: cache saved", path=INSTRUMENT_CACHE_FILE, count=len(self._instruments))
        except Exception as e:
            log_warn("InstrumentManager: cache save failed", error=str(e))
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    # ── Lookups ──

    def search(self, query: str, exchange: str | None = None) -> list[dict[str, Any]]:
        """
        Search instruments by trading symbol fragment.

        Args:
            query: Search text (e.g. "NIFTY", "BANKNIFTY")
            exchange: Optional filter (e.g. "NSE", "BSE")

        Returns:
            Matching instrument dicts.
        """
        query = query.upper()
        results = []
        for inst in self._instruments:
            symbol = inst.get("tradingsymbol", "").upper()
            if query not in symbol:
                continue
            if exchange and inst.get("exchange", "").upper() != exchange.upper():
                continue
            results.append(inst)
        return results[:50]  # limit results

    def get_by_token(self, token: int) -> dict[str, Any] | None:
        """Look up an instrument by its Kite instrument token."""
        return self._by_token.get(token)

    def get_by_symbol(self, symbol: str, exchange: str = "NSE") -> dict[str, Any] | None:
        """Look up an instrument by trading symbol and exchange."""
        matches = self._by_symbol.get(symbol, [])
        if not matches:
            return None
        # Prefer the given exchange
        for m in matches:
            if m.get("exchange", "").upper() == exchange.upper():
                return m
        return matches[0]

    def get_nse_futures(self, symbol: str) -> list[dict[str, Any]]:
        """Get NSE futures for a given symbol."""
        results = []
        for inst in self._instruments:
            if (
                inst.get("tradingsymbol", "").startswith(symbol)
                and inst.get("exchange") == "NSE"
                and inst.get("segment") == "NSE-FO"
                and inst.get("instrument_type") == "FUTIDX"
            ):
                results.append(inst)
        return results

    def get_nse_options(
        self, symbol: str, expiry: str | None = None
    ) -> list[dict[str, Any]]:
        """Get NSE options for a given symbol and optional expiry."""
        results = []
        for inst in self._instruments:
            if (
                inst.get("tradingsymbol", "").startswith(symbol)
                and inst.get("exchange") == "NSE"
                and inst.get("segment") == "NFO"
                and inst.get("instrument_type") in ("OPTIDX", "OPTSTK")
            ):
                if expiry and inst.get("expiry") != expiry:
                    continue
                results.append(inst)
        return results

    def get_expiries(self, symbol: str) -> list[str]:
        """Get available expiry dates for a symbol's options/futures."""
        expiries: set[str] = set()
        for inst in self._instruments:
            if (
                inst.get("tradingsymbol", "").startswith(symbol)
                and inst.get("segment") in ("NFO", "NSE-FO")
                and inst.get("expiry")
            ):
                expiries.add(inst["expiry"])
        return sorted(expiries)

    def map_to_kite_symbol(self, internal_symbol: str) -> str | None:
        """
        Map an internal display name (e.g. 'NIFTY 50') to a Kite trading symbol.

        Returns:
            Kite trading symbol or None if not found.
        """
        mapping = {
            "NIFTY 50": "NIFTY 50",
            "BANKNIFTY": "NIFTY BANK",
            "BANK NIFTY": "NIFTY BANK",
            "SENSEX": "SENSEX",
        }
        return mapping.get(internal_symbol)

    def map_to_kite_token(self, internal_symbol: str) -> int | None:
        """
        Map an internal display name to a Kite instrument token.

        Returns:
            Kite instrument token or None if not mapped.
        """
        # Try direct lookup by Kite symbol first
        kite_symbol = self.map_to_kite_symbol(internal_symbol)
        if kite_symbol:
            inst = self.get_by_symbol(kite_symbol, "NSE")
            if inst:
                return inst.get("instrument_token")
            # Broader lookup — try any exchange
            for inst in self._instruments:
                if inst.get("tradingsymbol") == kite_symbol:
                    return inst.get("instrument_token")

        # Fallback: search by internal display name directly in instrument master
        for inst in self._instruments:
            ts = inst.get("tradingsymbol", "").upper()
            name = inst.get("name", "").upper()
            if internal_symbol.upper() in (ts, name):
                return inst.get("instrument_token")

        return None

    # ── Status ──

    def get_stats(self) -> dict[str, Any]:
        return {
            "loaded": self._loaded,
            "total_instruments": len(self._instruments),
            "last_download": self._last_download.isoformat() if self._last_download else None,
            "cache_file": INSTRUMENT_CACHE_FILE,
        }
