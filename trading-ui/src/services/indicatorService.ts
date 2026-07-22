import apiClient from "@/lib/api"

export interface IndicatorSnapshot {
  symbol: string
  interval: string
  timestamp: string
  ema_9: number | null
  ema_20: number | null
  ema_50: number | null
  ema_200: number | null
  sma_20: number | null
  sma_50: number | null
  rsi_14: number | null
  atr_14: number | null
  vwap: number | null
  macd: number | null
  macd_signal: number | null
  macd_histogram: number | null
  adx_14: number | null
  supertrend_trend: string | null
  candle_close: number | null
  all_ready: boolean
}

export const indicatorService = {
  async getLatest(symbol = "NIFTY 50", interval = "15m"): Promise<IndicatorSnapshot> {
    const { data } = await apiClient.get("/api/indicators/latest", { params: { symbol, interval } })
    return data
  },
}
