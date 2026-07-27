"""
MarketMind AI — Option Instrument Service

Discovers, validates, normalizes, and caches option instruments
from the provider. Groups by underlying/expiry/type/strike.
Preserves last valid set on refresh failure.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Any

from options.models import (
    InstrumentRefreshResult,
    OptionInstrument,
    OptionType,
)
from options.providers.base import OptionDataProvider

from utils.logger import log_info, log_warn, log_error


def _normalize_underlying(name: str) -> str:
    mapping = {
        "NIFTY": "NIFTY 50",
        "NIFTY 50": "NIFTY 50",
        "NIFTY BANK": "BANKNIFTY",
        "BANKNIFTY": "BANKNIFTY",
        "BANK NIFTY": "BANKNIFTY",
        "SENSEX": "SENSEX",
    }
    return mapping.get(name.strip().upper(), name.strip())


def _contract_identity(inst: OptionInstrument) -> str:
    return (
        f"{inst.underlying}|{inst.expiry.isoformat()}|"
        f"{inst.strike:.0f}|{inst.option_type.value}|{inst.instrument_token}"
    )


def _validate_instrument(
    inst: OptionInstrument,
    expected_underlying: str,
) -> str | None:
    if inst.instrument_token <= 0:
        return "missing_instrument_token"
    if inst.strike < 0:
        return "negative_strike"
    if inst.strike == 0:
        return "zero_strike"
    if inst.lot_size <= 0:
        return "invalid_lot_size"
    if inst.tick_size <= 0:
        return "invalid_tick_size"
    if inst.option_type not in (OptionType.CE, OptionType.PE):
        return "unsupported_option_type"
    if inst.underlying != expected_underlying:
        return "mismatched_underlying"
    today = date.today()
    if inst.expiry < today:
        return "expired_contract"
    return None


class OptionInstrumentService:
    """
    Manages option instruments for all underlyings.

    Discovers instruments from the provider, validates them,
    groups by expiry/type/strike, and preserves last valid set
    on refresh failure.
    """

    def __init__(self, provider: OptionDataProvider):
        self._provider = provider
        self._instruments: dict[str, dict[date, dict[OptionType, dict[float, OptionInstrument]]]] = {}
        self._expiry_cache: dict[str, list[date]] = {}
        self._instrument_version: dict[str, int] = {}
        self._last_refresh: dict[str, InstrumentRefreshResult] = {}
        self._lock = asyncio.Lock()

    def get_instruments(
        self,
        underlying: str,
        expiry: date | None = None,
    ) -> tuple[OptionInstrument, ...]:
        norm = _normalize_underlying(underlying)
        by_expiry = self._instruments.get(norm, {})
        if not by_expiry:
            return ()
        if expiry:
            by_type = by_expiry.get(expiry, {})
            result = []
            for by_strike in by_type.values():
                result.extend(by_strike.values())
            return tuple(result)
        result = []
        for by_type in by_expiry.values():
            for by_strike in by_type.values():
                result.extend(by_strike.values())
        return tuple(result)

    def get_available_expiries(self, underlying: str) -> tuple[date, ...]:
        norm = _normalize_underlying(underlying)
        by_expiry = self._instruments.get(norm, {})
        today = date.today()
        future = [e for e in sorted(by_expiry.keys()) if e >= today]
        return tuple(future)

    def find_contract(
        self,
        underlying: str,
        expiry: date,
        strike: float,
        option_type: OptionType,
    ) -> OptionInstrument | None:
        norm = _normalize_underlying(underlying)
        by_type = self._instruments.get(norm, {}).get(expiry, {})
        by_strike = by_type.get(option_type, {})
        return by_strike.get(strike)

    def get_version(self, underlying: str) -> int:
        return self._instrument_version.get(_normalize_underlying(underlying), 0)

    def is_loaded(self, underlying: str | None = None) -> bool:
        if underlying:
            norm = _normalize_underlying(underlying)
            return bool(self._instruments.get(norm))
        return bool(self._instruments)

    def get_last_refresh(self, underlying: str) -> InstrumentRefreshResult | None:
        return self._last_refresh.get(_normalize_underlying(underlying))

    async def refresh(self, underlying: str) -> InstrumentRefreshResult:
        norm = _normalize_underlying(underlying)
        async with self._lock:
            try:
                instruments = await asyncio.wait_for(
                    self._provider.fetch_instruments(norm),
                    timeout=15.0,
                )
            except Exception as e:
                result = InstrumentRefreshResult(
                    success=False, underlying=norm, error=str(e),
                )
                self._last_refresh[norm] = result
                log_warn("InstrumentService refresh failed", underlying=norm, error=str(e))
                return result

            by_expiry: dict[date, dict[OptionType, dict[float, OptionInstrument]]] = {}
            errors: list[str] = []
            seen: set[str] = set()
            for inst in instruments:
                err = _validate_instrument(inst, norm)
                if err:
                    errors.append(f"{inst.key}:{err}")
                    continue
                identity = _contract_identity(inst)
                if identity in seen:
                    errors.append(f"{inst.key}:duplicate")
                    continue
                seen.add(identity)
                by_type = by_expiry.setdefault(inst.expiry, {})
                by_strike = by_type.setdefault(inst.option_type, {})
                by_strike[inst.strike] = inst

            if not by_expiry:
                result = InstrumentRefreshResult(
                    success=False, underlying=norm,
                    error=f"No valid instruments: {'; '.join(errors[:5])}",
                )
                self._last_refresh[norm] = result
                log_warn("InstrumentService: no valid instruments", underlying=norm)
                return result

            self._instruments[norm] = by_expiry
            self._instrument_version[norm] = self._instrument_version.get(norm, 0) + 1
            total = sum(
                len(bs) for bt in by_expiry.values() for bs in bt.values()
            )
            result = InstrumentRefreshResult(
                success=True,
                underlying=norm,
                instrument_count=total,
                expiry_count=len(by_expiry),
            )
            self._last_refresh[norm] = result
            log_info(
                "InstrumentService refresh OK",
                underlying=norm,
                instruments=total,
                expiries=len(by_expiry),
                version=self._instrument_version[norm],
            )
            return result
