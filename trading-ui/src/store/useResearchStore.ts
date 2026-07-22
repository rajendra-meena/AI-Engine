import { create } from "zustand"
import { persist } from "zustand/middleware"

/* ─── Types ─── */

export type ExperimentStatus = "draft" | "running" | "completed" | "failed" | "cancelled"
export type OptimizationMethod = "grid" | "random" | "bayesian" | "genetic"
export type WalkForwardType = "rolling" | "anchored" | "expanding"

export interface BacktestConfig {
  symbol: string
  interval: string
  startDate: string
  endDate: string
  initialCapital: number
  commission: number
  slippage: number
  tax: number
  leverage: number
}

export interface BacktestResult {
  totalTrades: number
  wins: number
  losses: number
  winRate: number
  netProfit: number
  grossProfit: number
  grossLoss: number
  profitFactor: number
  expectancy: number
  sharpe: number
  sortino: number
  calmar: number
  recoveryFactor: number
  ulcerIndex: number
  sqn: number
  avgTrade: number
  avgHoldingTime: number
  maxDrawdown: number
  maxDrawdownPercent: number
  consecWins: number
  consecLosses: number
  exposure: number
  riskAdjustedReturn: number
  equityCurve: { date: string; value: number }[]
  drawdownCurve: { date: string; value: number }[]
  monthlyReturns: { month: string; value: number }[]
  tradeDistribution: { type: string; count: number }[]
}

export interface OptimizationParam {
  key: string
  label: string
  min: number
  max: number
  step: number
}

export interface OptimizationResult {
  id: string
  params: Record<string, number>
  metrics: BacktestResult
}

export interface WalkForwardWindow {
  trainStart: string
  trainEnd: string
  testStart: string
  testEnd: string
}

export interface WalkForwardResult {
  windows: WalkForwardWindow[]
  inSample: BacktestResult
  outOfSample: BacktestResult
  combined: BacktestResult
}

export interface MonteCarloResult {
  simulations: number
  meanReturn: number
  medianReturn: number
  stdReturn: number
  var95: number
  var99: number
  maxReturn: number
  minReturn: number
  percentPositive: number
  distribution: { range: string; count: number }[]
  equityBands: { date: string; upper: number; lower: number; median: number }[]
}

export interface PortfolioAllocation {
  strategyId: string
  name: string
  weight: number
}

export interface PortfolioOptimizationResult {
  allocations: PortfolioAllocation[]
  expectedReturn: number
  expectedRisk: number
  sharpe: number
  correlation: { x: string; y: string; value: number }[]
}

export interface Experiment {
  id: string
  name: string
  author: string
  strategyId: string
  strategyVersion: number
  type: "backtest" | "optimization" | "walkforward" | "montecarlo" | "portfolio"
  config: Record<string, unknown>
  status: ExperimentStatus
  results: BacktestResult | OptimizationResult[] | WalkForwardResult | MonteCarloResult | PortfolioOptimizationResult | null
  duration: number
  seed: number
  tags: string[]
  notes: string
  createdAt: string
  updatedAt: string
}

/* ─── Store ─── */

interface ResearchState {
  experiments: Experiment[]
  currentExperiment: Experiment | null
  activeTab: string
  config: BacktestConfig
  optimizationParams: OptimizationParam[]
  optimMethod: OptimizationMethod
  walkForwardType: WalkForwardType
  trainWindow: number
  testWindow: number
  mcSimulations: number
  selectedSymbols: string[]

  setExperiments: (e: Experiment[]) => void
  addExperiment: (e: Experiment) => void
  updateExperiment: (id: string, update: Partial<Experiment>) => void
  removeExperiment: (id: string) => void
  setCurrentExperiment: (e: Experiment | null) => void
  setActiveTab: (tab: string) => void
  setConfig: (config: Partial<BacktestConfig>) => void
  setOptimizationParams: (p: OptimizationParam[]) => void
  setOptimMethod: (m: OptimizationMethod) => void
  setWalkForwardType: (t: WalkForwardType) => void
  setTrainWindow: (n: number) => void
  setTestWindow: (n: number) => void
  setMcSimulations: (n: number) => void
  setSelectedSymbols: (s: string[]) => void
  reset: () => void
}

const DEFAULT_BACKTEST_CONFIG: BacktestConfig = {
  symbol: "NIFTY 50",
  interval: "15m",
  startDate: new Date(Date.now() - 90 * 86400000).toISOString().split("T")[0],
  endDate: new Date().toISOString().split("T")[0],
  initialCapital: 100000,
  commission: 0.05,
  slippage: 0.02,
  tax: 0.0,
  leverage: 1,
}

export const useResearchStore = create<ResearchState>()(
  persist(
    (set) => ({
      experiments: [],
      currentExperiment: null,
      activeTab: "home",
      config: { ...DEFAULT_BACKTEST_CONFIG },
      optimizationParams: [],
      optimMethod: "grid",
      walkForwardType: "rolling",
      trainWindow: 60,
      testWindow: 20,
      mcSimulations: 1000,
      selectedSymbols: ["NIFTY 50", "BANK NIFTY"],

      setExperiments: (experiments) => set({ experiments }),
      addExperiment: (exp) => set((s) => ({ experiments: [...s.experiments, exp] })),
      updateExperiment: (id, update) => set((s) => ({
        experiments: s.experiments.map((e) => (e.id === id ? { ...e, ...update } : e)),
        currentExperiment: s.currentExperiment?.id === id ? { ...s.currentExperiment, ...update } : s.currentExperiment,
      })),
      removeExperiment: (id) => set((s) => ({
        experiments: s.experiments.filter((e) => e.id !== id),
        currentExperiment: s.currentExperiment?.id === id ? null : s.currentExperiment,
      })),
      setCurrentExperiment: (e) => set({ currentExperiment: e }),
      setActiveTab: (activeTab) => set({ activeTab }),
      setConfig: (partial) => set((s) => ({ config: { ...s.config, ...partial } })),
      setOptimizationParams: (p) => set({ optimizationParams: p }),
      setOptimMethod: (m) => set({ optimMethod: m }),
      setWalkForwardType: (t) => set({ walkForwardType: t }),
      setTrainWindow: (n) => set({ trainWindow: n }),
      setTestWindow: (n) => set({ testWindow: n }),
      setMcSimulations: (n) => set({ mcSimulations: n }),
      setSelectedSymbols: (s) => set({ selectedSymbols: s }),
      reset: () => set({ experiments: [], currentExperiment: null, config: { ...DEFAULT_BACKTEST_CONFIG } }),
    }),
    { name: "marketmind-research", partialize: (state) => ({ experiments: state.experiments, config: state.config }) }
  )
)
