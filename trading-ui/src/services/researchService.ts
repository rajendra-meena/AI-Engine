/**
 * researchService.ts
 *
 * Quant Research Lab API client — backtesting, optimization, walk-forward, Monte Carlo, portfolio.
 */

import apiClient from "@/lib/api"
import type { BacktestConfig, BacktestResult, OptimizationResult, OptimizationParam, WalkForwardResult, WalkForwardType, MonteCarloResult, PortfolioOptimizationResult, Experiment } from "@/store/useResearchStore"

export const researchService = {
  async runBacktest(config: BacktestConfig, strategyRules?: { entry: Record<string, unknown>[]; exit: Record<string, unknown>[] }) {
    const { data } = await apiClient.post("/api/backtests", { config, strategyRules })
    return data as BacktestResult
  },

  async runWalkForward(config: BacktestConfig, wfType: WalkForwardType, trainWindow: number, testWindow: number, strategyRules?: { entry: Record<string, unknown>[]; exit: Record<string, unknown>[] }) {
    const { data } = await apiClient.post("/api/walkforward", { config, wfType, trainWindow, testWindow, strategyRules })
    return data as WalkForwardResult
  },

  async runMonteCarlo(backtestResult: BacktestResult, simulations: number, seed?: number) {
    const { data } = await apiClient.post("/api/montecarlo", { backtestResult, simulations, seed })
    return data as MonteCarloResult
  },

  async runOptimization(config: BacktestConfig, params: OptimizationParam[], method: string, strategyId?: string) {
    const { data } = await apiClient.post("/api/optimization", { config, params, method, strategyId })
    return data as OptimizationResult[]
  },

  async optimizePortfolio(strategies: { id: string; name: string; metrics: BacktestResult }[]) {
    const { data } = await apiClient.post("/api/portfolio/optimize", { strategies })
    return data as PortfolioOptimizationResult
  },

  async getExperiments() {
    const { data } = await apiClient.get("/api/research/history")
    return data as Experiment[]
  },

  async saveExperiment(exp: Partial<Experiment>) {
    const { data } = await apiClient.post("/api/research/history", exp)
    return data as Experiment
  },

  async deleteExperiment(id: string) {
    await apiClient.delete(`/api/research/history/${id}`)
  },

  async getResearchReport(experimentId: string) {
    const { data } = await apiClient.get(`/api/research/reports/${experimentId}`)
    return data
  },

  /** Client-side metrics computation from trade list */
  computeMetrics(trades: Array<{ pnl: number; duration?: number }>): Partial<BacktestResult> {
    const total = trades.length
    if (!total) return {}
    const wins = trades.filter((t) => t.pnl > 0)
    const losses = trades.filter((t) => t.pnl <= 0)
    const netProfit = trades.reduce((a, t) => a + t.pnl, 0)
    const grossProfit = wins.reduce((a, t) => a + t.pnl, 0)
    const grossLoss = Math.abs(losses.reduce((a, t) => a + t.pnl, 0))
    const winRate = (wins.length / total) * 100
    const avgWin = wins.length ? grossProfit / wins.length : 0
    const avgLoss = losses.length ? grossLoss / losses.length : 1
    const profitFactor = grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? 999 : 0
    const avgTrade = netProfit / total
    const avgHolding = trades.reduce((a, t) => a + (t.duration || 0), 0) / total

    let peak = 0, maxDD = 0, maxDDPct = 0, cum = 0
    for (const t of trades) { cum += t.pnl; if (cum > peak) peak = cum; const dd = peak - cum; if (dd > maxDD) maxDD = dd; if (peak > 0) maxDDPct = Math.max(maxDDPct, dd / peak * 100) }

    const returns = trades.map((t) => t.pnl)
    const avg = returns.reduce((a, r) => a + r, 0) / total
    const variance = returns.reduce((a, r) => a + (r - avg) ** 2, 0) / total
    const std = Math.sqrt(variance) || 1
    const negReturns = returns.filter((r) => r < 0)
    const downDev = negReturns.length ? Math.sqrt(negReturns.reduce((a, r) => a + r ** 2, 0) / negReturns.length) : 1

    let consecW = 0, consecL = 0, maxCW = 0, maxCL = 0
    for (const t of trades) { if (t.pnl > 0) { consecW++; consecL = 0; if (consecW > maxCW) maxCW = consecW } else { consecL++; consecW = 0; if (consecL > maxCL) maxCL = consecL } }

    return { totalTrades: total, wins: wins.length, losses: losses.length, winRate, netProfit, grossProfit, grossLoss, profitFactor, expectancy: avgWin * (winRate / 100) - avgLoss * (1 - winRate / 100), sharpe: (avg / std) * Math.sqrt(252), sortino: (avg / downDev) * Math.sqrt(252), calmar: maxDDPct > 0 ? (netProfit / total) * 252 / maxDDPct : 0, recoveryFactor: maxDD > 0 ? netProfit / maxDD : 0, sqn: std > 0 ? Math.sqrt(total) * avg / std : 0, avgTrade, avgHoldingTime: avgHolding, maxDrawdown: maxDD, maxDrawdownPercent: maxDDPct, consecWins: maxCW, consecLosses: maxCL, exposure: (wins.length + losses.length) / total * 100 }
  },

  /** Monte Carlo simulation */
  simulateMonteCarlo(trades: number[], simulations: number, seed?: number): MonteCarloResult {
    const rng = seed ? (() => { let s = seed; return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646 } })() : Math.random
    const results: number[] = []
    for (let s = 0; s < simulations; s++) { let total = 0; for (let i = 0; i < trades.length; i++) total += trades[Math.floor(rng() * trades.length)]; results.push(total) }
    results.sort((a, b) => a - b)
    const mean = results.reduce((a, r) => a + r, 0) / simulations
    const median = results[Math.floor(simulations / 2)]
    const variance = results.reduce((a, r) => a + (r - mean) ** 2, 0) / simulations
    const std = Math.sqrt(variance)
    const positive = results.filter((r) => r > 0).length
    return { simulations, meanReturn: mean, medianReturn: median, stdReturn: std, var95: results[Math.floor(simulations * 0.05)], var99: results[Math.floor(simulations * 0.01)], maxReturn: results[results.length - 1], minReturn: results[0], percentPositive: (positive / simulations) * 100, distribution: [{ range: `${Math.round(results[0])}-${Math.round(results[results.length - 1])}`, count: simulations }], equityBands: [] }
  },
}
