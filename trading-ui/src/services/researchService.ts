"use client"

import type { BacktestConfig, BacktestResult, OptimizationResult, OptimizationParam, WalkForwardResult, MonteCarloResult, PortfolioOptimizationResult, Experiment } from "@/store/useResearchStore"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export const researchService = {
  async runBacktest(config: BacktestConfig) {
    const res = await fetch(`${API_BASE}/api/backtests`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config }),
    })
    if (!res.ok) throw new Error("Backtest failed")
    return res.json() as Promise<BacktestResult>
  },

  async runWalkForward(config: BacktestConfig, wfType: string, trainWindow: number, testWindow: number) {
    const res = await fetch(`${API_BASE}/api/walkforward`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config, wfType, trainWindow, testWindow }),
    })
    if (!res.ok) throw new Error("Walk forward failed")
    return res.json() as Promise<WalkForwardResult>
  },

  async runValidation(params: Record<string, unknown>) {
    const res = await fetch(`${API_BASE}/api/backtest/validation/run`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    })
    if (!res.ok) throw new Error("Validation failed")
    return res.json()
  },

  async getValidation(valId: string) {
    const res = await fetch(`${API_BASE}/api/backtest/validation/${valId}`)
    if (!res.ok) throw new Error("Validation not found")
    return res.json()
  },

  async getValidationHistory() {
    const res = await fetch(`${API_BASE}/api/backtest/validation/history`)
    if (!res.ok) throw new Error("Failed to fetch history")
    return res.json()
  },

  async deleteValidation(valId: string) {
    const res = await fetch(`${API_BASE}/api/backtest/validation/${valId}`, { method: "DELETE" })
    if (!res.ok) throw new Error("Delete failed")
    return res.json()
  },

  async compareValidations(valIds: string[]) {
    const res = await fetch(`${API_BASE}/api/backtest/validation/compare`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(valIds),
    })
    if (!res.ok) throw new Error("Compare failed")
    return res.json()
  },

  async runMonteCarloSingle(trades: { net_pnl?: number; pnl?: number }[], simulation_count = 5000, seed?: number) {
    const res = await fetch(`${API_BASE}/api/backtest/validation/monte-carlo`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trades, simulation_count, seed }),
    })
    if (!res.ok) throw new Error("Monte Carlo failed")
    return res.json()
  },
}
