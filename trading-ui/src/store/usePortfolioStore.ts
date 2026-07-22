import { create } from "zustand"
import { persist } from "zustand/middleware"

/* ─── Types ─── */

export type OrderType = "market" | "limit" | "stop" | "stop_limit" | "bracket"
export type OrderSide = "buy" | "sell"
export type OrderStatus = "open" | "filled" | "partial" | "cancelled" | "rejected"
export type PositionStatus = "open" | "closed"

export interface Order {
  id: string
  symbol: string
  side: OrderSide
  type: OrderType
  quantity: number
  price: number | null
  stopPrice: number | null
  status: OrderStatus
  filledQty: number
  avgFillPrice: number | null
  createdAt: string
  filledAt: string | null
  stopLoss: number | null
  takeProfit: number | null
}

export interface Position {
  id: string
  symbol: string
  direction: "LONG" | "SHORT"
  entry: number
  currentPrice: number
  quantity: number
  pnl: number
  pnlPercent: number
  rr: number
  aiScore: number | null
  aiConfidence: number | null
  risk: string | null
  status: PositionStatus
  trailingStop: number | null
  targets: number[]
  partialExit: number | null
  openedAt: string
  closedAt: string | null
  reason: string | null
}

export interface ClosedTrade extends Position {
  exit: number
  duration: number
  exitReason: string
  aiDecision: string | null
  pattern: string | null
  trend: string | null
  notes: string | null
}

export interface PortfolioSummary {
  totalValue: number
  todayPnL: number
  totalPnL: number
  openPositions: number
  closedPositions: number
  winRate: number
  avgRR: number
  availableMargin: number
  usedMargin: number
  exposure: number
  capitalAllocation: number
}

export interface JournalEntry {
  id: string
  tradeId: string
  symbol: string
  entry: number
  exit: number | null
  direction: "LONG" | "SHORT"
  reason: string | null
  aiScore: number | null
  aiConfidence: number | null
  structure: string | null
  pattern: string | null
  result: string | null
  notes: string
  createdAt: string
}

export interface WatchlistGroup {
  id: string
  name: string
  symbols: string[]
  color: string | null
}

export interface EquityPoint {
  date: string
  value: number
}

export interface PortfolioAnalytics {
  equityCurve: EquityPoint[]
  drawdown: number
  profitFactor: number
  expectancy: number
  avgHoldingTime: number
  largestWin: number
  largestLoss: number
}

/* ─── Store ─── */

interface PortfolioState {
  /* ── Data ── */
  summary: PortfolioSummary
  positions: Position[]
  closedTrades: ClosedTrade[]
  journal: JournalEntry[]
  watchlists: WatchlistGroup[]
  orders: Order[]
  analytics: PortfolioAnalytics
  selectedWatchlist: string | null

  /* ── Paper trading config ── */
  paperCapital: number
  maxRiskPercent: number
  defaultLotSize: number

  /* ── UI ── */
  activeTab: "overview" | "positions" | "trades" | "journal" | "watchlist" | "analytics"

  /* ── Actions: data ── */
  setSummary: (summary: Partial<PortfolioSummary>) => void
  setPositions: (positions: Position[]) => void
  addPosition: (position: Position) => void
  updatePosition: (id: string, update: Partial<Position>) => void
  closePosition: (id: string, closedTrade: ClosedTrade) => void
  setClosedTrades: (trades: ClosedTrade[]) => void
  addClosedTrade: (trade: ClosedTrade) => void
  setOrders: (orders: Order[]) => void
  addOrder: (order: Order) => void
  updateOrder: (id: string, update: Partial<Order>) => void
  setAnalytics: (analytics: PortfolioAnalytics) => void

  /* ── Journal ── */
  addJournalEntry: (entry: JournalEntry) => void
  updateJournalEntry: (id: string, update: Partial<JournalEntry>) => void

  /* ── Watchlist ── */
  addWatchlist: (group: WatchlistGroup) => void
  removeWatchlist: (id: string) => void
  addToWatchlist: (groupId: string, symbol: string) => void
  removeFromWatchlist: (groupId: string, symbol: string) => void
  setSelectedWatchlist: (id: string | null) => void

  /* ── Config ── */
  setPaperCapital: (capital: number) => void
  setMaxRiskPercent: (percent: number) => void
  setDefaultLotSize: (size: number) => void

  /* ── UI ── */
  setActiveTab: (tab: string) => void
  reset: () => void
}

const DEFAULT_SUMMARY: PortfolioSummary = {
  totalValue: 100000,
  todayPnL: 0,
  totalPnL: 0,
  openPositions: 0,
  closedPositions: 0,
  winRate: 0,
  avgRR: 0,
  availableMargin: 100000,
  usedMargin: 0,
  exposure: 0,
  capitalAllocation: 0,
}

export const usePortfolioStore = create<PortfolioState>()(
  persist(
    (set) => ({
      summary: { ...DEFAULT_SUMMARY },
      positions: [],
      closedTrades: [],
      journal: [],
      watchlists: [{ id: "default", name: "Favorites", symbols: ["NIFTY 50", "BANK NIFTY"], color: null }],
      orders: [],
      analytics: { equityCurve: [], drawdown: 0, profitFactor: 0, expectancy: 0, avgHoldingTime: 0, largestWin: 0, largestLoss: 0 },
      selectedWatchlist: null,
      paperCapital: 100000,
      maxRiskPercent: 2,
      defaultLotSize: 1,
      activeTab: "overview",

      setSummary: (partial) => set((s) => ({ summary: { ...s.summary, ...partial } })),
      setPositions: (positions) => set({ positions }),
      addPosition: (position) => set((s) => ({ positions: [...s.positions, position] })),
      updatePosition: (id, update) =>
        set((s) => ({
          positions: s.positions.map((p) => (p.id === id ? { ...p, ...update } : p)),
        })),
      closePosition: (id, closedTrade) =>
        set((s) => ({
          positions: s.positions.filter((p) => p.id !== id),
          closedTrades: [...s.closedTrades, closedTrade],
        })),
      setClosedTrades: (trades) => set({ closedTrades: trades }),
      addClosedTrade: (trade) => set((s) => ({ closedTrades: [...s.closedTrades, trade] })),
      setOrders: (orders) => set({ orders }),
      addOrder: (order) => set((s) => ({ orders: [...s.orders, order] })),
      updateOrder: (id, update) =>
        set((s) => ({
          orders: s.orders.map((o) => (o.id === id ? { ...o, ...update } : o)),
        })),
      setAnalytics: (analytics) => set({ analytics }),

      addJournalEntry: (entry) => set((s) => ({ journal: [...s.journal, entry] })),
      updateJournalEntry: (id, update) =>
        set((s) => ({
          journal: s.journal.map((j) => (j.id === id ? { ...j, ...update } : j)),
        })),

      addWatchlist: (group) => set((s) => ({ watchlists: [...s.watchlists, group] })),
      removeWatchlist: (id) => set((s) => ({ watchlists: s.watchlists.filter((w) => w.id !== id) })),
      addToWatchlist: (groupId, symbol) =>
        set((s) => ({
          watchlists: s.watchlists.map((w) =>
            w.id === groupId ? { ...w, symbols: [...w.symbols, symbol] } : w
          ),
        })),
      removeFromWatchlist: (groupId, symbol) =>
        set((s) => ({
          watchlists: s.watchlists.map((w) =>
            w.id === groupId ? { ...w, symbols: w.symbols.filter((s) => s !== symbol) } : w
          ),
        })),
      setSelectedWatchlist: (selectedWatchlist) => set({ selectedWatchlist }),

      setPaperCapital: (paperCapital) => set({ paperCapital }),
      setMaxRiskPercent: (maxRiskPercent) => set({ maxRiskPercent }),
      setDefaultLotSize: (defaultLotSize) => set({ defaultLotSize }),

      setActiveTab: (tab) => set({ activeTab: tab as PortfolioState["activeTab"] }),
      reset: () => set({
        summary: { ...DEFAULT_SUMMARY },
        positions: [],
        closedTrades: [],
        orders: [],
        journal: [],
      }),
    }),
    { name: "marketmind-portfolio", partialize: (state) => ({ watchlists: state.watchlists, paperCapital: state.paperCapital, maxRiskPercent: state.maxRiskPercent, defaultLotSize: state.defaultLotSize, closedTrades: state.closedTrades, journal: state.journal }) }
  )
)
