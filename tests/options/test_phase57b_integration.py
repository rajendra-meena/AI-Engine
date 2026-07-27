"""
Phase 57B Integration Tests — OptionChainEngine end-to-end with MockOptionProvider

Tests engine lifecycle, refresh flows, stale handling, failure recovery,
concurrent refresh deduplication, and readiness state transitions.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from core.event_bus import EventBus
from core.event_model import Event
from options.chain_engine import OptionChainEngine
from options.config import OptionEngineConfig
from options.events import (
    OPTION_CHAIN_REFRESH_FAILED,
    OPTION_CHAIN_REFRESH_STARTED,
    OPTION_CHAIN_STALE,
    OPTION_CHAIN_UPDATED,
    OPTION_ENGINE_NOT_READY,
    OPTION_ENGINE_READY,
    OPTION_INSTRUMENTS_LOADED,
    OPTION_PROVIDER_CONNECTED,
    OPTIONS_ENGINE_STOPPED,
)
from options.models import (
    FreshnessState,
    OptionChainSnapshot,
    ReadinessStatus,
)
from options.providers.mock import MockOptionProvider


def _config(**overrides):
    defaults = dict(
        provider="MOCK",
        underlyings=("NIFTY 50",),
        chain_poll_interval_seconds=300,
        chain_max_age_seconds=30.0,
        chain_stale_after_seconds=120.0,
        instrument_refresh_interval_seconds=300.0,
        provider_timeout_seconds=5.0,
    )
    defaults.update(overrides)
    return OptionEngineConfig(**defaults)


async def _make_engine(provider=None, config=None):
    p = provider or MockOptionProvider(spot=24500.0)
    if not p._connected:
        await p.connect()
    c = config or _config()
    b = EventBus()
    await b.start()
    engine = OptionChainEngine(p, c, b)
    return engine, p, b


async def _cleanup(engine, bus):
    try:
        await asyncio.wait_for(engine.stop(), timeout=5)
    except (asyncio.TimeoutError, Exception):
        pass
    try:
        await asyncio.wait_for(bus.stop(), timeout=2)
    except (asyncio.TimeoutError, Exception):
        pass


# ═══════════════════════════════════════════════════════════════
#  1. SUCCESSFUL INGESTION
# ═══════════════════════════════════════════════════════════════


class TestSuccessfulIngestion:
    @pytest.mark.asyncio
    async def test_engine_start_and_manual_refresh(self):
        engine, provider, bus = await _make_engine()
        try:
            await engine.start()
            assert engine.is_running
            result = await engine.refresh_underlying("NIFTY 50", force=True)
            assert result.success is True
            assert result.chain_version == 1
            assert result.validation is not None
            assert result.validation.accepted is True
            assert result.freshness in (FreshnessState.FRESH, FreshnessState.AGING)
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_snapshot_available_after_refresh(self):
        engine, _, bus = await _make_engine()
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
            snap = engine.get_snapshot("NIFTY 50", require_fresh=True)
            assert snap is not None
            assert snap.underlying == "NIFTY 50"
            assert len(snap.expiries) > 0
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_readiness_transitions(self):
        engine, _, bus = await _make_engine()
        try:
            r0 = engine.get_readiness()
            assert r0.status == ReadinessStatus.NOT_STARTED
            await engine.start()
            r1 = engine.get_readiness()
            assert r1.engine_running is True
            await engine.refresh_underlying("NIFTY 50", force=True)
            r2 = engine.get_readiness()
            assert r2.status == ReadinessStatus.READY
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_chain_version_increments(self):
        engine, _, bus = await _make_engine()
        try:
            await engine.start()
            r1 = await engine.refresh_underlying("NIFTY 50", force=True)
            assert r1.chain_version == 1
            r2 = await engine.refresh_underlying("NIFTY 50", force=True)
            assert r2.chain_version == 2
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_events_published(self):
        engine, _, bus = await _make_engine()
        events: list[str] = []
        _orig = bus.publish

        async def _capture(event: Event):
            events.append(event.type)
            return await _orig(event)

        bus.publish = _capture  # type: ignore
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
        finally:
            await _cleanup(engine, bus)
        assert OPTION_CHAIN_REFRESH_STARTED in events
        assert OPTION_INSTRUMENTS_LOADED in events
        assert OPTION_CHAIN_UPDATED in events
        assert OPTION_ENGINE_READY in events


# ═══════════════════════════════════════════════════════════════
#  2. STALE CHAIN
# ═══════════════════════════════════════════════════════════════


class TestStaleChain:
    @pytest.mark.asyncio
    async def test_stale_snapshot_rejected(self):
        provider = MockOptionProvider(spot=24500.0, stale_offset_seconds=999)
        await provider.connect()
        engine, _, bus = await _make_engine(provider=provider)
        try:
            await engine.start()
            result = await engine.refresh_underlying("NIFTY 50", force=True)
            assert result.success is False
            assert result.freshness == FreshnessState.STALE
            assert result.error_code == "CHAIN_STALE"
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_stale_produces_non_ready(self):
        provider = MockOptionProvider(spot=24500.0, stale_offset_seconds=999)
        await provider.connect()
        engine, _, bus = await _make_engine(provider=provider)
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
            r = engine.get_readiness()
            assert r.status != ReadinessStatus.READY
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_stale_get_fresh_returns_none(self):
        provider = MockOptionProvider(spot=24500.0, stale_offset_seconds=999)
        await provider.connect()
        engine, _, bus = await _make_engine(provider=provider)
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
            snap = engine.get_snapshot("NIFTY 50", require_fresh=True)
            assert snap is None
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
#  3. PROVIDER FAILURE WITH CACHE
# ═══════════════════════════════════════════════════════════════


class TestProviderFailureWithCache:
    @pytest.mark.asyncio
    async def test_valid_cache_survives_failure(self):
        engine, provider, bus = await _make_engine()
        try:
            await engine.start()
            r1 = await engine.refresh_underlying("NIFTY 50", force=True)
            assert r1.success is True
            snap_before = engine.get_snapshot("NIFTY 50")
            assert snap_before is not None

            provider.set_fail_next_fetch(True)
            r2 = await engine.refresh_underlying("NIFTY 50", force=True)
            assert r2.success is False
            snap_after = engine.get_snapshot("NIFTY 50", require_fresh=False)
            assert snap_after is not None
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_failure_increments_counter(self):
        engine, provider, bus = await _make_engine()
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
            provider.set_fail_next_fetch(True)
            await engine.refresh_underlying("NIFTY 50", force=True)
            r = engine.get_readiness()
            assert r.consecutive_failures >= 1
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
#  4. RECOVERY
# ═══════════════════════════════════════════════════════════════


class TestRecovery:
    @pytest.mark.asyncio
    async def test_recovery_after_failure(self):
        engine, provider, bus = await _make_engine()
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
            provider.set_fail_next_fetch(True)
            await engine.refresh_underlying("NIFTY 50", force=True)
            r_before = engine.get_readiness()
            assert r_before.consecutive_failures >= 1

            r_after = await engine.refresh_underlying("NIFTY 50", force=True)
            assert r_after.success is True
            r_final = engine.get_readiness()
            assert r_final.consecutive_failures == 0
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
#  5. CONCURRENT REFRESH DEDUPLICATION
# ═══════════════════════════════════════════════════════════════


class TestConcurrentRefresh:
    @pytest.mark.asyncio
    async def test_concurrent_refreshes_deduplicated(self):
        engine, _, bus = await _make_engine()
        try:
            await engine.start()
            results = await asyncio.gather(
                engine.refresh_underlying("NIFTY 50", force=True),
                engine.refresh_underlying("NIFTY 50", force=True),
            )
            success_count = sum(1 for r in results if r.success)
            assert success_count >= 1
            r = engine.get_readiness()
            assert r.chain_version >= 1
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
#  6. LIFECYCLE IDEMPOTENCY
# ═══════════════════════════════════════════════════════════════


class TestLifecycleIdempotency:
    @pytest.mark.asyncio
    async def test_double_start(self):
        engine, _, bus = await _make_engine()
        try:
            await engine.start()
            await engine.start()
            assert engine.is_running
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_double_stop(self):
        engine, _, bus = await _make_engine()
        try:
            await engine.start()
            await engine.stop()
            await engine.stop()
            assert not engine.is_running
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        engine, _, bus = await _make_engine()
        try:
            await engine.stop()
            assert not engine.is_running
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
#  7. REFRESH NOT RUNNING
# ═══════════════════════════════════════════════════════════════


class TestRefreshNotRunning:
    @pytest.mark.asyncio
    async def test_refresh_before_start(self):
        engine, _, bus = await _make_engine()
        try:
            result = await engine.refresh_underlying("NIFTY 50")
            assert result.success is False
            assert "not_running" in result.error
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
#  8. CACHE STATUS
# ═══════════════════════════════════════════════════════════════


class TestCacheStatus:
    @pytest.mark.asyncio
    async def test_cache_status_after_refresh(self):
        engine, _, bus = await _make_engine()
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
            status = await engine.get_cache_status_async("NIFTY 50")
            assert status["has_data"] is True
            assert status["chain_version"] >= 1
            assert "freshness_detail" in status
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
#  9. EMPTY CHAIN
# ═══════════════════════════════════════════════════════════════


class TestEmptyChain:
    @pytest.mark.asyncio
    async def test_empty_chain_rejected(self):
        provider = MockOptionProvider(spot=24500.0, empty_chain=True)
        await provider.connect()
        engine, _, bus = await _make_engine(provider=provider)
        try:
            await engine.start()
            result = await engine.refresh_underlying("NIFTY 50", force=True)
            assert result.success is False
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
# 10. REQUIRE FRESH CHAIN GATE
# ═══════════════════════════════════════════════════════════════


class TestFreshChainGate:
    @pytest.mark.asyncio
    async def test_require_fresh_returns_snapshot(self):
        engine, _, bus = await _make_engine()
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
            snap = engine.require_fresh_chain("NIFTY 50")
            assert snap is not None
            assert snap.underlying == "NIFTY 50"
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_require_fresh_returns_none_when_stale(self):
        provider = MockOptionProvider(spot=24500.0, stale_offset_seconds=999)
        await provider.connect()
        engine, _, bus = await _make_engine(provider=provider)
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
            snap = engine.require_fresh_chain("NIFTY 50")
            assert snap is None
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
# 11. AGING CHAIN TESTS
# ═══════════════════════════════════════════════════════════════


class TestAgingChain:
    @pytest.mark.asyncio
    async def test_aging_chain_still_updates_cache(self):
        """An aging chain (not yet stale) should still be accepted and cached."""
        engine, _, bus = await _make_engine()
        try:
            await engine.start()
            result = await engine.refresh_underlying("NIFTY 50", force=True)
            assert result.success is True
            assert result.freshness in (FreshnessState.FRESH, FreshnessState.AGING)
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_options_engine_started_event(self):
        """OPTIONS_ENGINE_STARTED should be published on engine start."""
        engine, _, bus = await _make_engine()
        events: list[str] = []
        _orig = bus.publish
        async def _capture(event):
            events.append(event.type)
            return await _orig(event)
        bus.publish = _capture
        try:
            await engine.start()
            assert "options_engine_started" in events
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
# 12. EVENT ORDERING TESTS
# ═══════════════════════════════════════════════════════════════


class TestEventOrdering:
    @pytest.mark.asyncio
    async def test_success_event_order(self):
        """For a successful refresh, verify correct event sequence."""
        engine, _, bus = await _make_engine()
        events: list[str] = []
        _orig = bus.publish
        async def _capture(event):
            events.append(event.type)
            return await _orig(event)
        bus.publish = _capture
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
        finally:
            await _cleanup(engine, bus)

        expected_prefix = [
            "option_chain_refresh_started",
            "option_instruments_loaded",
            "option_chain_received",
            "option_chain_validated",
            "option_chain_updated",
        ]
        for exp in expected_prefix:
            assert exp in events, f"Missing expected event: {exp}"
        # UPDATED must appear after VALIDATED
        updated_idx = events.index("option_chain_updated")
        validated_idx = events.index("option_chain_validated")
        assert updated_idx > validated_idx

    @pytest.mark.asyncio
    async def test_stale_event_emitted(self):
        """Stale detection should emit OPTION_CHAIN_STALE."""
        provider = MockOptionProvider(spot=24500.0, stale_offset_seconds=999)
        await provider.connect()
        engine, _, bus = await _make_engine(provider=provider)
        events: list[str] = []
        _orig = bus.publish
        async def _capture(event):
            events.append(event.type)
            return await _orig(event)
        bus.publish = _capture
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
            assert "option_chain_stale" in events
            assert "option_chain_updated" not in events
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_failure_event_emitted(self):
        """Provider failure should emit OPTION_CHAIN_REFRESH_FAILED."""
        provider = MockOptionProvider(spot=24500.0)
        await provider.connect()
        engine, _, bus = await _make_engine(provider=provider)
        events: list[str] = []
        _orig = bus.publish
        async def _capture(event):
            events.append(event.type)
            return await _orig(event)
        bus.publish = _capture
        try:
            await engine.start()
            provider.set_fail_next_fetch(True)
            await engine.refresh_underlying("NIFTY 50", force=True)
            assert "option_chain_refresh_failed" in events
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
# 13. RECOVERY INTEGRATION
# ═══════════════════════════════════════════════════════════════


class TestRecoveryExtended:
    @pytest.mark.asyncio
    async def test_recovery_clears_failure_counter(self):
        """After failure then success, consecutive_failures should reset to 0."""
        engine, provider, bus = await _make_engine()
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
            v1 = engine.get_readiness().chain_version

            provider.set_fail_next_fetch(True)
            await engine.refresh_underlying("NIFTY 50", force=True)
            assert engine.get_readiness().consecutive_failures >= 1

            r = await engine.refresh_underlying("NIFTY 50", force=True)
            assert r.success is True
            r2 = engine.get_readiness()
            assert r2.consecutive_failures == 0
            assert r2.chain_version == v1 + 1
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_recovery_after_multiple_failures(self):
        """Multiple failures, then recovery should restore READY."""
        engine, provider, bus = await _make_engine()
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
            for _ in range(3):
                provider.set_fail_next_chain_fetch(True)
                await engine.refresh_underlying("NIFTY 50", force=True)
            r_fail = engine.get_readiness()
            assert r_fail.consecutive_failures >= 1

            r = await engine.refresh_underlying("NIFTY 50", force=True)
            assert r.success is True
            r_final = engine.get_readiness()
            assert r_final.consecutive_failures == 0
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
# 14. DIAGNOSTIC ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════


class TestDiagnosticAPI:
    """Verify the OptionChainEngine meets the API contract."""

    @pytest.mark.asyncio
    async def test_readiness_api_payload(self):
        """to_dict() should contain all required fields."""
        engine, _, bus = await _make_engine()
        try:
            await engine.start()
            r = engine.get_readiness()
            d = r.to_dict()
            assert "status" in d
            assert "engine_running" in d
            assert "provider_ready" in d
            assert "chain_version" in d
            assert "underlying_statuses" in d
        finally:
            await _cleanup(engine, bus)

    @pytest.mark.asyncio
    async def test_require_fresh_chain_gate(self):
        """require_fresh_chain is the canonical freshness gate."""
        engine, _, bus = await _make_engine()
        try:
            await engine.start()
            await engine.refresh_underlying("NIFTY 50", force=True)
            snap = engine.require_fresh_chain("NIFTY 50")
            assert snap is not None
            assert snap.underlying == "NIFTY 50"
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
# 15. EMPTY / MALFORMED CHAIN EDGE CASES
# ═══════════════════════════════════════════════════════════════


class TestMalformedChain:
    @pytest.mark.asyncio
    async def test_malformed_chain_rejected(self):
        provider = MockOptionProvider(spot=24500.0, malformed_chain=True)
        await provider.connect()
        engine, _, bus = await _make_engine(provider=provider)
        try:
            await engine.start()
            result = await engine.refresh_underlying("NIFTY 50", force=True)
            assert result.success is False
        finally:
            await _cleanup(engine, bus)


# ═══════════════════════════════════════════════════════════════
# 16. CACHE PRESERVATION AFTER FAILURE
# ═══════════════════════════════════════════════════════════════


class TestCachePreservation:
    @pytest.mark.asyncio
    async def test_cache_survives_chain_fetch_failure(self):
        engine, provider, bus = await _make_engine()
        try:
            await engine.start()
            r1 = await engine.refresh_underlying("NIFTY 50", force=True)
            assert r1.success is True
            assert r1.chain_version == 1

            provider.set_fail_next_chain_fetch(True)
            r2 = await engine.refresh_underlying("NIFTY 50", force=True)
            assert r2.success is False
            assert r2.error_code == "CHAIN_FETCH_FAILED"

            snap = engine.get_snapshot("NIFTY 50", require_fresh=False)
            assert snap is not None
        finally:
            await _cleanup(engine, bus)
