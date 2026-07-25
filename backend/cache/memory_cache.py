"""
MarketMind AI — In-Memory Cache

A generic, TTL-based, async-safe in-memory cache. Used as L1 cache
between MarketDataService and the data providers.

Design:
  - Simple dict-based storage with per-key TTL
  - asyncio.Lock for thread-safe concurrent access
  - Bounded by max_items (LRU eviction when full)
  - Statistics tracking (hits, misses, hit ratio, expired entries)

This is NOT:
  - A distributed cache (no Redis)
  - A persistent cache (no disk writes)
  - An automatic refresh mechanism (no background workers)

Usage:
    cache = MemoryCache()
    await cache.set("my_key", {"data": [1,2,3]}, ttl_seconds=60)
    value = await cache.get("my_key")
    stats = cache.get_stats()
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any
from collections import OrderedDict

from core.constants import (
    MEMORY_CACHE_TTL_DEFAULT,
    MEMORY_CACHE_MAX_ITEMS,
)
from utils.logger import log_info, log_warn


@dataclass
class CacheEntry:
    """A single cache entry with TTL tracking."""

    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = MEMORY_CACHE_TTL_DEFAULT
    last_access: float = field(default_factory=time.time)
    access_count: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if this entry has exceeded its TTL."""
        return (time.time() - self.created_at) > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        """How long this entry has been alive."""
        return time.time() - self.created_at


@dataclass
class CacheStats:
    """Aggregate cache performance statistics."""

    hits: int = 0
    misses: int = 0
    expired_hits: int = 0
    evictions: int = 0
    sets: int = 0
    deletes: int = 0
    clears: int = 0

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return round(self.hits / total * 100, 1)

    @property
    def effective_hit_ratio(self) -> float:
        """Hit ratio excluding expired entries (they're still cache misses)."""
        effective_hits = self.hits - self.expired_hits
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return round(max(effective_hits, 0) / total * 100, 1)


class MemoryCache:
    """
    Generic in-memory cache with TTL, LRU eviction, and stats.

    Thread-safe via asyncio.Lock. All public methods are awaitable.
    """

    def __init__(self, max_items: int = MEMORY_CACHE_MAX_ITEMS):
        self._store: dict[str, CacheEntry] = OrderedDict()
        self._max_items = max_items
        self._lock = asyncio.Lock()
        self._stats = CacheStats()

    # ── Core operations ──

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from the cache.

        Returns the cached value, or `default` if the key doesn't exist
        or the entry has expired. Expired entries are removed on access.
        """
        async with self._lock:
            entry = self._store.get(key)

            if entry is None:
                self._stats.misses += 1
                return default

            if entry.is_expired:
                self._stats.expired_hits += 1
                self._stats.misses += 1
                del self._store[key]
                return default

            # Move to end (LRU: mark as recently used)
            self._store.move_to_end(key)
            entry.last_access = time.time()
            entry.access_count += 1
            self._stats.hits += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: float | None = None):
        """
        Store a value in the cache.

        Args:
            key: Cache key (use cache_keys module for consistency).
            value: Any pickle-safe object.
            ttl_seconds: Time-to-live in seconds. Uses default if None.
        """
        async with self._lock:
            if key not in self._store and len(self._store) >= self._max_items:
                self._evict_lru()

            self._store[key] = CacheEntry(
                key=key,
                value=value,
                ttl_seconds=(
                    ttl_seconds if ttl_seconds is not None else MEMORY_CACHE_TTL_DEFAULT
                ),
            )
            self._stats.sets += 1

    async def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._store[key]
                return False
            return True

    async def delete(self, key: str) -> bool:
        """Delete a single key. Returns True if it existed."""
        async with self._lock:
            if key in self._store:
                del self._store[key]
                self._stats.deletes += 1
                return True
            return False

    async def invalidate(self, pattern: str | None = None):
        """
        Invalidate cache entries matching a pattern.

        Pattern format uses simple wildcard matching:
          \"*\" matches anything
          \"*:{symbol}:*\" matches all keys for a symbol
          \"intraday:*:{interval}\" matches all keys for an interval

        If pattern is None, clears everything.
        """
        async with self._lock:
            if pattern is None:
                self._store.clear()
                self._stats.clears += 1
                log_info("MemoryCache: invalidated all entries")
                return

            to_delete = [k for k in self._store if self._match_pattern(k, pattern)]
            for k in to_delete:
                del self._store[k]

            if to_delete:
                log_info(
                    "MemoryCache: invalidated entries",
                    pattern=pattern,
                    count=len(to_delete),
                )

    async def clear(self):
        """Clear all cached entries."""
        await self.invalidate()

    async def refresh_ttl(self, key: str, ttl_seconds: float | None = None):
        """Reset the TTL timer on an existing entry without changing its value."""
        async with self._lock:
            entry = self._store.get(key)
            if entry and not entry.is_expired:
                entry.created_at = time.time()
                if ttl_seconds is not None:
                    entry.ttl_seconds = ttl_seconds

    # ── Statistics ──

    def get_stats(self) -> dict[str, Any]:
        """Return cache performance statistics."""
        active = sum(1 for e in self._store.values() if not e.is_expired)
        expired = sum(1 for e in self._store.values() if e.is_expired)
        return {
            "active_entries": active,
            "expired_entries": expired,
            "max_items": self._max_items,
            "usage_percent": (
                round((active + expired) / self._max_items * 100, 1)
                if self._max_items
                else 0
            ),
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "hit_ratio": self._stats.hit_ratio,
            "effective_hit_ratio": self._stats.effective_hit_ratio,
            "expired_hits": self._stats.expired_hits,
            "evictions": self._stats.evictions,
            "total_sets": self._stats.sets,
            "total_deletes": self._stats.deletes,
        }

    def get_keys(self) -> list[str]:
        """Return all active (non-expired) cache keys."""
        return [k for k, e in list(self._store.items()) if not e.is_expired]

    # ── Internal helpers ──

    def _evict_lru(self):
        """Remove the least recently used entry (first in OrderedDict)."""
        if self._store:
            self._store.popitem(last=False)
            self._stats.evictions += 1

    @staticmethod
    def _match_pattern(key: str, pattern: str) -> bool:
        """Simple wildcard matching for cache key patterns."""
        if pattern == "*":
            return True
        parts = pattern.split("*")
        pos = 0
        for i, part in enumerate(parts):
            if not part:
                continue
            if i == 0:
                if not key.startswith(part):
                    return False
                pos = len(part)
            else:
                found = key.find(part, pos)
                if found == -1:
                    return False
                pos = found + len(part)
        if not pattern.endswith("*") and pos != len(key):
            return False
        return True
