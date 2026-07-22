import apiClient from "@/lib/api"
import type { Candle, DailyRefs } from "@/types"

export interface IntradayResponse {
  symbol: string
  candles: Candle[]
  dailyRefs: DailyRefs | null
  cached: boolean
  cache_size: number
}

export const chartService = {
  async fetchCandles(symbol: string, interval: string, days = 5): Promise<IntradayResponse> {
    const { data } = await apiClient.get("/api/intraday", { params: { symbol, interval, days } })
    return data
  },

  async fetchDailyData(symbol: string, start?: string, end?: string) {
    const { data } = await apiClient.get("/api/data", { params: { symbol, start, end } })
    return data
  },

  async fetchEngineStatus() {
    const { data } = await apiClient.get("/api/candles/status")
    return data
  },

  async fetchIndicators(symbol: string, interval: string) {
    const { data } = await apiClient.get("/api/indicators/latest", { params: { symbol, interval } })
    return data
  },

  async fetchStructure(symbol: string, interval: string) {
    const { data } = await apiClient.get("/api/structure/latest", { params: { symbol, interval } })
    return data
  },

  async fetchPatterns(symbol: string, interval: string) {
    const { data } = await apiClient.get("/api/patterns/latest", { params: { symbol, interval } })
    return data
  },

  async fetchSR(symbol: string) {
    const { data } = await apiClient.get("/api/sr/latest", { params: { symbol } })
    return data
  },
}
