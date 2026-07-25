"use client"

import { create } from "zustand"

export interface MarketTick {
  symbol: string
  exchange: string
  last_price: number
  volume: number
  timestamp: string
  change_percent: number
  source: string
  received_at: string
}

interface MarketTickState {
  ticks: Record<string, MarketTick>
  lastTickTime: string | null
  tickCount: number
  updateTick: (tick: MarketTick) => void
  getPrice: (symbol: string) => number
  getTick: (symbol: string) => MarketTick | undefined
  isStale: (symbol: string, maxAgeMs?: number) => boolean
  reset: () => void
}

export const useMarketTickStore = create<MarketTickState>((set, get) => ({
  ticks: {},
  lastTickTime: null,
  tickCount: 0,

  updateTick: (tick) =>
    set((state) => ({
      ticks: { ...state.ticks, [tick.symbol]: tick },
      lastTickTime: tick.received_at || tick.timestamp,
      tickCount: state.tickCount + 1,
    })),

  getPrice: (symbol) => {
    const tick = get().ticks[symbol]
    return tick?.last_price ?? 0
  },

  getTick: (symbol) => {
    return get().ticks[symbol]
  },

  isStale: (symbol, maxAgeMs = 5000) => {
    const tick = get().ticks[symbol]
    if (!tick) return true
    const tickTime = new Date(tick.received_at || tick.timestamp).getTime()
    return Date.now() - tickTime > maxAgeMs
  },

  reset: () => set({ ticks: {}, lastTickTime: null, tickCount: 0 }),
}))
