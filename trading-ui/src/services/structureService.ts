import apiClient from "@/lib/api"

export interface StructureSnapshot {
  symbol: string
  interval: string
  timestamp: string
  trend: string
  trend_strength: string
  trend_age: number
  last_hh: number | null
  last_hl: number | null
  last_lh: number | null
  last_ll: number | null
  current_swing_high: number | null
  current_swing_low: number | null
  market_phase: string
  bos_count: number
  choch_count: number
  impulse_active: boolean
  pullback_active: boolean
  consolidation_bars: number
  liquidity_sweeps: number
  valid_structure: boolean
}

export const structureService = {
  async getLatest(symbol = "NIFTY 50", interval = "15m"): Promise<StructureSnapshot> {
    const { data } = await apiClient.get("/api/structure/latest", { params: { symbol, interval } })
    return data
  },
}
