/**
 * strategyService.ts
 *
 * Strategy Builder API client and rule engine utilities.
 */

import apiClient from "@/lib/api"
import type {
  Strategy, StrategyTemplate, StrategyVersion, StrategyMetrics,
  OptimizationResult, ComparisonResult, StrategyDeployment, StrategyCondition,
} from "@/store/useStrategyStore"

export const strategyService = {
  /* ── CRUD ── */

  async list(): Promise<Strategy[]> {
    const { data } = await apiClient.get("/api/strategies")
    return data
  },

  async get(id: string): Promise<Strategy> {
    const { data } = await apiClient.get(`/api/strategies/${id}`)
    return data
  },

  async create(strategy: Partial<Strategy>): Promise<Strategy> {
    const { data } = await apiClient.post("/api/strategies", strategy)
    return data
  },

  async update(id: string, strategy: Partial<Strategy>): Promise<Strategy> {
    const { data } = await apiClient.put(`/api/strategies/${id}`, strategy)
    return data
  },

  async remove(id: string): Promise<void> {
    await apiClient.delete(`/api/strategies/${id}`)
  },

  /* ── Templates ── */

  async getTemplates(): Promise<StrategyTemplate[]> {
    const { data } = await apiClient.get("/api/strategy/templates")
    return data
  },

  /* ── Versions ── */

  async getVersions(strategyId: string): Promise<StrategyVersion[]> {
    const { data } = await apiClient.get(`/api/strategies/${strategyId}/versions`)
    return data
  },

  async createVersion(strategyId: string, version: Partial<StrategyVersion>): Promise<StrategyVersion> {
    const { data } = await apiClient.post(`/api/strategies/${strategyId}/versions`, version)
    return data
  },

  /* ── Optimization ── */

  async optimize(strategyId: string, method: string, params: Record<string, { min: number; max: number; step: number }>): Promise<OptimizationResult[]> {
    const { data } = await apiClient.post("/api/strategy/optimize", { strategyId, method, params })
    return data
  },

  /* ── Comparison ── */

  async compare(strategyIds: string[]): Promise<ComparisonResult[]> {
    const { data } = await apiClient.post("/api/strategy/compare", { strategyIds })
    return data
  },

  /* ── Validate ── */

  async validate(strategy: Partial<Strategy>): Promise<{ valid: boolean; errors: string[] }> {
    const { data } = await apiClient.post("/api/strategy/validate", strategy)
    return data
  },

  /* ── Deploy ── */

  async deploy(strategyId: string, target: string, config?: Record<string, unknown>): Promise<StrategyDeployment> {
    const { data } = await apiClient.post("/api/strategy/deploy", { strategyId, target, config })
    return data
  },

  async getDeployments(strategyId: string): Promise<StrategyDeployment[]> {
    const { data } = await apiClient.get(`/api/strategies/${strategyId}/deployments`)
    return data
  },

  /* ── AI Explain ── */

  async explain(strategy: Partial<Strategy>): Promise<{ analysis: string; suggestions: string[]; risks: string[] }> {
    const { data } = await apiClient.post("/api/strategy/explain", strategy)
    return data
  },

  /* ── Client-side condition evaluation ── */

  evaluateCondition(condition: StrategyCondition, marketData: Record<string, number>): boolean {
    const val = marketData[condition.field || condition.type]
    if (val == null) return false

    switch (condition.operator) {
      case ">": return val > Number(condition.value)
      case ">=": return val >= Number(condition.value)
      case "<": return val < Number(condition.value)
      case "<=": return val <= Number(condition.value)
      case "==": return val === condition.value
      case "!=": return val !== condition.value
      default: return false
    }
  },

  /**
   * Compute basic strategy metrics from backtest results.
   */
  computeMetrics(trades: Array<{ pnl: number; duration: number; rr?: number }>): StrategyMetrics {
    const total = trades.length
    if (total === 0) return { profit: 0, winRate: 0, expectancy: 0, drawdown: 0, sharpe: 0, sortino: 0, profitFactor: 0, avgRR: 0, avgHoldingTime: 0, maxConsecutiveLoss: 0, recoveryFactor: 0, calmarRatio: 0, totalTrades: 0 }

    const wins = trades.filter((t) => t.pnl > 0)
    const losses = trades.filter((t) => t.pnl <= 0)
    const totalProfit = trades.reduce((a, t) => a + t.pnl, 0)
    const totalLoss = losses.reduce((a, t) => a + t.pnl, 0)

    const winRate = (wins.length / total) * 100
    const avgWin = wins.length > 0 ? wins.reduce((a, t) => a + t.pnl, 0) / wins.length : 0
    const avgLoss = losses.length > 0 ? Math.abs(losses.reduce((a, t) => a + t.pnl, 0) / losses.length) : 1
    const profitFactor = totalLoss !== 0 ? Math.abs(totalProfit / totalLoss) : totalProfit > 0 ? Infinity : 0

    const avgRR = trades.reduce((a, t) => a + (t.rr || Math.abs(t.pnl / (avgLoss || 1))), 0) / total
    const avgHoldingTime = trades.reduce((a, t) => a + (t.duration || 0), 0) / total

    const returns = trades.map((t) => t.pnl)
    const avgReturn = totalProfit / total
    const stdDev = Math.sqrt(returns.reduce((a, r) => a + (r - avgReturn) ** 2, 0) / total)
    const negReturns = returns.filter((r) => r < 0)
    const downDev = negReturns.length > 0 ? Math.sqrt(negReturns.reduce((a, r) => a + r ** 2, 0) / negReturns.length) : 1

    let maxDrawdown = 0
    let peak = 0
    let cumSum = 0
    for (const t of trades) {
      cumSum += t.pnl
      if (cumSum > peak) peak = cumSum
      const dd = (peak - cumSum) / Math.max(1, peak)
      if (dd > maxDrawdown) maxDrawdown = dd
    }

    // Consecutive losses
    let maxCons = 0
    let curCons = 0
    for (const t of trades) {
      if (t.pnl <= 0) { curCons++; if (curCons > maxCons) maxCons = curCons }
      else curCons = 0
    }

    return {
      profit: totalProfit,
      winRate,
      expectancy: avgWin * (winRate / 100) - avgLoss * (1 - winRate / 100),
      drawdown: maxDrawdown * 100,
      sharpe: stdDev > 0 ? (avgReturn / stdDev) * Math.sqrt(252) : 0,
      sortino: downDev > 0 ? (avgReturn / downDev) * Math.sqrt(252) : 0,
      profitFactor: isFinite(profitFactor) ? profitFactor : 999,
      avgRR,
      avgHoldingTime,
      maxConsecutiveLoss: maxCons,
      recoveryFactor: maxDrawdown > 0 ? totalProfit / (maxDrawdown * Math.max(1, peak)) : 0,
      calmarRatio: maxDrawdown > 0 ? (totalProfit / total) * 252 / maxDrawdown : 0,
      totalTrades: total,
    }
  },
}
