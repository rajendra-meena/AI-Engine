/* eslint-disable @typescript-eslint/no-explicit-any */
"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface RegimeSnapshot {
  id: string
  symbol: string
  timestamp: string
  regime: string
  regime_category: string
  confidence: number
  supporting_factors: string[]
  duration_bars: number
  duration_minutes: number
  stability_score: number
  transition_probability: number
  previous_regime: string | null
  regime_age_bars: number
  strategy_recommendation?: StrategyRecommendation
}

export interface StrategyRecommendation {
  regime: string
  primary: string
  secondary: string
  avoid: string[]
  expected_win_rate: number
  historical_success: number
  confidence: number
  reasoning: string
}

export interface RegimeTransition {
  id: string
  symbol: string
  timestamp: string
  from_regime: string
  to_regime: string
  transition_type: string
  confidence: number
  duration_bars: number
}

export interface RegimePerformance {
  [regime: string]: {
    total_trades: number
    win_count: number
    loss_count: number
    win_rate: number
    net_pnl: number
    avg_confidence: number
    avg_holding_hours: number
    profit_factor: number
    max_drawdown: number
  }
}

export interface StrategyComparisonEntry {
  strategy_id: string
  strategy_name: string
  total_trades: number
  win_rate: number
  profit_factor: number
  sharpe_ratio: number | null
  sortino_ratio: number | null
  expected_return: number
  max_drawdown: number
  avg_holding_hours: number
  consistency_score: number
  trade_count: number
}

export interface RegimeExplanation {
  regime: string
  confidence: number
  primary_reason: string
  supporting_evidence: string[]
  recommended_strategy: string
  avoid_strategies: string[]
  strategy_reasoning: string
  market_conditions_summary: string
}

export interface ConfidenceAdjustment {
  adjusted_confidence: number
  original_confidence: number
  adjustments: { factor: string; regime: string; impact: number; reason: string }[]
  total_adjustment: number
  current_regime: string | null
}

class RegimeService {
  private base = API_BASE

  async getCurrent(symbol = "NIFTY 50"): Promise<RegimeSnapshot> {
    const res = await fetch(`${this.base}/api/regime/current?symbol=${encodeURIComponent(symbol)}`)
    if (!res.ok) throw new Error("Failed to fetch current regime")
    return res.json()
  }

  async getHistory(symbol = "NIFTY 50", count = 100): Promise<{ snapshots: RegimeSnapshot[] }> {
    const res = await fetch(`${this.base}/api/regime/history?symbol=${encodeURIComponent(symbol)}&count=${count}`)
    if (!res.ok) throw new Error("Failed to fetch regime history")
    return res.json()
  }

  async getTransitions(symbol = "NIFTY 50", count = 50): Promise<{ transitions: RegimeTransition[] }> {
    const res = await fetch(`${this.base}/api/regime/transitions?symbol=${encodeURIComponent(symbol)}&count=${count}`)
    if (!res.ok) throw new Error("Failed to fetch transitions")
    return res.json()
  }

  async getStrategies(symbol = "NIFTY 50"): Promise<StrategyRecommendation> {
    const res = await fetch(`${this.base}/api/regime/strategies?symbol=${encodeURIComponent(symbol)}`)
    if (!res.ok) throw new Error("Failed to fetch regime strategies")
    return res.json()
  }

  async getPerformance(): Promise<{ regimes: RegimePerformance }> {
    const res = await fetch(`${this.base}/api/regime/performance`)
    if (!res.ok) throw new Error("Failed to fetch regime performance")
    return res.json()
  }

  async getComparison(): Promise<{ comparison: StrategyComparisonEntry[] }> {
    const res = await fetch(`${this.base}/api/regime/comparison`)
    if (!res.ok) throw new Error("Failed to fetch strategy comparison")
    return res.json()
  }

  async getExplain(symbol = "NIFTY 50"): Promise<RegimeExplanation> {
    const res = await fetch(`${this.base}/api/regime/explain?symbol=${encodeURIComponent(symbol)}`)
    if (!res.ok) throw new Error("Failed to fetch regime explanation")
    return res.json()
  }

  async getRegimeList(): Promise<{ regimes: any[] }> {
    const res = await fetch(`${this.base}/api/regime/list`)
    if (!res.ok) throw new Error("Failed to fetch regime list")
    return res.json()
  }

  async getConfidenceAdjustment(symbol = "NIFTY 50", baseConfidence = 50): Promise<ConfidenceAdjustment> {
    const res = await fetch(`${this.base}/api/regime/confidence-adjustment?symbol=${encodeURIComponent(symbol)}&base_confidence=${baseConfidence}`)
    if (!res.ok) throw new Error("Failed to fetch confidence adjustment")
    return res.json()
  }
}

export const regimeService = new RegimeService()
