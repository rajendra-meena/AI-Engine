/* eslint-disable @typescript-eslint/no-explicit-any */
import apiClient from "@/lib/api"

export interface DecisionSnapshot {
  symbol: string
  timestamp: string
  decision: string
  score: number
  score_grade: string
  confidence: number
  confidence_grade: string
  risk_level: string
  risk_score: number
  max_risk_percent: number
  trade_plan: {
    direction: string
    valid: boolean
    entry_zone: any
    sl_zone: any
    target_zones: any[]
    risk_reward_context: string
    max_risk_percent: number
  }
  reasoning: string[]
  warnings: string[]
}

export const decisionService = {
  async getLatest(symbol = "NIFTY 50"): Promise<DecisionSnapshot> {
    const { data } = await apiClient.get("/api/ai/latest", { params: { symbol } })
    return data
  },
}
