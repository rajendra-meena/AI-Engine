"use client"

// WebSocket event payloads are typed loosely — backend events are schema-less
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useCallback, useEffect, useRef } from "react"
import { replayService } from "@/services/replayService"
import { useReplayStore, type ReplayJournalEntry } from "@/store/useReplayStore"
import { getWSManager } from "@/services/websocketManager"

const DEFAULT_SYMBOL = "NIFTY 50"
const DEFAULT_INTERVAL = "15m"
const DEFAULT_DAYS = 30

/**
 * useReplay — connects all Replay Studio UI to the backend Replay Engine.
 *
 * Handles:
 * - Play/Pause/Resume/Stop/Seek/Speed via REST API
 * - Real-time replay events via WebSocket
 * - Candle accumulation in store
 * - Session lifecycle tracking
 * - Journal entries for AI decisions
 */
export function useReplay() {
  const store = useReplayStore()
  const wsCleanup = useRef<(() => void)[]>([])

  // ── Subscribe to WebSocket replay events ──
  useEffect(() => {
    const ws = getWSManager()

    const unsubStart = ws.onEvent("replay_started", (payload: any) => {
      store.setActive(true)
      store.setState("running")
      store.setIsPlaying(true)
      store.setIsPaused(false)
      store.setStartTime(Date.now())
      if (payload?.total_candles) store.setTotalCandles(Number(payload.total_candles))
    })

    const unsubStop = ws.onEvent("replay_stopped", () => {
      store.setActive(false)
      store.setState("stopped")
      store.setIsPlaying(false)
      store.setIsPaused(false)
    })

    const unsubPause = ws.onEvent("replay_paused", () => {
      store.setState("paused")
      store.setIsPlaying(false)
      store.setIsPaused(true)
    })

    const unsubResume = ws.onEvent("replay_resumed", () => {
      store.setState("running")
      store.setIsPlaying(true)
      store.setIsPaused(false)
    })

    const unsubFinish = ws.onEvent("replay_finished", () => {
      store.setState("finished")
      store.setIsPlaying(false)
      store.setIsPaused(false)
    })

    const unsubSeek = ws.onEvent("replay_seek", (payload: any) => {
      if (payload.current_index != null) {
        store.setCurrentIndex(Number(payload.current_index))
      }
    })

    const unsubSpeed = ws.onEvent("replay_speed_changed", (payload: any) => {
      if (payload.speed) store.setSpeed(Number(payload.speed))
    })

    const unsubCandle = ws.onEvent("new_historical_candle", (payload: any) => {
      const candle = payload?.candle
      if (candle) {
        store.addCandle(candle)
        store.setCurrentIndex(payload.index ?? store.currentIndex + 1)
      }
    })

    wsCleanup.current = [
      unsubStart, unsubStop, unsubPause, unsubResume,
      unsubFinish, unsubSeek, unsubSpeed, unsubCandle,
    ]

    // Poll status on mount to recover if WS misses state
    replayService.getStatus().then((status) => {
      if (status.session && status.state !== "idle") {
        store.setActive(true)
        store.setState(status.state)
        store.setSession(status.session)
        store.setCurrentIndex(status.session.current_index)
        store.setTotalCandles(status.session.total_candles)
        store.setIsPlaying(status.state === "running")
        store.setIsPaused(status.state === "paused")
        const speedNum = parseInt(String(status.session.speed))
        if (!isNaN(speedNum)) store.setSpeed(speedNum)
      }
    }).catch(() => {
      // backend may not be available yet
    })

    return () => {
      wsCleanup.current.forEach((fn) => fn())
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Actions ──

  const start = useCallback(async (symbol = DEFAULT_SYMBOL, interval = DEFAULT_INTERVAL, days = DEFAULT_DAYS) => {
    store.reset()
    try {
      const result = await replayService.start(symbol, interval, days)
      if (result.session) {
        store.setSession(result.session)
        store.setTotalCandles(result.session.total_candles)
      }
    } catch (e) {
      console.error("Replay start failed", e)
    }
  }, [store])

  const pause = useCallback(async () => {
    await replayService.pause()
  }, [])

  const resume = useCallback(async () => {
    await replayService.resume()
  }, [])

  const stop = useCallback(async () => {
    await replayService.stop()
    store.reset()
  }, [store])

  const seek = useCallback(async (position: number) => {
    await replayService.seek(position)
  }, [])

  const setSpeed = useCallback(async (speed: number) => {
    await replayService.setSpeed(speed)
  }, [])

  const togglePlay = useCallback(async () => {
    const s = useReplayStore.getState()
    if (s.state === "running") await pause()
    else if (s.state === "paused") await resume()
    else await start()
  }, [start, pause, resume])

  const stepBack = useCallback(async () => {
    const s = useReplayStore.getState()
    const next = Math.max(0, s.currentIndex - 1)
    await seek(next)
  }, [seek])

  const stepForward = useCallback(async () => {
    const s = useReplayStore.getState()
    const next = Math.min(s.totalCandles, s.currentIndex + 1)
    await seek(next)
  }, [seek])

  const addJournalEntry = useCallback((entry: ReplayJournalEntry) => {
    store.addJournalEntry(entry)
  }, [store])

  return {
    /* state */
    active: store.active,
    session: store.session,
    state: store.state,
    isPlaying: store.isPlaying,
    isPaused: store.isPaused,
    speed: store.speed,
    currentIndex: store.currentIndex,
    totalCandles: store.totalCandles,
    replayCandles: store.replayCandles,
    journal: store.journal,
    processedDecisions: store.processedDecisions,
    processedTrades: store.processedTrades,
    startTime: store.startTime,

    /* UI toggles */
    view: store.view,
    showJournal: store.showJournal,
    showStatistics: store.showStatistics,
    showMiniMap: store.showMiniMap,
    showCalendar: store.showCalendar,

    /* actions */
    start,
    pause,
    resume,
    stop,
    seek,
    setSpeed,
    togglePlay,
    stepBack,
    stepForward,
    addJournalEntry,
    toggleJournal: store.toggleJournal,
    toggleStatistics: store.toggleStatistics,
    toggleMiniMap: store.toggleMiniMap,
    toggleCalendar: store.toggleCalendar,
  }
}
