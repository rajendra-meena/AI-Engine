"""
MarketMind AI — Option Chain Cache

Async-safe cache for option chain snapshots.
Stores immutable snapshots with versioning, freshness tracking,
and diagnostics. Never overwrites valid data with empty/failed data.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Any

from options.models import (
    FreshnessInfo,
    FreshnessState,
    OptionChainCacheStatus,
    OptionChainSnapshot,
)

from utils.logger import log_info, log_warn


class _CacheEntry:
    __slots__ = (
        "snapshot", "chain_version", "received_at",
        "last_success_at", "last_attempt_at", "last_error",
        "consecutive_failures",
    )

    def __init__(self) -> None:
        self.snapshot: OptionChainSnapshot | None = None
        self.chain_version: int = 0
        self.received_at: datetime | None = None
        self.last_success_at: datetime | None = None
        self.last_attempt_at: datetime | None = None
        self.last_error: str = ""
        self.consecutive_failures: int = 0


class OptionChainCache:
    """
    Async-safe cache for option chain snapshots.

    Keys: (underlying, expiry) where expiry=None means latest.
    Never mutates cached snapshots. Never overwrites valid data with empty.
    """

    def __init__(
        self,
        max_age_seconds: float = 15.0,
        stale_after_seconds: float = 60.0,
    ):
        self._max_age = max_age_seconds
        self._stale_after = stale_after_seconds
        self._entries: dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def put(self, snapshot: OptionChainSnapshot) -> None:
        key = snapshot.underlying
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                entry = _CacheEntry()
                self._entries[key] = entry
            entry.snapshot = snapshot
            entry.chain_version += 1
            entry.received_at = datetime.now(timezone.utc)
            entry.last_success_at = entry.received_at
            entry.last_error = ""
            entry.consecutive_failures = 0

    async def get(
        self,
        underlying: str,
        expiry: date | None = None,
    ) -> OptionChainSnapshot | None:
        async with self._lock:
            entry = self._entries.get(underlying)
            if entry is None or entry.snapshot is None:
                return None
            if expiry is not None:
                s = entry.snapshot.get_slice(expiry)
                return entry.snapshot if s is not None else None
            return entry.snapshot

    async def get_fresh(
        self,
        underlying: str,
        expiry: date | None = None,
        now: datetime | None = None,
    ) -> OptionChainSnapshot | None:
        snapshot = await self.get(underlying, expiry)
        if snapshot is None:
            return None
        fi = self._compute_freshness(snapshot, now)
        if fi.state in (FreshnessState.FRESH, FreshnessState.AGING):
            return snapshot
        return None

    async def get_status(self, underlying: str) -> OptionChainCacheStatus:
        async with self._lock:
            entry = self._entries.get(underlying)
            if entry is None or entry.snapshot is None:
                return OptionChainCacheStatus(
                    underlying=underlying, has_data=False,
                    freshness=FreshnessState.UNAVAILABLE,
                )
            snap = entry.snapshot
            fi = self._compute_freshness(snap)
            contract_count = 0
            for s in snap.expiries.values():
                contract_count += len(s.ce_quotes) + len(s.pe_quotes)
            return OptionChainCacheStatus(
                underlying=underlying,
                has_data=True,
                chain_version=entry.chain_version,
                freshness=fi.state,
                data_age_seconds=fi.age_seconds,
                last_success_at=entry.last_success_at,
                last_attempt_at=entry.last_attempt_at,
                last_error=entry.last_error,
                consecutive_failures=entry.consecutive_failures,
                expiry_count=len(snap.expiries),
                contract_count=contract_count,
            )

    async def record_attempt(
        self,
        underlying: str,
        success: bool,
        error: str = "",
    ) -> None:
        async with self._lock:
            entry = self._entries.get(underlying)
            if entry is None:
                entry = _CacheEntry()
                self._entries[underlying] = entry
            entry.last_attempt_at = datetime.now(timezone.utc)
            if success:
                entry.last_error = ""
                entry.consecutive_failures = 0
            else:
                entry.last_error = error
                entry.consecutive_failures += 1

    async def invalidate(self, underlying: str, reason: str = "") -> None:
        async with self._lock:
            entry = self._entries.get(underlying)
            if entry is not None:
                entry.last_error = f"invalidated: {reason}"
                log_warn("Cache invalidated", underlying=underlying, reason=reason)

    async def get_chain_version(self, underlying: str) -> int:
        async with self._lock:
            entry = self._entries.get(underlying)
            return entry.chain_version if entry else 0

    def compute_freshness(
        self,
        underlying: str,
        now: datetime | None = None,
    ) -> FreshnessInfo:
        entry = self._entries.get(underlying)
        if entry is None or entry.snapshot is None:
            return FreshnessInfo(state=FreshnessState.UNAVAILABLE)
        return self._compute_freshness(entry.snapshot, now)

    def compute_freshness_from_snapshot(
        self,
        snapshot: OptionChainSnapshot,
        now: datetime | None = None,
    ) -> FreshnessInfo:
        return self._compute_freshness(snapshot, now)

    def get_now(
        self,
        underlying: str,
        expiry: date | None = None,
    ) -> OptionChainSnapshot | None:
        entry = self._entries.get(underlying)
        if entry is None or entry.snapshot is None:
            return None
        if expiry is not None:
            s = entry.snapshot.get_slice(expiry)
            return entry.snapshot if s is not None else None
        return entry.snapshot

    def get_fresh_now(
        self,
        underlying: str,
        expiry: date | None = None,
        now: datetime | None = None,
    ) -> OptionChainSnapshot | None:
        snapshot = self.get_now(underlying, expiry)
        if snapshot is None:
            return None
        fi = self._compute_freshness(snapshot, now)
        if fi.state in (FreshnessState.FRESH, FreshnessState.AGING):
            return snapshot
        return None

    def _compute_freshness(
        self,
        snapshot: OptionChainSnapshot,
        now: datetime | None = None,
    ) -> FreshnessInfo:
        now = now or datetime.now(timezone.utc)
        ts = snapshot.fetched_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        age = max((now - ts).total_seconds(), 0.0)

        if age <= self._max_age:
            state = FreshnessState.FRESH
        elif age <= self._stale_after:
            state = FreshnessState.AGING
        else:
            state = FreshnessState.STALE

        return FreshnessInfo(
            state=state,
            age_seconds=age,
            max_age_seconds=self._max_age,
            stale_after_seconds=self._stale_after,
            timestamp_source="fetched_at",
            fetched_at=ts,
        )
