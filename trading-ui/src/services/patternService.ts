/* eslint-disable @typescript-eslint/no-explicit-any */
import apiClient from "@/lib/api"

export interface PatternSnapshot {
  symbol: string
  interval: string
  timestamp: string
  candlestick_patterns: any[]
  chart_patterns: any[]
  breakout_patterns: any[]
  strongest_pattern: string
  pattern_direction: string
  confidence: string
  total_count: number
}

export const patternService = {
  async getLatest(symbol = "NIFTY 50", interval = "15m"): Promise<PatternSnapshot> {
    const { data } = await apiClient.get("/api/patterns/latest", { params: { symbol, interval } })
    return data
  },
}
