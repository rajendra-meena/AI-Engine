"""
MarketMind AI — Candle Aggregation Engine

Receives ticks from the StreamRouter, builds OHLCV candles for all supported
timeframes, detects closes at timeframe boundaries, and publishes events.

Key design:
    - One ActiveCandle per (symbol, interval) pair
    - round_to_timeframe() determines which candle bucket a tick belongs to
    - When the bucket changes → close old candle, start new one
    - Completed candles stored in CandleBuffer for history queries
    - Events published for STARTED, UPDATED, CLOSED
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from candles.builder import ActiveCandle
from candles.buffer import CandleBuffer
from candles.timeframes import SUPPORTED_TIMEFRAMES, TIMEFRAME_KEYS, round_to_timeframe
from candles.events import CANDLE_STARTED, CANDLE_UPDATED, CANDLE_CLOSED, TIMEFRAME_UPDATED
from core.event_bus import EventBus
from core.event_model import Event
from stream.router import StreamRouter
from utils.logger import log_info, log_warn, log_error


class CandleEngine:
    """
    Aggregates ticks into OHLCV candles for multiple timeframes.

    Usage:
        engine = CandleEngine(stream_router, event_bus)
        await engine.start()   # registers with StreamRouter
        ...
        candle = engine.latest("NIFTY 50", "15m")
        history = engine.history("NIFTY 50", "5m", 20)
        active = engine.active_candle("NIFTY 50", "15m")
        await engine.stop()
    """

    def __init__(self, stream_router: StreamRouter, event_bus: EventBus):
        self._router = stream_router
        self._event_bus = event_bus
        self._buffer = CandleBuffer()
        self._active: dict[tuple[str, str], ActiveCandle] = {}  # (symbol, interval) → candle
        self._stats = {
            "total_ticks_processed": 0,
            "total_candles_closed": 0,
            "total_candles_started": 0,
            "total_errors": 0,
            "start_time": datetime.now(timezone.utc).isoformat(),
        }
        self._running = False

    # ── Lifecycle ──

    async def start(self):
        """Register with the Stream Router as a tick consumer."""
        if self._running:
            return
        self._running = True
        self._router.register_consumer(
            name="candle_engine",
            handler=self._on_tick,
            symbols=None,      # all symbols
            channels=["market_data"],
            mode="all",         # live + replay
        )
        log_info("CandleEngine started", timeframes=TIMEFRAME_KEYS)

    async def stop(self):
        """Unregister from the Stream Router."""
        self._running = False
        self._router.unregister_consumer("candle_engine")
        log_info(
            "CandleEngine stopped",
            candles_closed=self._stats["total_candles_closed"],
            ticks_processed=self._stats["total_ticks_processed"],
        )

    # ── Tick handler (called by StreamRouter) ──

    async def _on_tick(self, payload: dict, channel: str, mode: str):
        """
        Process an incoming tick from the Stream Router.
        Updates all active candles and checks for closes.
        """
        try:
            symbol = payload.get("symbol", "")
            price = float(payload.get("price", 0))
            volume = float(payload.get("volume", 0))
            ts_str = payload.get("timestamp", datetime.now(timezone.utc).isoformat())

            try:
                ts = datetime.fromisoformat(ts_str)
            except (ValueError, TypeError):
                ts = datetime.now(timezone.utc)

            self._stats["total_ticks_processed"] += 1

            for tf in SUPPORTED_TIMEFRAMES:
                await self._process_tick_for_timeframe(symbol, tf.key, tf.minutes, price, volume, ts, ts_str)

        except Exception as e:
            self._stats["total_errors"] += 1
            log_error("CandleEngine tick error", error=str(e))

    async def _process_tick_for_timeframe(
        self,
        symbol: str,
        interval: str,
        minutes: int,
        price: float,
        volume: float,
        ts: datetime,
        ts_str: str,
    ):
        """Process a single tick for one timeframe."""
        bucket = round_to_timeframe(ts, minutes)
        bucket_str = bucket.isoformat(timespec="seconds")
        key = (symbol, interval)

        active = self._active.get(key)

        # If no active candle or bucket changed → close old, start new
        if active is None or active.open_time != bucket_str:
            if active is not None:
                # Close the previous candle
                closed = active.to_candle()
                self._buffer.add(closed)
                self._stats["total_candles_closed"] += 1
                await self._publish_event(CANDLE_CLOSED, {
                    "symbol": symbol,
                    "interval": interval,
                    "candle": closed.to_dict_full(),
                })

            # Start new candle
            self._active[key] = ActiveCandle(
                symbol=symbol,
                interval=interval,
                open_time=bucket_str,
            )
            active = self._active[key]
            self._stats["total_candles_started"] += 1
            await self._publish_event(CANDLE_STARTED, {
                "symbol": symbol,
                "interval": interval,
                "open_time": bucket_str,
            })

        # Update active candle with tick
        active.update(price, volume, ts_str)

        # Publish update event (sampled: every 5th tick to reduce noise)
        if active.tick_count % 5 == 0 or active.tick_count <= 3:
            await self._publish_event(CANDLE_UPDATED, {
                "symbol": symbol,
                "interval": interval,
                "candle": active.to_active_dict(),
            })

    # ── Queries ──

    def latest(self, symbol: str, interval: str) -> dict[str, Any] | None:
        """Most recent completed candle."""
        candle = self._buffer.latest(symbol, interval)
        if candle:
            return candle.to_dict_full()
        return None

    def history(self, symbol: str, interval: str, count: int = 100) -> list[dict[str, Any]]:
        """Last N completed candles."""
        return [c.to_dict_full() for c in self._buffer.history(symbol, interval, count)]

    def active_candle(self, symbol: str, interval: str) -> dict[str, Any] | None:
        """Current forming candle (not yet closed)."""
        key = (symbol, interval)
        ac = self._active.get(key)
        if ac is None:
            return None
        return ac.to_active_dict()

    def timeframes(self) -> list[str]:
        """List of supported timeframe keys."""
        return list(TIMEFRAME_KEYS)

    def buffer_status(self) -> dict[str, Any]:
        """Candle buffer statistics."""
        return self._buffer.get_stats()

    def get_stats(self) -> dict[str, Any]:
        """Full engine statistics."""
        s = dict(self._stats)
        s["running"] = self._running
        s["active_candles"] = len(self._active)
        s["buffer"] = self._buffer.get_stats()
        return s

    # ── Internal ──

    async def _publish_event(self, event_type: str, payload: dict):
        event = Event(type=event_type, source="candle_engine", payload=payload)
        await self._event_bus.publish(event)
