"""
MarketMind AI — Option Engine Readiness Tracker

Maintains the canonical readiness state for the Options Engine.
Combines provider health, instrument status, chain freshness,
and error history into a single readiness snapshot.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from options.models import (
    FreshnessState,
    OptionEngineReadiness,
    ReadinessStatus,
)

from utils.logger import log_info


class ReadinessTracker:
    """
    Tracks and computes the readiness state of the Options Engine.

    Thread-safe via simple attribute access (single event loop assumed).
    """

    def __init__(self) -> None:
        self._engine_running = False
        self._provider_ready = False
        self._instruments_loaded: set[str] = set()
        self._chain_available: set[str] = set()
        self._chain_fresh: set[str] = set()
        self._freshness: dict[str, FreshnessState] = {}
        self._blocked_reasons: list[str] = []
        self._warnings: list[str] = []
        self._last_success_at: datetime | None = None
        self._last_attempt_at: datetime | None = None
        self._last_error: str = ""
        self._consecutive_failures: int = 0
        self._chain_version: dict[str, int] = {}

    def set_engine_running(self, running: bool) -> None:
        self._engine_running = running

    def set_provider_ready(self, ready: bool) -> None:
        self._provider_ready = ready

    def set_instruments_loaded(self, underlying: str, loaded: bool) -> None:
        if loaded:
            self._instruments_loaded.add(underlying)
        else:
            self._instruments_loaded.discard(underlying)

    def set_chain_available(self, underlying: str, available: bool) -> None:
        if available:
            self._chain_available.add(underlying)
        else:
            self._chain_available.discard(underlying)

    def set_chain_fresh(self, underlying: str, fresh: bool) -> None:
        if fresh:
            self._chain_fresh.add(underlying)
        else:
            self._chain_fresh.discard(underlying)

    def set_freshness(self, underlying: str, state: FreshnessState) -> None:
        self._freshness[underlying] = state

    def set_chain_version(self, underlying: str, version: int) -> None:
        self._chain_version[underlying] = version

    def record_success(self) -> None:
        self._last_success_at = datetime.now(timezone.utc)
        self._consecutive_failures = 0
        self._last_error = ""

    def record_attempt(self) -> None:
        self._last_attempt_at = datetime.now(timezone.utc)

    def record_failure(self, error: str) -> None:
        self._last_error = error
        self._consecutive_failures += 1

    def add_warning(self, warning: str) -> None:
        if warning not in self._warnings:
            self._warnings.append(warning)

    def clear_warning(self, warning: str) -> None:
        self._warnings = [w for w in self._warnings if w != warning]

    def reset(self) -> None:
        self._engine_running = False
        self._provider_ready = False
        self._instruments_loaded.clear()
        self._chain_available.clear()
        self._chain_fresh.clear()
        self._freshness.clear()
        self._blocked_reasons.clear()
        self._warnings.clear()
        self._last_success_at = None
        self._last_attempt_at = None
        self._last_error = ""
        self._consecutive_failures = 0
        self._chain_version.clear()

    def compute(
        self,
        underlyings: tuple[str, ...] = (),
    ) -> OptionEngineReadiness:
        blocked: list[str] = []
        if not self._engine_running:
            blocked.append("OPTION_ENGINE_NOT_RUNNING")
        if not self._provider_ready:
            blocked.append("OPTION_PROVIDER_UNAVAILABLE")

        all_instruments = self._instruments_loaded
        all_chain_avail = self._chain_available
        all_chain_fresh = self._chain_fresh

        if underlyings:
            for u in underlyings:
                if u not in all_instruments:
                    blocked.append("OPTION_INSTRUMENTS_NOT_LOADED")
                    break
            for u in underlyings:
                if u not in all_chain_avail:
                    blocked.append("OPTION_CHAIN_UNAVAILABLE")
                    break
            for u in underlyings:
                fu = self._freshness.get(u, FreshnessState.UNKNOWN)
                if fu == FreshnessState.STALE:
                    blocked.append("OPTION_CHAIN_STALE")
                    break
                if fu not in (FreshnessState.FRESH, FreshnessState.AGING):
                    blocked.append("OPTION_CHAIN_UNAVAILABLE")
                    break
        else:
            if not all_instruments:
                blocked.append("OPTION_INSTRUMENTS_NOT_LOADED")
            if not all_chain_avail:
                blocked.append("OPTION_CHAIN_UNAVAILABLE")

        if blocked:
            if self._consecutive_failures > 0 and self._provider_ready is False:
                status = ReadinessStatus.PROVIDER_ERROR
            elif any("STALE" in r for r in blocked):
                status = ReadinessStatus.STALE
            elif self._engine_running and self._consecutive_failures > 3:
                status = ReadinessStatus.DEGRADED
            else:
                status = ReadinessStatus.NOT_STARTED if not self._engine_running else ReadinessStatus.WAITING_FOR_CHAIN
        else:
            status = ReadinessStatus.READY

        overall_freshness = FreshnessState.UNKNOWN
        if self._freshness:
            states = list(self._freshness.values())
            if all(s == FreshnessState.FRESH for s in states):
                overall_freshness = FreshnessState.FRESH
            elif any(s == FreshnessState.STALE for s in states):
                overall_freshness = FreshnessState.STALE
            elif any(s == FreshnessState.AGING for s in states):
                overall_freshness = FreshnessState.AGING
            else:
                overall_freshness = states[0]

        chain_v = max(self._chain_version.values()) if self._chain_version else 0
        underlyings_status = {}
        for u in (underlyings or self._instruments_loaded):
            fu = self._freshness.get(u, FreshnessState.UNKNOWN)
            underlyings_status[u] = fu.value

        return OptionEngineReadiness(
            engine_running=self._engine_running,
            provider_ready=self._provider_ready,
            instruments_loaded=bool(self._instruments_loaded),
            chain_available=bool(self._chain_available),
            chain_fresh=bool(self._chain_fresh),
            freshness=overall_freshness,
            status=status,
            blocked_reasons=tuple(blocked),
            warnings=tuple(self._warnings),
            last_success_at=self._last_success_at,
            last_attempt_at=self._last_attempt_at,
            last_error=self._last_error,
            consecutive_failures=self._consecutive_failures,
            chain_version=chain_v,
            underlying_statuses=underlyings_status,
        )
