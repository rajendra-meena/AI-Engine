import { create } from "zustand"
import type { Prediction, PredictionStats } from "@/types"

/* ─── Types ─── */

export interface AnalyticsFilters {
  dateFrom: string | null
  dateTo: string | null
  timeframe: string | null
  direction: string | null
  riskLevel: string | null
  pattern: string | null
  indicator: string | null
  result: "win" | "loss" | "all" | null
  search: string
}

export type SortField = "time" | "score" | "confidence" | "direction" | "risk" | "decision" | "result" | "pnl"
export type SortDirection = "asc" | "desc"

export interface SortConfig {
  field: SortField
  direction: SortDirection
}

export interface PaginationConfig {
  page: number
  pageSize: number
}

export type ChartView = "daily" | "weekly" | "monthly" | "rolling"
export type ChartType = "bar" | "line" | "area"

export interface AnalyticsView {
  accuracyChart: ChartView
  accuracyChartType: ChartType
  showConfidence: boolean
  showRisk: boolean
  showPatterns: boolean
  showIndicators: boolean
  showTimeframes: boolean
}

/* ─── Store ─── */

interface AnalyticsState {
  /* ── Data ── */
  predictions: Prediction[]
  stats: PredictionStats | null
  totalCount: number
  loading: boolean
  error: string | null

  /* ── Filters ── */
  filters: AnalyticsFilters
  sort: SortConfig
  pagination: PaginationConfig

  /* ── UI ── */
  view: AnalyticsView
  selectedSymbol: string
  selectedDate: string | null
  autoRefresh: boolean

  /* ── Actions: data ── */
  setPredictions: (predictions: Prediction[], totalCount: number) => void
  setStats: (stats: PredictionStats) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void

  /* ── Actions: filters ── */
  setFilters: (filters: Partial<AnalyticsFilters>) => void
  resetFilters: () => void
  setSort: (sort: SortConfig) => void
  setPage: (page: number) => void
  setPageSize: (size: number) => void

  /* ── Actions: UI ── */
  setView: (view: Partial<AnalyticsView>) => void
  setSelectedSymbol: (symbol: string) => void
  setSelectedDate: (date: string | null) => void
  setAutoRefresh: (auto: boolean) => void
  reset: () => void
}

const DEFAULT_FILTERS: AnalyticsFilters = {
  dateFrom: null,
  dateTo: null,
  timeframe: null,
  direction: null,
  riskLevel: null,
  pattern: null,
  indicator: null,
  result: null,
  search: "",
}

const DEFAULT_VIEW: AnalyticsView = {
  accuracyChart: "daily",
  accuracyChartType: "bar",
  showConfidence: true,
  showRisk: true,
  showPatterns: true,
  showIndicators: true,
  showTimeframes: true,
}

export const useAnalyticsStore = create<AnalyticsState>((set) => ({
  predictions: [],
  stats: null,
  totalCount: 0,
  loading: false,
  error: null,

  filters: { ...DEFAULT_FILTERS },
  sort: { field: "time", direction: "desc" },
  pagination: { page: 1, pageSize: 50 },

  view: { ...DEFAULT_VIEW },
  selectedSymbol: "NIFTY 50",
  selectedDate: null,
  autoRefresh: true,

  setPredictions: (predictions, totalCount) => set({ predictions, totalCount, loading: false }),
  setStats: (stats) => set({ stats }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),

  setFilters: (partial) => set((s) => ({ filters: { ...s.filters, ...partial }, pagination: { ...s.pagination, page: 1 } })),
  resetFilters: () => set({ filters: { ...DEFAULT_FILTERS }, pagination: { page: 1, pageSize: 50 } }),
  setSort: (sort) => set({ sort }),
  setPage: (page) => set((s) => ({ pagination: { ...s.pagination, page } })),
  setPageSize: (pageSize) => set((s) => ({ pagination: { ...s.pagination, pageSize, page: 1 } })),

  setView: (partial) => set((s) => ({ view: { ...s.view, ...partial } })),
  setSelectedSymbol: (selectedSymbol) => set({ selectedSymbol }),
  setSelectedDate: (selectedDate) => set({ selectedDate }),
  setAutoRefresh: (autoRefresh) => set({ autoRefresh }),

  reset: () => set({ predictions: [], stats: null, totalCount: 0, loading: false, error: null, filters: { ...DEFAULT_FILTERS }, pagination: { page: 1, pageSize: 50 } }),
}))
