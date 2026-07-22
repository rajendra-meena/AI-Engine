import apiClient from "@/lib/api"
import type { MarketDataResponse, DailyDataResponse, ProviderStatus } from "@/types"

export const marketService = {
  async getIntraday(symbol: string, interval = "15m", days = 3): Promise<MarketDataResponse> {
    const { data } = await apiClient.get("/api/intraday", { params: { symbol, interval, days } })
    return data
  },

  async getDaily(symbol: string, start?: string, end?: string): Promise<DailyDataResponse> {
    const { data } = await apiClient.get("/api/data", { params: { symbol, start, end } })
    return data
  },

  async getCacheStatus(symbol: string) {
    const { data } = await apiClient.get("/api/cache/status", { params: { symbol } })
    return data
  },

  async getProviderStatus(): Promise<ProviderStatus> {
    const { data } = await apiClient.get("/api/provider/status")
    return data
  },
}
