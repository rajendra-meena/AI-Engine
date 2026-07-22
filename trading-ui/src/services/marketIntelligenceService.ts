/**
 * marketIntelligenceService.ts
 *
 * Market Intelligence API client — economic calendar, news, institutional flow,
 * options intelligence, sector data.
 */

import apiClient from "@/lib/api"

/* ─── Types ─── */

export interface EconomicEvent {
  id: string
  title: string
  country: string
  date: string
  impact: "high" | "medium" | "low"
  previous: string | null
  forecast: string | null
  actual: string | null
  currency: string
  affectedAssets: string[]
  riskRating: "low" | "medium" | "high"
}

export interface NewsItem {
  id: string
  title: string
  summary: string
  source: string
  category: string
  sentiment: "positive" | "negative" | "neutral"
  sentimentScore: number
  confidence: number
  importance: "high" | "medium" | "low"
  expectedImpact: string
  marketBias: "bullish" | "bearish" | "neutral"
  url: string
  publishedAt: string
}

export interface InstitutionalFlow {
  date: string
  fiiBuy: number
  fiiSell: number
  fiiNet: number
  diiBuy: number
  diiSell: number
  diiNet: number
  deliveryPercent: number
  blockDeals: { script: string; quantity: number; price: number }[]
  bulkDeals: { script: string; quantity: number; price: number }[]
}

export interface OptionsData {
  symbol: string
  expiry: string
  pcr: number
  maxPain: number
  iv: number
  ivRank: number
  ivPercentile: number
  oiBuildUp: { strike: number; type: "ce" | "pe"; oi: number; change: number }[]
  gammaExposure: number
  dealerPositioning: string
}

export interface SectorData {
  name: string
  change: number
  relativeStrength: number
  momentum: number
  trend: "uptrend" | "downtrend" | "ranging"
  leadership: number
  capitalRotation: number
}

export interface MarketRegime {
  regime: string
  volatility: string
  breadth: number
  correlation: number
  riskOn: boolean
}

export const marketIntelligenceService = {
  /* ── Economic Calendar ── */

  async getEconomicCalendar(country?: string, from?: string, to?: string): Promise<EconomicEvent[]> {
    try {
      const { data } = await apiClient.get("/api/intelligence/economic-calendar", { params: { country, from, to } })
      return data as EconomicEvent[]
    } catch { return [] }
  },

  /* ── News Intelligence ── */

  async getNews(symbol?: string, category?: string, limit = 20): Promise<NewsItem[]> {
    try {
      const { data } = await apiClient.get("/api/intelligence/news", { params: { symbol, category, limit } })
      return data as NewsItem[]
    } catch { return [] }
  },

  /* ── Institutional Flow ── */

  async getInstitutionalFlow(symbol?: string): Promise<InstitutionalFlow | null> {
    try {
      const { data } = await apiClient.get("/api/intelligence/institutional-flow", { params: { symbol } })
      return data as InstitutionalFlow
    } catch { return null }
  },

  /* ── Options Intelligence ── */

  async getOptionsData(symbol: string): Promise<OptionsData | null> {
    try {
      const { data } = await apiClient.get("/api/intelligence/options", { params: { symbol } })
      return data as OptionsData
    } catch { return null }
  },

  /* ── Sector Intelligence ── */

  async getSectorData(): Promise<SectorData[]> {
    try {
      const { data } = await apiClient.get("/api/intelligence/sectors")
      return data as SectorData[]
    } catch { return [] }
  },

  /* ── Market Regime ── */

  async getMarketRegime(): Promise<MarketRegime | null> {
    try {
      const { data } = await apiClient.get("/api/intelligence/regime")
      return data as MarketRegime
    } catch { return null }
  },
}
