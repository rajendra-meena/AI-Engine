import { create } from "zustand"
import { persist } from "zustand/middleware"

/* ─── Types ─── */

export type ScannerSortField = "score" | "confidence" | "rr" | "change" | "volume" | "price" | "symbol"
export type SortDirection = "asc" | "desc"

export interface ScannerSort {
  field: ScannerSortField
  direction: SortDirection
}

export interface ScannerFilters {
  exchange: string | null
  sector: string | null
  index: string | null
  fando: boolean | null
  watchlist: string | null
  onlyBuy: boolean
  onlySell: boolean
  minScore: number
  minConfidence: number
  maxRisk: string | null
  patternType: string | null
  trend: string | null
  timeframe: string | null
  search: string
}

export interface WatchlistItem {
  symbol: string
  pinned: boolean
  addedAt: string
}

export interface SavedView {
  id: string
  name: string
  filters: ScannerFilters
  sort: ScannerSort
}

export interface AlertConfig {
  id: string
  label: string
  field: "score" | "confidence" | "rr"
  operator: "gt" | "lt"
  value: number
  enabled: boolean
  flash: boolean
  sound: boolean
  desktop: boolean
}

export interface ScannerRow {
  symbol: string
  price: number
  change: number
  volume: number
  trend: string
  score: number
  confidence: number
  risk: string
  rr: number
  institutionalBias: string
  mtfAlignment: string
  supportDistance: number | null
  resistanceDistance: number | null
  pattern: string | null
  decision: string
  lastUpdate: string
  rank: number
}

/* ─── Store ─── */

interface ScannerState {
  rows: ScannerRow[]
  loading: boolean
  error: string | null
  filters: ScannerFilters
  sort: ScannerSort
  watchlist: WatchlistItem[]
  savedViews: SavedView[]
  alerts: AlertConfig[]
  selectedSymbol: string | null
  lastRefresh: number | null
  autoRefresh: boolean
  activeView: string | null
  flashSymbols: string[]

  setRows: (rows: ScannerRow[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setFilters: (filters: Partial<ScannerFilters>) => void
  resetFilters: () => void
  setSort: (sort: ScannerSort) => void
  setSelectedSymbol: (symbol: string | null) => void
  setAutoRefresh: (auto: boolean) => void
  setLastRefresh: (t: number) => void
  setActiveView: (view: string | null) => void
  addFlashSymbol: (symbol: string) => void
  clearFlashSymbols: () => void

  /* Watchlist */
  addToWatchlist: (symbol: string) => void
  removeFromWatchlist: (symbol: string) => void
  togglePin: (symbol: string) => void
  isWatchlisted: (symbol: string) => boolean

  /* Views */
  saveView: (name: string) => void
  deleteView: (id: string) => void
  loadView: (id: string) => void

  /* Alerts */
  toggleAlert: (id: string) => void
  updateAlert: (id: string, config: Partial<AlertConfig>) => void

  reset: () => void
}

const DEFAULT_FILTERS: ScannerFilters = {
  exchange: null, sector: null, index: null, fando: null, watchlist: null,
  onlyBuy: false, onlySell: false, minScore: 0, minConfidence: 0,
  maxRisk: null, patternType: null, trend: null, timeframe: null, search: "",
}

const DEFAULT_ALERTS: AlertConfig[] = [
  { id: "high-score", label: "Score > 90", field: "score", operator: "gt", value: 90, enabled: false, flash: true, sound: false, desktop: false },
  { id: "high-confidence", label: "Confidence > 90", field: "confidence", operator: "gt", value: 90, enabled: false, flash: true, sound: false, desktop: false },
  { id: "high-rr", label: "RR > 2.5", field: "rr", operator: "gt", value: 2.5, enabled: false, flash: true, sound: false, desktop: false },
]

export const useScannerStore = create<ScannerState>()(
  persist(
    (set, get) => ({
      rows: [], loading: false, error: null,
      filters: { ...DEFAULT_FILTERS },
      sort: { field: "score", direction: "desc" },
      watchlist: [],
      savedViews: [],
      alerts: [...DEFAULT_ALERTS],
      selectedSymbol: null,
      lastRefresh: null,
      autoRefresh: true,
      activeView: null,
      flashSymbols: [],

      setRows: (rows) => set({ rows, loading: false }),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
      setFilters: (partial) => set((s) => ({ filters: { ...s.filters, ...partial } })),
      resetFilters: () => set({ filters: { ...DEFAULT_FILTERS } }),
      setSort: (sort) => set({ sort }),
      setSelectedSymbol: (selectedSymbol) => set({ selectedSymbol }),
      setAutoRefresh: (autoRefresh) => set({ autoRefresh }),
      setLastRefresh: (lastRefresh) => set({ lastRefresh }),
      setActiveView: (activeView) => set({ activeView }),
      addFlashSymbol: (symbol) => set((s) => ({ flashSymbols: [...s.flashSymbols, symbol] })),
      clearFlashSymbols: () => set({ flashSymbols: [] }),

      addToWatchlist: (symbol) => set((s) => ({
        watchlist: s.watchlist.some((w) => w.symbol === symbol)
          ? s.watchlist
          : [...s.watchlist, { symbol, pinned: false, addedAt: new Date().toISOString() }],
      })),
      removeFromWatchlist: (symbol) => set((s) => ({
        watchlist: s.watchlist.filter((w) => w.symbol !== symbol),
      })),
      togglePin: (symbol) => set((s) => ({
        watchlist: s.watchlist.map((w) => w.symbol === symbol ? { ...w, pinned: !w.pinned } : w),
      })),
      isWatchlisted: (symbol) => get().watchlist.some((w) => w.symbol === symbol),

      saveView: (name) => {
        const state = get()
        const id = `view_${Date.now()}`
        set({ savedViews: [...state.savedViews, { id, name, filters: { ...state.filters }, sort: { ...state.sort } }] })
      },
      deleteView: (id) => set((s) => ({ savedViews: s.savedViews.filter((v) => v.id !== id) })),
      loadView: (id) => {
        const view = get().savedViews.find((v) => v.id === id)
        if (view) set({ filters: { ...view.filters }, sort: { ...view.sort }, activeView: id })
      },

      toggleAlert: (id) => set((s) => ({
        alerts: s.alerts.map((a) => a.id === id ? { ...a, enabled: !a.enabled } : a),
      })),
      updateAlert: (id, config) => set((s) => ({
        alerts: s.alerts.map((a) => a.id === id ? { ...a, ...config } : a),
      })),

      reset: () => set({ rows: [], loading: false, error: null, filters: { ...DEFAULT_FILTERS }, selectedSymbol: null }),
    }),
    { name: "marketmind-scanner", partialize: (state) => ({ watchlist: state.watchlist, savedViews: state.savedViews, alerts: state.alerts, autoRefresh: state.autoRefresh }) }
  )
)
