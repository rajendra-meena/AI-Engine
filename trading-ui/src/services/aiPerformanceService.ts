/* eslint-disable @typescript-eslint/no-explicit-any */
"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface TradeEvaluation {
  id: string
  prediction_id: string
  overall_score: number
  outcome_class: "Excellent" | "Good" | "Average" | "Poor" | "Failed"
  entry_accuracy: number
  exit_quality: number
  sl_quality: number
  target_quality: number
  mfe_mae_ratio: number
  slippage_impact: number
  evaluated_at: string
}

export interface StrategyMetrics {
  strategy_id: string
  strategy_name: string
  total_trades: number
  win_rate: number
  profit_factor: number
  expectancy: number
  sharpe_ratio: number | null
  sortino_ratio: number | null
  calmar_ratio: number | null
  recovery_factor: number | null
  max_drawdown: number
  avg_holding_hours: number
  avg_r_multiple: number
  largest_win: number
  largest_loss: number
  consecutive_wins: number
  consecutive_losses: number
}

export interface PatternMetrics {
  pattern_name: string
  pattern_type: string | null
  total_occurrences: number
  win_count: number
  loss_count: number
  win_rate: number
  avg_return: number
  failure_rate: number
  avg_duration_hours: number
}

export interface MarketConditionMetrics {
  condition_type: string
  condition_value: string
  total_trades: number
  win_count: number
  win_rate: number
  avg_return: number
  profit_factor: number
}

export interface CalibrationBucket {
  bucket_label: string
  min: number
  max: number
  avg_confidence: number
  actual_accuracy: number
  calibration_error: number
  count: number
}

export interface CalibrationMetrics {
  ece: number
  mce: number
  bias: string
  bias_magnitude: number
  sample_count: number
  confidence_accuracy: number
  reliability_curve: CalibrationBucket[]
}

export interface MistakeRecord {
  id: string
  prediction_id: string
  mistake_type: string
  severity: string
  description: string
  impact: number
  lesson: string | null
}

export interface MistakeSummary {
  total_count: number
  by_type: Record<string, number>
  by_severity: Record<string, number>
  total_impact: number
  most_common: string
}

export interface AIPerformanceDashboard {
  overview: {
    total_evaluated: number
    avg_score: number
    outcome_distribution: Record<string, number>
  }
  strategies: StrategyMetrics[]
  patterns: PatternMetrics[]
  market_conditions: MarketConditionMetrics[]
  calibration: CalibrationMetrics
  mistakes: { summary: MistakeSummary; mistakes: MistakeRecord[] }
  trades_count: number
}

class AIPerformanceService {
  private base = API_BASE

  async getOverview(): Promise<any> {
    const res = await fetch(`${this.base}/api/ai/performance/overview`)
    if (!res.ok) throw new Error("Failed to fetch overview")
    return res.json()
  }

  async getStrategies(): Promise<{ strategies: StrategyMetrics[] }> {
    const res = await fetch(`${this.base}/api/ai/performance/strategies`)
    if (!res.ok) throw new Error("Failed to fetch strategies")
    return res.json()
  }

  async getPatterns(): Promise<{ patterns: PatternMetrics[] }> {
    const res = await fetch(`${this.base}/api/ai/performance/patterns`)
    if (!res.ok) throw new Error("Failed to fetch patterns")
    return res.json()
  }

  async getMarketConditions(): Promise<{ conditions: MarketConditionMetrics[] }> {
    const res = await fetch(`${this.base}/api/ai/performance/market`)
    if (!res.ok) throw new Error("Failed to fetch market conditions")
    return res.json()
  }

  async getCalibration(): Promise<CalibrationMetrics> {
    const res = await fetch(`${this.base}/api/ai/performance/calibration`)
    if (!res.ok) throw new Error("Failed to fetch calibration")
    return res.json()
  }

  async getMistakes(): Promise<{ summary: MistakeSummary; mistakes: MistakeRecord[] }> {
    const res = await fetch(`${this.base}/api/ai/performance/mistakes`)
    if (!res.ok) throw new Error("Failed to fetch mistakes")
    return res.json()
  }

  async getTrades(limit = 50, offset = 0, outcomeClass?: string): Promise<{ trades: TradeEvaluation[]; total: number }> {
    let url = `${this.base}/api/ai/performance/trades?limit=${limit}&offset=${offset}`
    if (outcomeClass) url += `&outcome_class=${encodeURIComponent(outcomeClass)}`
    const res = await fetch(url)
    if (!res.ok) throw new Error("Failed to fetch trades")
    return res.json()
  }

  async getDashboard(): Promise<AIPerformanceDashboard> {
    const res = await fetch(`${this.base}/api/ai/performance/dashboard`)
    if (!res.ok) throw new Error("Failed to fetch dashboard")
    return res.json()
  }

  async evaluateAll(): Promise<{ success: boolean; evaluated: number }> {
    const res = await fetch(`${this.base}/api/ai/performance/evaluate`, { method: "POST" })
    if (!res.ok) throw new Error("Evaluation failed")
    return res.json()
  }

  async exportData(fmt = "json", limit = 1000): Promise<any> {
    const res = await fetch(`${this.base}/api/ai/performance/export?fmt=${fmt}&limit=${limit}`)
    if (!res.ok) throw new Error("Export failed")
    return res.json()
  }
}

export const aiPerformanceService = new AIPerformanceService()
