/**
 * replayService.ts
 *
 * Typed API client for the backend Replay Engine.
 * All endpoints map to backend/replay/api.py routes.
 *
 * NO mock data — every call hits the FastAPI backend.
 */

import apiClient from "@/lib/api"

/* ─── Types ─── */

export interface ReplaySession {
  id: string
  symbol: string
  interval: string
  state: string
  speed: string
  current_index: number
  total_candles: number
  progress_percent: number
  created_at: string
  started_at: string | null
  finished_at: string | null
  last_event_time: string | null
}

export interface ReplayStatus {
  state: string
  session: ReplaySession | null
}

export interface ReplayActionResponse {
  status: string
  session?: ReplaySession
  speed?: number
  current_index?: number
}

/* ─── Service ─── */

export const replayService = {
  async start(symbol = "NIFTY 50", interval = "15m", days = 30): Promise<ReplayActionResponse> {
    const { data } = await apiClient.post("/api/replay/start", null, {
      params: { symbol, interval, days },
    })
    return data
  },

  async pause(): Promise<ReplayActionResponse> {
    const { data } = await apiClient.post("/api/replay/pause")
    return data
  },

  async resume(): Promise<ReplayActionResponse> {
    const { data } = await apiClient.post("/api/replay/resume")
    return data
  },

  async stop(): Promise<ReplayActionResponse> {
    const { data } = await apiClient.post("/api/replay/stop")
    return data
  },

  async reset(): Promise<ReplayActionResponse> {
    const { data } = await apiClient.post("/api/replay/reset")
    return data
  },

  async seek(position: number): Promise<ReplayActionResponse> {
    const { data } = await apiClient.post("/api/replay/seek", null, {
      params: { position },
    })
    return data
  },

  async setSpeed(speed: number): Promise<ReplayActionResponse> {
    const { data } = await apiClient.post("/api/replay/speed", null, {
      params: { speed },
    })
    return data
  },

  async getStatus(): Promise<ReplayStatus> {
    const { data } = await apiClient.get("/api/replay/status")
    return data
  },
}
