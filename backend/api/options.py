"""
MarketMind AI — Option Chain Diagnostic API (Phase 57B)

Minimal read-only endpoints for inspecting option chain engine state.
These are diagnostic — not the full Options Workspace API.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core import service_locator
from options.chain_engine import OptionChainEngine
from options.models import OptionEngineReadiness

router = APIRouter(tags=["options"])


def _get_engine() -> OptionChainEngine | None:
    return service_locator.option_chain_engine


@router.get("/api/options/readiness")
async def options_readiness(underlying: str | None = Query(None)):
    """Return the Options Engine readiness state."""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="OptionChainEngine not initialized")
    r = engine.get_readiness(underlying)
    return r.to_dict()


@router.get("/api/options/chain")
async def options_chain(
    underlying: str = Query(..., description="Underlying symbol"),
    expiry: str | None = Query(None, description="Expiry date (YYYY-MM-DD)"),
    require_fresh: bool = Query(True, description="Only return fresh data"),
):
    """Return the option chain snapshot for an underlying."""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="OptionChainEngine not initialized")
    exp: date | None = None
    if expiry:
        try:
            exp = date.fromisoformat(expiry)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid expiry format: {expiry!r}")
    snap = engine.get_snapshot(underlying, expiry=exp, require_fresh=require_fresh)
    if snap is None:
        raise HTTPException(status_code=404, detail="No chain snapshot available (or stale)")
    # Return a simplified dict — never expose mutable model instances
    return {
        "underlying": snap.underlying,
        "spot_price": snap.spot_price,
        "fetched_at": snap.fetched_at.isoformat() if snap.fetched_at else None,
        "source": snap.source.value,
        "expiries": {
            e.isoformat(): {
                "ce_contracts": len(s.ce_quotes),
                "pe_contracts": len(s.pe_quotes),
                "strikes": len(s.strikes),
                "spot_price": s.spot_price,
            }
            for e, s in snap.expiries.items()
        },
    }


@router.post("/api/options/chain/refresh")
async def options_refresh(
    underlying: str = Query(..., description="Underlying symbol"),
    force: bool = Query(False, description="Force refresh even if inflight"),
):
    """Trigger a manual refresh of the option chain."""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="OptionChainEngine not initialized")
    result = await engine.refresh_underlying(underlying, force=force)
    return {
        "success": result.success,
        "underlying": result.underlying,
        "chain_version": result.chain_version,
        "freshness": result.freshness.value if result.freshness else None,
        "error": result.error,
        "error_code": result.error_code,
        "duration_ms": result.duration_ms,
    }


@router.get("/api/options/cache/status")
async def options_cache_status(
    underlying: str = Query(..., description="Underlying symbol"),
):
    """Return the option chain cache status for an underlying."""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="OptionChainEngine not initialized")
    status = await engine.get_cache_status_async(underlying)
    return status
