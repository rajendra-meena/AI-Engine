import apiClient from "@/lib/api"

export interface MTFSnapshot {
  symbol: string
  timestamp: string
  timeframes: Record<string, { bias: string; trend: string; confidence: number; mode: string }>
  alignment_level: string
  alignment_score: number
  institutional_bias: string
  market_condition: string
  execution_timeframe: Record<string, string>
  trading_permission: string
  overall_confidence: number
  warnings: string[]
}

export const mtfService = {
  async getLatest(symbol = "NIFTY 50"): Promise<MTFSnapshot> {
    const { data } = await apiClient.get("/api/mtf/latest", { params: { symbol } })
    return data
  },
}
