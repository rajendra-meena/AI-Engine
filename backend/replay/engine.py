"""
MarketMind AI — Historical Replay Engine Core

Replays historical candle data sequentially, publishing events for each candle
as if it were arriving live. Supports play, pause, resume, seek, and speed control.

Usage:
    engine = ReplayEngine(market_service, event_bus)
    session = await engine.start(symbol="NIFTY 50", interval="15m", days=30)
    await engine.pause()
    await engine.resume()
    await engine.seek(50)  # jump to 50% progress
    status = engine.get_status()
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

from services.market_data_service import MarketDataService
from core.event_bus import EventBus
from core.event_model import Event
from replay.events import (
    REPLAY_STARTED,
    REPLAY_STOPPED,
    REPLAY_PAUSED,
    REPLAY_RESUMED,
    REPLAY_FINISHED,
    REPLAY_SEEK,
    REPLAY_SPEED_CHANGED,
    NEW_HISTORICAL_CANDLE,
)
from utils.logger import log_info, log_warn, log_error


class ReplayState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    FINISHED = "finished"


REPLAY_SPEEDS = [1, 2, 5, 10, 30, 60, 100]


@dataclass
class ReplaySession:
    """Tracks the state of a single replay session."""

    id: str
    symbol: str
    interval: str
    total_candles: int
    current_index: int = 0
    state: ReplayState = ReplayState.IDLE
    speed: int = 1
    candles: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: str | None = None
    finished_at: str | None = None
    last_event_time: str | None = None

    @property
    def progress_percent(self) -> float:
        if self.total_candles == 0:
            return 0.0
        return round(self.current_index / self.total_candles * 100, 1)

    @property
    def is_finished(self) -> bool:
        return self.current_index >= self.total_candles

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "interval": self.interval,
            "state": self.state.value,
            "speed": f"{self.speed}x",
            "current_index": self.current_index,
            "total_candles": self.total_candles,
            "progress_percent": self.progress_percent,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "last_event_time": self.last_event_time,
        }


class ReplayEngine:
    """
    Orchestrates historical market data replay sessions.

    One session at a time. Start a new session to replay different data.
    """

    def __init__(self, market_service: MarketDataService, event_bus: EventBus):
        self._service = market_service
        self._event_bus = event_bus
        self._session: ReplaySession | None = None
        self._task: asyncio.Task | None = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # not paused initially

    # ── Session lifecycle ──

    async def start(
        self,
        symbol: str = "NIFTY 50",
        interval: str = "15m",
        days: int = 30,
    ) -> ReplaySession:
        """
        Start a new replay session.

        Fetches historical candles via MarketDataService, creates a session,
        and begins replaying them sequentially in a background task.

        If a session is already running, it is stopped first.
        """
        await self.stop()

        log_info(
            "Replay: fetching historical data",
            symbol=symbol,
            interval=interval,
            days=days,
        )

        result = await self._service.get_intraday(symbol, interval, days)
        candles = result.get("candles", [])

        if not candles:
            raise ValueError(f"No historical data available for {symbol} {interval}")

        session_id = uuid.uuid4().hex[:12]
        self._session = ReplaySession(
            id=session_id,
            symbol=symbol,
            interval=interval,
            total_candles=len(candles),
            candles=candles,
            state=ReplayState.RUNNING,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        self._pause_event.set()

        self._task = asyncio.create_task(
            self._run(),
            name=f"replay-{session_id[:6]}",
        )

        await self._publish_event(
            REPLAY_STARTED,
            {
                "session_id": session_id,
                "symbol": symbol,
                "interval": interval,
                "total_candles": len(candles),
            },
        )

        log_info(
            "Replay started", session_id=session_id, symbol=symbol, candles=len(candles)
        )
        return self._session

    async def stop(self) -> dict[str, Any] | None:
        """Stop the current replay session and return its final state."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._session and self._session.state == ReplayState.RUNNING:
            self._session.state = ReplayState.STOPPED
            await self._publish_event(REPLAY_STOPPED, self._session.to_dict())

        result = self._session.to_dict() if self._session else None
        self._session = None
        return result

    async def pause(self) -> bool:
        """Pause the current replay. Returns False if not running."""
        if self._session is None or self._session.state != ReplayState.RUNNING:
            return False
        self._session.state = ReplayState.PAUSED
        self._pause_event.clear()
        await self._publish_event(REPLAY_PAUSED, self._session.to_dict())
        log_info("Replay paused", session_id=self._session.id)
        return True

    async def resume(self) -> bool:
        """Resume a paused replay. Returns False if not paused."""
        if self._session is None or self._session.state != ReplayState.PAUSED:
            return False
        self._session.state = ReplayState.RUNNING
        self._pause_event.set()
        await self._publish_event(REPLAY_RESUMED, self._session.to_dict())
        log_info("Replay resumed", session_id=self._session.id)
        return True

    async def seek(self, target: int | float) -> int:
        """
        Seek to a specific position in the replay.

        Args:
            target: If int (0–N), seek to that candle index.
                    If float (0.0–1.0), seek to that fraction of total.

        Returns:
            The new current_index.
        """
        if self._session is None or not self._session.candles:
            return 0

        if isinstance(target, float):
            target = int(target * self._session.total_candles)

        target = max(0, min(target, self._session.total_candles - 1))
        self._session.current_index = target

        await self._publish_event(
            REPLAY_SEEK,
            {
                "session_id": self._session.id,
                "current_index": target,
                "progress_percent": self._session.progress_percent,
            },
        )

        log_info("Replay seek", session_id=self._session.id, index=target)
        return target

    async def set_speed(self, speed: int) -> int:
        """Set replay speed. Clamped to valid speeds."""
        speed = max(1, min(speed, 100))
        if self._session:
            self._session.speed = speed
            await self._publish_event(
                REPLAY_SPEED_CHANGED,
                {
                    "session_id": self._session.id,
                    "speed": speed,
                },
            )
            log_info("Replay speed changed", session_id=self._session.id, speed=speed)
        return speed

    def get_status(self) -> dict[str, Any] | None:
        """Return current session status."""
        if self._session is None:
            return {
                "state": ReplayState.IDLE.value,
                "session": None,
            }
        return {
            "state": self._session.state.value,
            "session": self._session.to_dict(),
        }

    # ── Background loop ──

    async def _run(self):
        """Background task: emits candles sequentially at replay speed."""
        session = self._session
        if session is None:
            return

        base_interval_seconds = _interval_to_seconds(session.interval)

        try:
            while session.current_index < session.total_candles:
                # Wait if paused
                await self._pause_event.wait()

                candle = session.candles[session.current_index]

                # Publish candle event
                await self._publish_event(
                    NEW_HISTORICAL_CANDLE,
                    {
                        "session_id": session.id,
                        "symbol": session.symbol,
                        "interval": session.interval,
                        "index": session.current_index,
                        "total": session.total_candles,
                        "progress_percent": session.progress_percent,
                        "candle": candle,
                    },
                )

                session.last_event_time = candle.get(
                    "time", datetime.now(timezone.utc).isoformat()
                )
                session.current_index += 1

                # Wait for the real-time interval divided by speed
                wait_time = base_interval_seconds / session.speed
                await asyncio.sleep(wait_time)

            # Finished
            session.state = ReplayState.FINISHED
            session.finished_at = datetime.now(timezone.utc).isoformat()
            await self._publish_event(REPLAY_FINISHED, session.to_dict())
            log_info(
                "Replay finished", session_id=session.id, candles=session.total_candles
            )

        except asyncio.CancelledError:
            raise
        except Exception as e:
            log_error("Replay error", session_id=session.id, error=str(e))
            await self._publish_event(
                "replay_error", {"session_id": session.id, "error": str(e)}
            )

    # ── Internal ──

    async def _publish_event(self, event_type: str, payload: dict):
        event = Event(
            type=event_type,
            source="replay_engine",
            payload=payload,
        )
        await self._event_bus.publish(event)


def _interval_to_seconds(interval: str) -> float:
    """Convert an interval string (e.g. '15m', '1h') to seconds."""
    if interval.endswith("m"):
        return int(interval[:-1]) * 60
    if interval.endswith("h"):
        return int(interval[:-1]) * 3600
    if interval.endswith("d"):
        return int(interval[:-1]) * 86400
    return 60  # default
