"use client"
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useEffect, useRef } from "react"
import { getWSManager } from "@/services/websocketManager"
import { useRealtimeStore } from "@/store/useRealtimeStore"
import { useChartData } from "./useChartData"

/**
 * useRealtime — single hook to connect all WebSocket events to Zustand stores.
 * Call once at the app root or dashboard level.
 */
export function useRealtime() {
  const { refetch } = useChartData()
  const initialized = useRef(false)
  const refetchRef = useRef(refetch)

  // Keep refetchRef in sync without writing refs during render
  useEffect(() => {
    refetchRef.current = refetch
  }, [refetch])

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true

    const ws = getWSManager()

    // Connection state
    const unsubState = ws.onState((state) => {
      useRealtimeStore.setState((s) => ({
        connection: {
          ...s.connection,
          state,
          lastConnected: state === "connected" ? new Date().toISOString() : s.connection.lastConnected,
          lastDisconnected: state === "disconnected" || state === "reconnecting" ? new Date().toISOString() : s.connection.lastDisconnected,
        },
      }))
    })

    // Latency
    const unsubLatency = ws.onEvent("__latency", (latency: number) => {
      useRealtimeStore.getState().setLatency(latency)
    })

    // Reconnect events
    const unsubReconnect = ws.onEvent("__reconnect", (event: any) => {
      useRealtimeStore.getState().recordReconnect(event)
    })

    // Candle closed → refresh chart data
    const unsubCandle = ws.onEvent("candle_closed", () => {
      refetchRef.current()
    })

    // Replay events
    const unsubReplayStart = ws.onEvent("replay_started", () => {
      useRealtimeStore.getState().setReplayActive(true)
    })
    const unsubReplayStop = ws.onEvent("replay_stopped", () => {
      useRealtimeStore.getState().setReplayActive(false)
    })
    const unsubReplayFinish = ws.onEvent("replay_finished", () => {
      useRealtimeStore.getState().setReplayActive(false)
    })

    // System health
    const unsubHealth = ws.onEvent("system_status", (payload: any) => {
      if (payload?.health) useRealtimeStore.getState().setSystemHealth(payload.health)
      if (payload?.provider) useRealtimeStore.getState().setProviderStatus(payload.provider)
    })

    // Subscribe to backend events
    ws.subscribe("chart", ["market_data"], ["NIFTY 50"], (msg: any) => {
      useRealtimeStore.getState().recordEvent(msg.type || "unknown")
    })

    return () => {
      unsubState()
      unsubLatency()
      unsubReconnect()
      unsubCandle()
      unsubReplayStart()
      unsubReplayStop()
      unsubReplayFinish()
      unsubHealth()
    }
  }, []) // intentionally empty — effect runs once; refetchRef avoids stale closure
}
