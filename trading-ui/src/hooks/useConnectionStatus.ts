"use client"

import { useRealtimeStore } from "@/store/useRealtimeStore"

/**
 * useConnectionStatus — read-only hook for WebSocket connection state.
 */
export function useConnectionStatus() {
  const connection = useRealtimeStore((s) => s.connection)
  const reconnectHistory = useRealtimeStore((s) => s.reconnectHistory)

  return {
    state: connection.state,
    latency: connection.latency,
    quality: connection.quality,
    reconnectCount: connection.reconnectCount,
    lastConnected: connection.lastConnected,
    lastDisconnected: connection.lastDisconnected,
    lastEvent: connection.lastEvent,
    eventsReceived: connection.eventsReceived,
    reconnectHistory,
  }
}
