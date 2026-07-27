"""
MarketMind AI — Option Chain Engine

Singleton engine responsible for:
- Instrument discovery
- Expiry discovery
- Chain fetching with freshness validation
- Structural validation
- Cache management
- Readiness tracking
- EventBus publication
- Adaptive refresh loops with deduplication
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import date, datetime, timezone
from typing import Any

from core.event_bus import EventBus
from core.event_model import Event, EventPriority
from options.cache import OptionChainCache
from options.config import OptionEngineConfig
from options.events import (
    OPTIONS_ENGINE_ERROR,
    OPTIONS_ENGINE_STARTED,
    OPTIONS_ENGINE_STOPPED,
    OPTION_ENGINE_READY,
    OPTION_ENGINE_DEGRADED,
    OPTION_ENGINE_NOT_READY,
    OPTION_INSTRUMENTS_LOADED,
    OPTION_INSTRUMENTS_REFRESH_FAILED,
    OPTION_INSTRUMENTS_REFRESH_STARTED,
    OPTION_CHAIN_AGING,
    OPTION_CHAIN_REFRESH_STARTED,
    OPTION_CHAIN_RECEIVED,
    OPTION_CHAIN_VALIDATED,
    OPTION_CHAIN_UPDATED,
    OPTION_CHAIN_STALE,
    OPTION_CHAIN_REFRESH_FAILED,
    OPTION_PROVIDER_CONNECTED,
    OPTION_PROVIDER_DEGRADED,
    OPTION_PROVIDER_DISCONNECTED,
)
from options.instrument_service import OptionInstrumentService, _normalize_underlying
from options.models import (
    ChainValidationResult,
    FreshnessState,
    OptionChainRefreshResult,
    OptionChainSnapshot,
    OptionEngineReadiness,
    ReadinessStatus,
)
from options.providers.base import OptionDataProvider
from options.readiness import ReadinessTracker

from utils.logger import log_info, log_warn, log_error


class _CacheEntryStub:
    """Minimal stub to safely read chain_version when no entry exists."""
    chain_version = 0


def _validate_chain_snapshot(
    snapshot: OptionChainSnapshot,
    expected_underlying: str,
) -> ChainValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if snapshot.underlying != expected_underlying:
        errors.append(f"underlying_mismatch: expected {expected_underlying}, got {snapshot.underlying}")

    if not snapshot.expiries:
        errors.append("no_expiries")
        return ChainValidationResult(
            accepted=False, errors=tuple(errors), contract_count=0,
        )

    if snapshot.spot_price <= 0:
        errors.append("invalid_spot_price")

    if snapshot.fetched_at.tzinfo is None:
        warnings.append("missing_timezone_info")

    now = datetime.now(timezone.utc)
    if snapshot.fetched_at.tzinfo is not None:
        if snapshot.fetched_at > now + __import__("datetime").timedelta(minutes=5):
            errors.append("impossibly_future_timestamp")

    total = 0
    ce_count = 0
    pe_count = 0
    invalid = 0
    seen: set[str] = set()

    def _check_quote(strike: float, q: Any, opt_type: str) -> None:
        nonlocal invalid
        is_invalid = False
        if q.ltp < 0:
            errors.append(f"negative_premium_{opt_type}_{strike}")
            is_invalid = True
        if q.oi < 0:
            errors.append(f"negative_oi_{opt_type}_{strike}")
            is_invalid = True
        if q.volume < 0:
            errors.append(f"negative_volume_{opt_type}_{strike}")
            is_invalid = True
        if q.instrument.option_type.value != opt_type:
            errors.append(f"type_mismatch_{opt_type}_{strike}")
            is_invalid = True
        if q.instrument.strike < 0:
            errors.append(f"negative_instrument_strike_{opt_type}_{strike}")
            is_invalid = True
        if q.instrument.instrument_token <= 0:
            errors.append(f"invalid_token_{opt_type}_{strike}")
            is_invalid = True
        if q.bid > 0 and q.ask > 0 and q.bid > q.ask:
            errors.append(f"bid_gt_ask_{opt_type}_{strike}")
            is_invalid = True
        identity = f"{s.underlying}|{expiry}|{strike:.0f}|{opt_type}|{q.instrument.instrument_token}"
        if identity in seen:
            errors.append(f"duplicate_contract_{identity}")
            is_invalid = True
        seen.add(identity)
        if q.iv is None:
            warnings.append(f"missing_iv_{opt_type}_{strike}")
        if q.delta is None:
            warnings.append(f"missing_delta_{opt_type}_{strike}")
        if is_invalid:
            invalid += 1

    for expiry, s in snapshot.expiries.items():
        if not s.ce_quotes and not s.pe_quotes:
            warnings.append(f"empty_expiry_{expiry}")
            continue

        if not s.ce_quotes:
            errors.append(f"no_ce_contracts_{expiry}")
        if not s.pe_quotes:
            errors.append(f"no_pe_contracts_{expiry}")

        ce_count += len(s.ce_quotes)
        pe_count += len(s.pe_quotes)
        total += len(s.ce_quotes) + len(s.pe_quotes)

        for strike, q in s.ce_quotes.items():
            _check_quote(strike, q, "CE")
        for strike, q in s.pe_quotes.items():
            _check_quote(strike, q, "PE")

    return ChainValidationResult(
        accepted=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        contract_count=total,
        ce_count=ce_count,
        pe_count=pe_count,
        expiry_count=len(snapshot.expiries),
        invalid_contract_count=invalid,
    )


class OptionChainEngine:
    """
    Singleton engine for option chain ingestion, validation, caching, and readiness.

    Usage:
        engine = OptionChainEngine(provider, config, event_bus)
        await engine.start()
        snap = engine.get_snapshot("NIFTY 50")
        await engine.stop()
    """

    def __init__(
        self,
        provider: OptionDataProvider,
        config: OptionEngineConfig,
        event_bus: EventBus | None = None,
    ):
        self._provider = provider
        self._config = config
        self._event_bus = event_bus
        self._instrument_service = OptionInstrumentService(provider)
        self._cache = OptionChainCache(
            max_age_seconds=config.chain_max_age_seconds,
            stale_after_seconds=config.chain_stale_after_seconds,
        )
        self._readiness = ReadinessTracker()
        self._running = False
        self._refresh_tasks: dict[str, asyncio.Task] = {}
        self._loop_tasks: list[asyncio.Task] = []
        self._main_loop_task: asyncio.Task | None = None
        self._inflight: dict[str, asyncio.Task] = {}
        self._backoff: dict[str, float] = {}
        self._provider_connected = False
        self._engine_lock = asyncio.Lock()

    # ── Lifecycle ──

    async def start(self) -> None:
        if self._running:
            return
        async with self._engine_lock:
            if self._running:
                return
            self._running = True
            self._readiness.set_engine_running(True)

            try:
                connected = await asyncio.wait_for(
                    self._provider.connect(),
                    timeout=self._config.provider_timeout_seconds,
                )
                self._provider_connected = connected
                self._readiness.set_provider_ready(connected)
                if connected:
                    await self._publish(OPTION_PROVIDER_CONNECTED, {})
                else:
                    await self._publish(OPTION_PROVIDER_DISCONNECTED, {})
            except Exception as e:
                self._provider_connected = False
                self._readiness.set_provider_ready(False)
                await self._publish(OPTION_PROVIDER_DISCONNECTED, {"error": str(e)})

            await self._publish(OPTIONS_ENGINE_STARTED, {
                "underlyings": list(self._config.underlyings),
            })

            for underlying in self._config.underlyings:
                task = asyncio.create_task(
                    self._refresh_instruments_loop(underlying),
                    name=f"instruments_{underlying}",
                )
                self._loop_tasks.append(task)

            self._main_loop_task = asyncio.create_task(
                self._main_refresh_loop(),
                name="options_chain_main_loop",
            )
            self._loop_tasks.append(self._main_loop_task)
            log_info("OptionChainEngine started", underlyings=list(self._config.underlyings))
            await self._publish(OPTION_ENGINE_NOT_READY, {"reason": "starting"})

    async def stop(self) -> None:
        if not self._running:
            return
        async with self._engine_lock:
            if not self._running:
                return
            self._running = False
            self._readiness.set_engine_running(False)

            for task in self._loop_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            self._loop_tasks.clear()

            for task in self._refresh_tasks.values():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            self._refresh_tasks.clear()

            try:
                await self._provider.disconnect()
            except Exception:
                pass
            self._provider_connected = False

            log_info("OptionChainEngine stopped")
            await self._publish(OPTIONS_ENGINE_STOPPED, {})

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Public API ──

    async def refresh_underlying(
        self,
        underlying: str,
        *,
        force: bool = False,
        analysis_cycle_id: str = "",
    ) -> OptionChainRefreshResult:
        norm = _normalize_underlying(underlying)
        if not self._running:
            return OptionChainRefreshResult(
                success=False, underlying=norm, error="engine_not_running",
            )

        if norm in self._inflight and not force:
            try:
                await asyncio.wait_for(asyncio.shield(self._inflight[norm]), timeout=30.0)
                status = await self._cache.get_status(norm)
                return OptionChainRefreshResult(
                    success=status.has_data,
                    underlying=norm,
                    chain_version=status.chain_version,
                    freshness=status.freshness,
                )
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        return await self._do_refresh(norm, force=force, analysis_cycle_id=analysis_cycle_id)

    def get_snapshot(
        self,
        underlying: str,
        expiry: date | None = None,
        *,
        require_fresh: bool = True,
    ) -> OptionChainSnapshot | None:
        norm = _normalize_underlying(underlying)
        if require_fresh:
            return self._cache.get_fresh_now(norm, expiry)
        entry = self._cache.get_now(norm, expiry)
        return entry

    def require_fresh_chain(
        self,
        underlying: str,
        expiry: date | None = None,
    ) -> OptionChainSnapshot | None:
        norm = _normalize_underlying(underlying)
        snap = self._cache.get_fresh_now(norm, expiry)
        return snap

    def get_readiness(
        self,
        underlying: str | None = None,
    ) -> OptionEngineReadiness:
        underlyings = self._config.underlyings if underlying is None else (underlying,)
        return self._readiness.compute(underlyings)

    def get_cache_status(self, underlying: str) -> dict[str, Any]:
        norm = _normalize_underlying(underlying)
        import asyncio as _asyncio
        try:
            loop = _asyncio.get_running_loop()
            return {"error": "use async get_cache_status_async"}
        except RuntimeError:
            pass
        return {}

    async def get_cache_status_async(self, underlying: str) -> dict[str, Any]:
        norm = _normalize_underlying(underlying)
        status = await self._cache.get_status(norm)
        fi = self._cache.compute_freshness(norm)
        result = status.to_dict()
        result["freshness_detail"] = fi.to_dict()
        return result

    def get_instrument_service(self) -> OptionInstrumentService:
        return self._instrument_service

    def get_cache(self) -> OptionChainCache:
        return self._cache

    # ── Internal ──

    async def _do_refresh(
        self,
        underlying: str,
        *,
        force: bool = False,
        analysis_cycle_id: str = "",
    ) -> OptionChainRefreshResult:
        start = time.monotonic()
        event_id = uuid.uuid4().hex[:12]
        await self._publish(OPTION_CHAIN_REFRESH_STARTED, {
            "event_id": event_id,
            "underlying": underlying,
            "analysis_cycle_id": analysis_cycle_id,
        })
        self._readiness.record_attempt()

        task = asyncio.ensure_future(self._fetch_and_process(underlying, analysis_cycle_id))
        self._inflight[underlying] = task
        try:
            result = await task
        finally:
            self._inflight.pop(underlying, None)

        result = OptionChainRefreshResult(
            success=result.success,
            underlying=result.underlying,
            chain_version=result.chain_version,
            instrument_version=result.instrument_version,
            validation=result.validation,
            freshness=result.freshness,
            error=result.error,
            error_code=result.error_code,
            duration_ms=(time.monotonic() - start) * 1000,
            timestamp=result.timestamp,
            analysis_cycle_id=analysis_cycle_id,
        )

        if result.success:
            self._readiness.record_success()
            self._backoff.pop(underlying, None)
        else:
            self._readiness.record_failure(result.error)

        r = self._readiness.compute(self._config.underlyings)
        if r.status == ReadinessStatus.READY:
            await self._publish(OPTION_ENGINE_READY, r.to_dict())
        elif r.status == ReadinessStatus.DEGRADED:
            await self._publish(OPTION_ENGINE_DEGRADED, r.to_dict())
        else:
            await self._publish(OPTION_ENGINE_NOT_READY, r.to_dict())

        return result

    async def _fetch_and_process(
        self,
        underlying: str,
        analysis_cycle_id: str,
    ) -> OptionChainRefreshResult:
        try:
            ir = await asyncio.wait_for(
                self._instrument_service.refresh(underlying),
                timeout=self._config.provider_timeout_seconds,
            )
        except Exception as e:
            self._readiness.set_instruments_loaded(underlying, False)
            return OptionChainRefreshResult(
                success=False, underlying=underlying,
                error=f"instrument_refresh_failed: {e}",
                error_code="INSTRUMENT_REFRESH_FAILED",
            )

        if not ir.success:
            self._readiness.set_instruments_loaded(underlying, False)
            return OptionChainRefreshResult(
                success=False, underlying=underlying,
                error=f"instrument_refresh_failed: {ir.error}",
                error_code="INSTRUMENT_REFRESH_FAILED",
            )

        self._readiness.set_instruments_loaded(underlying, True)
        if ir and ir.success:
            await self._publish(OPTION_INSTRUMENTS_LOADED, {
                "underlying": underlying,
                "instrument_count": ir.instrument_count,
                "expiry_count": ir.expiry_count,
                "instrument_version": self._instrument_service.get_version(underlying),
            })

        try:
            snapshot = await asyncio.wait_for(
                self._provider.fetch_chain_snapshot(underlying),
                timeout=self._config.provider_timeout_seconds,
            )
        except Exception as e:
            await self._cache.record_attempt(underlying, False, str(e))
            await self._publish(OPTION_CHAIN_REFRESH_FAILED, {
                "underlying": underlying,
                "error": str(e),
                "analysis_cycle_id": analysis_cycle_id,
            })
            return OptionChainRefreshResult(
                success=False, underlying=underlying,
                error=str(e), error_code="CHAIN_FETCH_FAILED",
            )

        await self._publish(OPTION_CHAIN_RECEIVED, {
            "underlying": underlying,
            "expiry_count": len(snapshot.expiries),
            "analysis_cycle_id": analysis_cycle_id,
        })

        validation = _validate_chain_snapshot(snapshot, underlying)
        if not validation.accepted:
            await self._cache.record_attempt(
                underlying, False,
                f"validation_failed: {'; '.join(validation.errors[:3])}",
            )
            await self._publish(OPTION_CHAIN_REFRESH_FAILED, {
                "underlying": underlying,
                "error": f"validation_failed: {validation.errors[0]}",
                "errors": list(validation.errors[:5]),
                "analysis_cycle_id": analysis_cycle_id,
            })
            return OptionChainRefreshResult(
                success=False, underlying=underlying,
                validation=validation,
                error=f"validation_failed: {validation.errors[0]}",
                error_code="VALIDATION_FAILED",
            )

        await self._publish(OPTION_CHAIN_VALIDATED, {
            "underlying": underlying,
            "contract_count": validation.contract_count,
            "expiry_count": validation.expiry_count,
            "ce_count": validation.ce_count,
            "pe_count": validation.pe_count,
            "invalid_contract_count": validation.invalid_contract_count,
            "analysis_cycle_id": analysis_cycle_id,
        })

        fi = self._cache.compute_freshness_from_snapshot(snapshot)
        if fi.state == FreshnessState.STALE:
            await self._cache.record_attempt(underlying, False, "stale_chain")
            await self._publish(OPTION_CHAIN_STALE, {
                "underlying": underlying,
                "age_seconds": fi.age_seconds,
                "max_age_seconds": fi.max_age_seconds,
                "stale_after_seconds": fi.stale_after_seconds,
                "chain_version": self._cache._entries.get(underlying, _CacheEntryStub()).chain_version,
                "analysis_cycle_id": analysis_cycle_id,
            })
            self._readiness.set_chain_fresh(underlying, False)
            self._readiness.set_freshness(underlying, FreshnessState.STALE)
            return OptionChainRefreshResult(
                success=False, underlying=underlying,
                validation=validation,
                freshness=FreshnessState.STALE,
                error="stale_chain",
                error_code="CHAIN_STALE",
            )

        await self._cache.put(snapshot)
        await self._cache.record_attempt(underlying, True)
        cv = await self._cache.get_chain_version(underlying)
        iv = self._instrument_service.get_version(underlying)
        self._readiness.set_chain_available(underlying, True)
        self._readiness.set_chain_fresh(underlying, fi.state in (FreshnessState.FRESH, FreshnessState.AGING))
        self._readiness.set_freshness(underlying, fi.state)
        self._readiness.set_chain_version(underlying, cv)

        if fi.state == FreshnessState.AGING:
            await self._publish(OPTION_CHAIN_AGING, {
                "underlying": underlying,
                "chain_version": cv,
                "instrument_version": iv,
                "age_seconds": fi.age_seconds,
                "max_age_seconds": fi.max_age_seconds,
                "stale_after_seconds": fi.stale_after_seconds,
                "contract_count": validation.contract_count,
                "expiry_count": validation.expiry_count,
                "analysis_cycle_id": analysis_cycle_id,
            })

        await self._publish(OPTION_CHAIN_UPDATED, {
            "underlying": underlying,
            "chain_version": cv,
            "instrument_version": iv,
            "contract_count": validation.contract_count,
            "expiry_count": validation.expiry_count,
            "freshness": fi.state.value,
            "data_age_ms": fi.age_seconds * 1000,
            "analysis_cycle_id": analysis_cycle_id,
        })

        return OptionChainRefreshResult(
            success=True,
            underlying=underlying,
            chain_version=cv,
            instrument_version=iv,
            validation=validation,
            freshness=fi.state,
        )

    async def _main_refresh_loop(self) -> None:
        while self._running:
            for underlying in self._config.underlyings:
                if not self._running:
                    break
                if underlying in self._inflight:
                    continue
                backoff = self._backoff.get(underlying, 0.0)
                if backoff > 0:
                    self._backoff[underlying] = min(
                        backoff * 2,
                        self._config.provider_error_max_backoff_seconds,
                    )
                    continue
                try:
                    await self.refresh_underlying(underlying)
                except Exception as e:
                    log_error("Chain refresh loop error", underlying=underlying, error=str(e))
                    self._backoff[underlying] = self._config.provider_error_initial_backoff_seconds

            interval = self._config.chain_poll_interval_seconds
            for _ in range(int(interval * 10)):
                if not self._running:
                    return
                await asyncio.sleep(0.1)

    async def _refresh_instruments_loop(self, underlying: str) -> None:
        while self._running:
            try:
                await asyncio.wait_for(
                    self._instrument_service.refresh(underlying),
                    timeout=self._config.provider_timeout_seconds,
                )
                if self._instrument_service.is_loaded(underlying):
                    self._readiness.set_instruments_loaded(underlying, True)
            except Exception as e:
                log_warn("Instrument refresh loop error", underlying=underlying, error=str(e))
            interval = self._config.instrument_refresh_interval_seconds
            for _ in range(int(interval * 10)):
                if not self._running:
                    return
                await asyncio.sleep(0.1)

    async def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._event_bus is None:
            return
        event = Event(
            type=event_type,
            payload=payload,
            source="OptionChainEngine",
            priority=EventPriority.NORMAL,
        )
        try:
            await self._event_bus.publish(event)
        except Exception as e:
            log_warn("Failed to publish event", event_type=event_type, error=str(e))
