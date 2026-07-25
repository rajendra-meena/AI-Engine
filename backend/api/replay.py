"""
MarketMind AI — Historical Replay API Routes

Endpoints for controlling the Historical Replay Engine.
"""

from fastapi import APIRouter, Query, HTTPException

from replay.engine import ReplayEngine, REPLAY_SPEEDS

router = APIRouter(tags=["replay"])

# Lazily initialised engine reference (set from main.py)
_replay_engine: ReplayEngine | None = None


def set_replay_engine(engine: ReplayEngine):
    global _replay_engine
    _replay_engine = engine


def _get_engine() -> ReplayEngine:
    assert _replay_engine is not None, "Replay engine not initialized"
    return _replay_engine


@router.post("/api/replay/start")
async def replay_start(
    symbol: str = Query("NIFTY 50", description="Symbol to replay"),
    interval: str = Query("15m", description="Candle interval"),
    days: int = Query(30, description="Days of historical data"),
):
    """Start a new historical replay session."""
    engine = _get_engine()
    try:
        session = await engine.start(symbol=symbol, interval=interval, days=days)
        return {"status": "started", "session": session.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/replay/pause")
async def replay_pause():
    """Pause the current replay session."""
    engine = _get_engine()
    if not await engine.pause():
        raise HTTPException(status_code=400, detail="No active replay to pause")
    return {"status": "paused"}


@router.post("/api/replay/resume")
async def replay_resume():
    """Resume a paused replay session."""
    engine = _get_engine()
    if not await engine.resume():
        raise HTTPException(status_code=400, detail="No paused replay to resume")
    return {"status": "resumed"}


@router.post("/api/replay/stop")
async def replay_stop():
    """Stop the current replay session."""
    engine = _get_engine()
    result = await engine.stop()
    return {"status": "stopped", "session": result}


@router.post("/api/replay/reset")
async def replay_reset():
    """Reset the replay (stop + allows new start)."""
    engine = _get_engine()
    await engine.stop()
    return {"status": "reset"}


@router.post("/api/replay/seek")
async def replay_seek(
    position: float = Query(
        ..., description="Position: int (candle index) or float 0.0–1.0 (percent)"
    ),
):
    """Seek to a position in the current replay."""
    engine = _get_engine()
    new_index = await engine.seek(position)
    return {"status": "seeked", "current_index": new_index}


@router.post("/api/replay/speed")
async def replay_speed(
    speed: int = Query(1, description=f"Replay speed multiplier: {REPLAY_SPEEDS}"),
):
    """Change replay speed."""
    engine = _get_engine()
    clamped = await engine.set_speed(speed)
    return {"status": "speed_changed", "speed": clamped}


@router.get("/api/replay/status")
async def replay_status():
    """Get current replay session status."""
    engine = _get_engine()
    return engine.get_status()
