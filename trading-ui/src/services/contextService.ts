import apiClient from "@/lib/api"

export interface ContextSnapshot {
  symbol: string
  interval: string
  timestamp: string
  trend: string
  trend_strength: string
  momentum: string
  momentum_strength: string
  volatility: string
  volatility_state: string
  liquidity_state: string
  market_phase: string
  session: string
  pattern_bias: string
  structure_bias: string
  indicator_bias: string
  overall_bias: string
  overall_strength: string
  confidence: number
  risk_level: string
  recommended_mode: string
  warnings: string[]
}

export const contextService = {
  async getLatest(symbol = "NIFTY 50", interval = "15m"): Promise<ContextSnapshot> {
    const { data } = await apiClient.get("/api/context/latest", { params: { symbol, interval } })
    return data
  },
}
