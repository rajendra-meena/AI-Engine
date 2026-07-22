import { create } from "zustand"
import { persist } from "zustand/middleware"

/* ─── Types ─── */

export type RuleOperator = "AND" | "OR" | "NOT"
export type ConditionType =
  | "ema_cross" | "ema_above" | "ema_below"
  | "sma_cross" | "sma_above" | "sma_below"
  | "vwap_above" | "vwap_below" | "vwap_bounce"
  | "rsi_above" | "rsi_below" | "rsi_overbought" | "rsi_oversold"
  | "macd_cross" | "macd_above" | "macd_below"
  | "adx_above" | "adx_below"
  | "atr_above" | "atr_below"
  | "supertrend_up" | "supertrend_down"
  | "volume_above" | "volume_spike"
  | "bos_bullish" | "bos_bearish"
  | "choch_bullish" | "choch_bearish"
  | "hh" | "hl" | "lh" | "ll"
  | "liquidity_sweep"
  | "supply_zone" | "demand_zone"
  | "support" | "resistance"
  | "pattern_detected"
  | "bias_bullish" | "bias_bearish"
  | "mtf_aligned"
  | "ai_score_above" | "ai_score_below"
  | "ai_confidence_above"
  | "risk_level"
  | "trend_up" | "trend_down" | "trend_ranging"
  | "volatility_high" | "volatility_low"
  | "momentum_bullish" | "momentum_bearish"
  | "gap_up" | "gap_down"
  | "prev_day_high" | "prev_day_low"
  | "time_between" | "session"
  | "price_above" | "price_below"
  | "price_cross_ema" | "price_cross_vwap"

export type RuleAction = "enter_long" | "enter_short" | "exit_long" | "exit_short" | "close_all"

export type ComparisonOperator = ">" | ">=" | "<" | "<=" | "==" | "!=" | "cross_above" | "cross_below"

export type OptimizationMethod = "grid" | "random" | "bayesian" | "genetic" | "walk_forward"

export type StrategyStatus = "draft" | "active" | "paused" | "archived"

export type DeploymentTarget = "paper" | "live" | "replay" | "scanner" | "portfolio"

export interface StrategyCondition {
  id: string
  type: ConditionType
  operator: ComparisonOperator
  value: number | string | boolean
  params?: Record<string, number>
  field?: string
  label?: string
}

export interface StrategyRule {
  id: string
  label: string
  operator: RuleOperator
  conditions: StrategyCondition[]
  groups?: StrategyRuleGroup[]
}

export interface StrategyRuleGroup {
  id: string
  operator: RuleOperator
  conditions: StrategyCondition[]
}

export interface StrategyEntryRule {
  id: string
  label: string
  operator: RuleOperator
  conditions: StrategyCondition[]
  priority: number
}

export interface StrategyExitRule {
  id: string
  label: string
  operator: RuleOperator
  conditions: StrategyCondition[]
  priority: number
}

export interface StrategyRiskRule {
  id: string
  label: string
  maxRisk: number
  maxPositionSize: number
  stopLoss: number | null
  takeProfit: number | null
  trailingStop: number | null
  maxDailyLoss: number | null
}

export interface StrategyParam {
  id: string
  label: string
  key: string
  type: "int" | "float" | "select" | "boolean"
  default: number | string | boolean
  min?: number
  max?: number
  step?: number
  options?: string[]
}

export interface StrategyVersion {
  id: string
  strategyId: string
  version: number
  name: string
  rules: StrategyEntryRule[]
  exitRules: StrategyExitRule[]
  riskRules: StrategyRiskRule[]
  params: StrategyParam[]
  tags: string[]
  notes: string
  author: string
  createdAt: string
}

export interface StrategyTemplate {
  id: string
  name: string
  description: string
  category: string
  entryRules: StrategyEntryRule[]
  exitRules: StrategyExitRule[]
  riskRules: StrategyRiskRule[]
  params: StrategyParam[]
}

export interface Strategy {
  id: string
  name: string
  description: string
  template: string | null
  version: number
  status: StrategyStatus
  entryRules: StrategyEntryRule[]
  exitRules: StrategyExitRule[]
  riskRules: StrategyRiskRule[]
  params: StrategyParam[]
  tags: string[]
  notes: string
  createdAt: string
  updatedAt: string
  versions: StrategyVersion[]
}

export interface StrategyDeployment {
  id: string
  strategyId: string
  target: DeploymentTarget
  enabled: boolean
  schedule: string | null
  capital: number | null
  createdAt: string
}

export interface OptimizationResult {
  params: Record<string, number>
  metrics: StrategyMetrics
}

export interface StrategyMetrics {
  profit: number
  winRate: number
  expectancy: number
  drawdown: number
  sharpe: number
  sortino: number
  profitFactor: number
  avgRR: number
  avgHoldingTime: number
  maxConsecutiveLoss: number
  recoveryFactor: number
  calmarRatio: number
  totalTrades: number
}

export interface ComparisonResult {
  strategyId: string
  name: string
  metrics: StrategyMetrics
}

/* ─── Store ─── */

interface StrategyState {
  strategies: Strategy[]
  currentStrategy: Strategy | null
  templates: StrategyTemplate[]
  deployments: StrategyDeployment[]
  comparisonResults: ComparisonResult[]
  optimizationResults: OptimizationResult[]
  activeTab: string
  editing: boolean

  setStrategies: (strategies: Strategy[]) => void
  setCurrentStrategy: (s: Strategy | null) => void
  addStrategy: (s: Strategy) => void
  updateStrategy: (id: string, update: Partial<Strategy>) => void
  removeStrategy: (id: string) => void
  setTemplates: (templates: StrategyTemplate[]) => void
  setDeployments: (d: StrategyDeployment[]) => void
  addDeployment: (d: StrategyDeployment) => void
  updateDeployment: (id: string, update: Partial<StrategyDeployment>) => void
  setComparisonResults: (r: ComparisonResult[]) => void
  setOptimizationResults: (r: OptimizationResult[]) => void
  setActiveTab: (tab: string) => void
  setEditing: (editing: boolean) => void
  reset: () => void
}

const DEFAULT_TEMPLATES: StrategyTemplate[] = [
  { id: "ema-trend", name: "EMA Trend Following", description: "Follow EMA crossovers with trend confirmation", category: "trend",
    entryRules: [{ id: "er1", label: "EMA Cross", operator: "AND", conditions: [{ id: "c1", type: "ema_cross", operator: "cross_above", value: 20, params: { period: 20 }, label: "EMA 20/50 Cross" }, { id: "c2", type: "trend_up", operator: "==", value: true, label: "Uptrend" }], priority: 1 }],
    exitRules: [{ id: "ex1", label: "EMA Cross Down", operator: "AND", conditions: [{ id: "c3", type: "ema_cross", operator: "cross_below", value: 20, params: { period: 20 }, label: "EMA 20/50 Cross Down" }], priority: 1 }],
    riskRules: [{ id: "rr1", label: "Default Risk", maxRisk: 2, maxPositionSize: 1, stopLoss: 1, takeProfit: 2, trailingStop: null, maxDailyLoss: 5 }],
    params: [{ id: "p1", label: "Fast EMA", key: "fastEma", type: "int", default: 9, min: 5, max: 50 }, { id: "p2", label: "Slow EMA", key: "slowEma", type: "int", default: 21, min: 10, max: 200 }] },
  { id: "vwap-bounce", name: "VWAP Bounce", description: "Trade bounces off VWAP with confirmation", category: "mean_reversion",
    entryRules: [{ id: "er1", label: "VWAP Bounce", operator: "AND", conditions: [{ id: "c1", type: "vwap_bounce", operator: "==", value: true, label: "VWAP Bounce" }, { id: "c2", type: "rsi_oversold", operator: "<", value: 30, label: "RSI Oversold" }], priority: 1 }],
    exitRules: [{ id: "ex1", label: "Target Hit", operator: "AND", conditions: [{ id: "c3", type: "price_above", operator: ">=", value: 1, params: { atr_multiple: 2 }, label: "2 ATR Target" }], priority: 1 }],
    riskRules: [{ id: "rr1", label: "Default Risk", maxRisk: 1, maxPositionSize: 1, stopLoss: 0.5, takeProfit: 2, trailingStop: null, maxDailyLoss: 3 }],
    params: [{ id: "p1", label: "ATR Multiple", key: "atrMultiple", type: "int", default: 2, min: 1, max: 5 }] },
  { id: "breakout", name: "Breakout Strategy", description: "Trade breakouts with volume confirmation", category: "breakout",
    entryRules: [{ id: "er1", label: "Breakout", operator: "AND", conditions: [{ id: "c1", type: "resistance", operator: "cross_above", value: true, label: "Resistance Break" }, { id: "c2", type: "volume_spike", operator: ">", value: 1.5, label: "Volume 1.5x" }], priority: 1 }],
    exitRules: [{ id: "ex1", label: "Stop Loss", operator: "OR", conditions: [{ id: "c3", type: "support", operator: "cross_below", value: true, label: "Support Break" }, { id: "c4", type: "price_below", operator: "<", value: 2, params: { atr_percent: 2 }, label: "2% Stop" }], priority: 1 }],
    riskRules: [{ id: "rr1", label: "Default Risk", maxRisk: 2, maxPositionSize: 1, stopLoss: 2, takeProfit: 4, trailingStop: null, maxDailyLoss: 5 }],
    params: [{ id: "p1", label: "Volume Threshold", key: "volThreshold", type: "float", default: 1.5, min: 1, max: 5, step: 0.1 }] },
  { id: "ai-hybrid", name: "AI Hybrid", description: "Combine AI signals with technical confirmation", category: "ai",
    entryRules: [{ id: "er1", label: "AI Confirmation", operator: "AND", conditions: [{ id: "c1", type: "ai_score_above", operator: ">=", value: 70, label: "AI Score >= 70" }, { id: "c2", type: "ai_confidence_above", operator: ">=", value: 60, label: "AI Conf >= 60" }, { id: "c3", type: "bias_bullish", operator: "==", value: true, label: "Bullish Bias" }], priority: 1 }],
    exitRules: [{ id: "ex1", label: "AI Exit", operator: "AND", conditions: [{ id: "c4", type: "ai_score_below", operator: "<", value: 40, label: "AI Score < 40" }], priority: 1 }],
    riskRules: [{ id: "rr1", label: "AI Risk", maxRisk: 1, maxPositionSize: 1, stopLoss: null, takeProfit: null, trailingStop: 1, maxDailyLoss: 3 }],
    params: [{ id: "p1", label: "Min Score", key: "minScore", type: "int", default: 70, min: 0, max: 100 }, { id: "p2", label: "Min Confidence", key: "minConfidence", type: "int", default: 60, min: 0, max: 100 }] },
]

export const useStrategyStore = create<StrategyState>()(
  persist(
    (set) => ({
      strategies: [],
      currentStrategy: null,
      templates: DEFAULT_TEMPLATES,
      deployments: [],
      comparisonResults: [],
      optimizationResults: [],
      activeTab: "strategies",
      editing: false,

      setStrategies: (strategies) => set({ strategies }),
      setCurrentStrategy: (currentStrategy) => set({ currentStrategy }),
      addStrategy: (strategy) => set((s) => ({ strategies: [...s.strategies, strategy] })),
      updateStrategy: (id, update) => set((s) => ({
        strategies: s.strategies.map((st) => (st.id === id ? { ...st, ...update } : st)),
        currentStrategy: s.currentStrategy?.id === id ? { ...s.currentStrategy, ...update } : s.currentStrategy,
      })),
      removeStrategy: (id) => set((s) => ({
        strategies: s.strategies.filter((st) => st.id !== id),
        currentStrategy: s.currentStrategy?.id === id ? null : s.currentStrategy,
      })),
      setTemplates: (templates) => set({ templates }),
      setDeployments: (d) => set({ deployments: d }),
      addDeployment: (d) => set((s) => ({ deployments: [...s.deployments, d] })),
      updateDeployment: (id, update) => set((s) => ({
        deployments: s.deployments.map((d) => (d.id === id ? { ...d, ...update } : d)),
      })),
      setComparisonResults: (comparisonResults) => set({ comparisonResults }),
      setOptimizationResults: (optimizationResults) => set({ optimizationResults }),
      setActiveTab: (activeTab) => set({ activeTab }),
      setEditing: (editing) => set({ editing }),
      reset: () => set({
        strategies: [], currentStrategy: null, deployments: [],
        comparisonResults: [], optimizationResults: [],
      }),
    }),
    { name: "marketmind-strategies", partialize: (state) => ({ strategies: state.strategies, deployments: state.deployments }) }
  )
)
