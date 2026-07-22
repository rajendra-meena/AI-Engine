/* eslint-disable @typescript-eslint/no-explicit-any */
import apiClient from "@/lib/api"

export interface SRSnapshot {
  symbol: string
  timestamp: string
  nearest_support: number | null
  nearest_resistance: number | null
  major_supports: any[]
  major_resistances: any[]
  supply_zones: any[]
  demand_zones: any[]
  dynamic_levels: any[]
  psychological_levels: any[]
  breakout_state: string
  zone_strength: string
  confidence: number
  warnings: string[]
}

export const srService = {
  async getLatest(symbol = "NIFTY 50"): Promise<SRSnapshot> {
    const { data } = await apiClient.get("/api/sr/latest", { params: { symbol } })
    return data
  },
}
