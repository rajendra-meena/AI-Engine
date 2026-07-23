import { create } from "zustand"
import type { ConnectionState, ConnectionInfo, ReconnectEvent } from "@/types/websocket"

interface RealtimeState {
  connection: ConnectionInfo
  reconnectHistory: ReconnectEvent[]
  eventHistory: { type: string; time: string }[]
  replayActive: boolean
  replayProgress: number
  streamingSymbols: string[]
  systemHealth: string
  providerStatus: string

  setConnectionState: (state: ConnectionState, reason?: string) => void
  setLatency: (latency: number) => void
  recordReconnect: (event: ReconnectEvent) => void
  recordEvent: (type: string) => void
  setReplayActive: (active: boolean) => void
  setReplayProgress: (progress: number) => void
  addStreamingSymbol: (symbol: string) => void
  removeStreamingSymbol: (symbol: string) => void
  setSystemHealth: (health: string) => void
  setProviderStatus: (status: string) => void
  reset: () => void
}

const initialConnection: ConnectionInfo = {
  state: "disconnected",
  latency: 0,
  reconnectCount: 0,
  lastConnected: null,
  lastDisconnected: null,
  lastEvent: null,
  lastEventTime: null,
  eventsReceived: 0,
  quality: "dead",
  reason: "",
}

export const useRealtimeStore = create<RealtimeState>((set) => ({
  connection: { ...initialConnection },
  reconnectHistory: [],
  eventHistory: [],
  replayActive: false,
  replayProgress: 0,
  streamingSymbols: [],
  systemHealth: "unknown",
  providerStatus: "unknown",

  setConnectionState: (state, reason = "") =>
    set((s) => ({
      connection: {
        ...s.connection,
        state,
        reason,
        lastConnected: state === "connected" ? new Date().toISOString() : s.connection.lastConnected,
        lastDisconnected: state === "disconnected" || state === "reconnecting" ? new Date().toISOString() : s.connection.lastDisconnected,
        quality: state === "connected" ? "good" : state === "reconnecting" ? "fair" : "dead",
      },
    })),

  setLatency: (latency) =>
    set((s) => ({
      connection: {
        ...s.connection,
        latency,
        quality: latency < 50 ? "excellent" : latency < 150 ? "good" : latency < 300 ? "fair" : "poor",
      },
    })),

  recordReconnect: (event) =>
    set((s) => ({
      reconnectHistory: [...s.reconnectHistory.slice(-49), event],
      connection: { ...s.connection, reconnectCount: event.attempt },
    })),

  recordEvent: (type) =>
    set((s) => ({
      eventHistory: [...s.eventHistory.slice(-99), { type, time: new Date().toISOString() }],
      connection: {
        ...s.connection,
        lastEvent: type,
        lastEventTime: new Date().toISOString(),
        eventsReceived: s.connection.eventsReceived + 1,
      },
    })),

  setReplayActive: (active) => set({ replayActive: active }),
  setReplayProgress: (progress) => set({ replayProgress: progress }),
  addStreamingSymbol: (symbol) =>
    set((s) => ({
      streamingSymbols: s.streamingSymbols.includes(symbol) ? s.streamingSymbols : [...s.streamingSymbols, symbol],
    })),
  removeStreamingSymbol: (symbol) =>
    set((s) => ({
      streamingSymbols: s.streamingSymbols.filter((x) => x !== symbol),
    })),
  setSystemHealth: (health) => set({ systemHealth: health }),
  setProviderStatus: (status) => set({ providerStatus: status }),
  reset: () =>
    set({
      connection: { ...initialConnection },
      reconnectHistory: [],
      eventHistory: [],
    }),
}))
