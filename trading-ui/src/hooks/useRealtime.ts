"use client"
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useEffect, useRef } from "react"
import { getWSManager } from "@/services/websocketManager"
import { useRealtimeStore } from "@/store/useRealtimeStore"
import { useChartStore } from "@/store/useChartStore"
import { useMarketTickStore } from "@/store/useMarketTickStore"
import { useChartData } from "./useChartData"

/**
 * useRealtime — single hook to connect all WebSocket events to Zustand stores.
 * Call once at the app root or dashboard level.
 */
export function useRealtime() {
  const { refetch } = useChartData()
  const initialized = useRef(false)
  const refetchRef = useRef(refetch)

  useEffect(() => {
    refetchRef.current = refetch
  }, [refetch])

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true

    const ws = getWSManager()

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

    const unsubLatency = ws.onEvent("__latency", (latency: number) => {
      useRealtimeStore.getState().setLatency(latency)
    })

    const unsubReconnect = ws.onEvent("__reconnect", (event: any) => {
      useRealtimeStore.getState().recordReconnect(event)
    })

    const unsubCandle = ws.onEvent("candle_closed", () => {
      refetchRef.current()
    })

    const unsubReplayStart = ws.onEvent("replay_started", () => {
      useRealtimeStore.getState().setReplayActive(true)
    })
    const unsubReplayStop = ws.onEvent("replay_stopped", () => {
      useRealtimeStore.getState().setReplayActive(false)
    })
    const unsubReplayFinish = ws.onEvent("replay_finished", () => {
      useRealtimeStore.getState().setReplayActive(false)
    })

    const unsubHealth = ws.onEvent("system_status", (payload: any) => {
      if (payload?.health) useRealtimeStore.getState().setSystemHealth(payload.health)
      if (payload?.provider) useRealtimeStore.getState().setProviderStatus(payload.provider)
    })

    // Live market tick handler — updates chart candle + tick store
    const unsubPrice = ws.onEvent("market_data", (payload: any) => {
      const symbol = payload?.symbol
      const price = payload?.last_price ?? payload?.price ?? payload?.close
      const volume = payload?.volume ?? 0
      if (!symbol || !price) return

      // Store the latest tick
      useMarketTickStore.getState().updateTick({
        symbol,
        exchange: payload?.exchange || "NSE",
        last_price: price,
        volume,
        timestamp: payload?.timestamp || new Date().toISOString(),
        change_percent: payload?.change_percent || 0,
        source: payload?.source || "zerodha",
        received_at: new Date().toISOString(),
      })

      // Update the chart's current (last) candle in real time
      const chartState = useChartStore.getState()
      if (chartState.symbol === symbol && chartState.candles.length > 0) {
        const candles = [...chartState.candles]
        const last = { ...candles[candles.length - 1] }
        last.close = price
        last.high = Math.max(last.high, price)
        last.low = Math.min(last.low, price || last.low)
        last.volume = (last.volume || 0) + volume
        candles[candles.length - 1] = last
        useChartStore.setState({ candles })
      }

      useRealtimeStore.getState().recordEvent("market_data")
    })

    // Subscribe to all lifecycle events for event tracking
    const lifecycleTypes = [
      "order.created", "order.risk_approved", "order.risk_blocked",
      "order.submitted", "order.acknowledged", "order.open",
      "order.partial_fill", "order.filled", "order.rejected", "order.cancelled",
      "trade.created", "trade.updated", "trade.closed",
      "position.opened", "position.updated", "position.closed",
    ]
    const lifecycleUnsubs = lifecycleTypes.map((eventType) =>
      ws.onEvent(eventType, () => {
        useRealtimeStore.getState().recordEvent(eventType)
      })
    )

    // Subscribe to backend market_data channel
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
      unsubPrice()
      lifecycleUnsubs.forEach((u) => u())
    }
  }, [])
}
