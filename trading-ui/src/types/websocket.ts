/* eslint-disable @typescript-eslint/no-explicit-any */
export interface WSMessage {
  id?: string
  type: string
  channel?: string
  symbol?: string
  timestamp?: string
  payload?: Record<string, any>
  version?: string
}

export interface WSSubscription {
  channels: string[]
  symbols: string[]
}

export type ConnectionState = "disconnected" | "connecting" | "connected" | "reconnecting"

export type ConnectionQuality = "excellent" | "good" | "fair" | "poor" | "dead"

export interface ConnectionInfo {
  state: ConnectionState
  latency: number
  reconnectCount: number
  lastConnected: string | null
  lastDisconnected: string | null
  lastEvent: string | null
  lastEventTime: string | null
  eventsReceived: number
  quality: ConnectionQuality
  reason: string
}

export interface ReconnectEvent {
  attempt: number
  delay: number
  reason: string
  timestamp: string
}

export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws"

export const SUBSCRIBABLE_EVENTS = [
  "new_tick",
  "new_historical_candle",
  "candle_started",
  "candle_updated",
  "candle_closed",
  "indicators_updated",
  "structure_updated",
  "pattern_detected",
  "trading_context_updated",
  "sr_updated",
  "mtf_updated",
  "ai_decision_updated",
  "replay_started",
  "replay_paused",
  "replay_resumed",
  "replay_stopped",
  "replay_finished",
  "order.created",
  "order.risk_approved",
  "order.risk_blocked",
  "order.submitted",
  "order.acknowledged",
  "order.open",
  "order.partial_fill",
  "order.filled",
  "order.rejected",
  "order.cancelled",
  "trade.created",
  "trade.updated",
  "trade.closed",
  "position.opened",
  "position.updated",
  "position.closed",
  "pnl.updated",
  "reconciliation.warning",
] as const

export type BackendEvent = (typeof SUBSCRIBABLE_EVENTS)[number]
