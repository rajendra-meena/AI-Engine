/* eslint-disable @typescript-eslint/no-explicit-any */
"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface AutoTradeEngine {
  state: string
  running: boolean
  paused: boolean
  analysis_enabled: boolean
  mode: string
  auto_execute_paper?: boolean
}

export interface ReadinessCheck {
  [system: string]: string
}

export interface ScanInfo {
  configured_symbols: number
  symbols_with_live_ticks: number
  symbols_analysed: number
  analyses_completed_total: number
  no_trade_decisions_total: number
  raw_directional_signals_total: number
  score_qualified_candidates_total: number
  trade_plans_created_total: number
  risk_approved_total: number
  risk_blocked_total: number
  execution_attempts_total: number
  execution_failed_total: number
  paper_trades_created_total: number
  last_analysis_at: string | null
  last_candle_closed_at: string | null
}

export interface CurrentMarketAnalysis {
  symbol: string
  status: string
  direction: string
  display_decision: string
  bias: string
  confidence: number
  opportunity_score: number
  reason: string
  reject_reasons: string[]
  risk_status: string
  analysed_at: string
  // Option execution fields (present when option_buying is active)
  execution_type?: string
  option_type?: string
  option_strike?: number
  option_expiry?: string
  option_premium?: number
  option_lot_size?: number
  option_lots?: number
}

export interface OpportunityCandidate {
  symbol: string
  opportunity_score: number
  max_score: number
  confidence: number
  grade: string
  regime: string
  strategy: string
  direction: string
  risk_status: string
  reasons: string[]
  reject_reasons: string[]
  selected: boolean
}

export interface TradePlan {
  plan_id: string
  symbol: string
  direction: string
  entry_price: number
  stop_loss: number
  target: number
  quantity: number
  notional: number
  max_loss: number
  estimated_reward: number
  risk_reward: number
  ai_confidence: number
  grade: string
  strategy: string
  regime: string
  plan_status: string
  [key: string]: any
}

export interface ApprovalResult {
  approved: boolean
  decision: string
  gates: { name: string; passed: boolean; detail: string }[]
  blocking_reasons: string[]
  [key: string]: any
}

export interface RiskResult {
  execution_permitted: boolean
  risk_score: number
  risk_grade: string
  rejected_by: string[]
  [key: string]: any
}

export interface WorkspaceResponse {
  engine: AutoTradeEngine
  readiness: ReadinessCheck
  scan: ScanInfo
  current_market_analysis?: CurrentMarketAnalysis[]
  candidates: OpportunityCandidate[]
  selected_opportunity: OpportunityCandidate | null
  decision: any
  regime: any
  approval: ApprovalResult | null
  risk: RiskResult | null
  trade_plan: TradePlan | null
  order: any
  position: any
  performance: any
  no_trade_reasons?: string[]
  blocking_reasons?: string[]
  ai_explanation?: any
  mtf_agreement?: any
  signal_validations?: any
  trade_quality?: any
  false_signal_check?: any
  alerts: any[]
  timeline: any[]
  errors: string[]
}

export interface EngineControlResponse {
  success: boolean
  state: string
  message: string
  blocked_systems?: string[]
}

export interface AutoTradeSettings {
  market_universe: string
  max_trades_per_day: number
  min_ai_confidence: number
  min_trade_grade: string
  min_risk_reward: number
  allow_buy_trades: boolean
  allow_sell_trades: boolean
  auto_execute_paper_trades: boolean
  execution_type: string
  lot_mode: string
  manual_lots: number
  max_auto_lots: number
  strike_mode: string
  expiry_mode: string
  premium_source: string
  settings_version: number
  updated_at: string
  success?: boolean
  errors?: string[]
}

export interface OptionExecutionPlan {
  underlying_symbol: string
  direction: string
  option_type: string
  expiry: string
  strike: number
  lot_size: number
  lots: number
  premium: number
  premium_source: string
  total_cost: number
  capital_required: number
  premium_entry: number
  premium_sl: number
  premium_target: number
  risk_per_lot: number
}

class AutoTradeService {
  private base = API_BASE

  async getWorkspace(): Promise<WorkspaceResponse> {
    const res = await fetch(`${this.base}/api/auto-trade/workspace`)
    if (!res.ok) throw new Error("Failed to fetch auto-trade workspace")
    return res.json()
  }

  async start(): Promise<EngineControlResponse> {
    const res = await fetch(`${this.base}/api/auto-trade/start`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to start engine")
    return res.json()
  }

  async stop(): Promise<EngineControlResponse> {
    const res = await fetch(`${this.base}/api/auto-trade/stop`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to stop engine")
    return res.json()
  }

  async pause(): Promise<EngineControlResponse> {
    const res = await fetch(`${this.base}/api/auto-trade/pause`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to pause engine")
    return res.json()
  }

  async resume(): Promise<EngineControlResponse> {
    const res = await fetch(`${this.base}/api/auto-trade/resume`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to resume engine")
    return res.json()
  }

  async getStatus(): Promise<{ engine: AutoTradeEngine; readiness: ReadinessCheck }> {
    const res = await fetch(`${this.base}/api/auto-trade/status`)
    if (!res.ok) throw new Error("Failed to fetch engine status")
    return res.json()
  }

  async setRuntimeMode(mode: string): Promise<RuntimeModeResponse> {
    const res = await fetch(`${this.base}/api/auto-trade/runtime-mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    })
    if (!res.ok) throw new Error("Failed to set runtime mode")
    return res.json()
  }

  async getRuntimeMode(): Promise<RuntimeModeResponse> {
    const res = await fetch(`${this.base}/api/auto-trade/runtime-mode`)
    if (!res.ok) throw new Error("Failed to fetch runtime mode")
    return res.json()
  }

  async getSettings(): Promise<AutoTradeSettings> {
    const res = await fetch(`${this.base}/api/auto-trade/settings`)
    if (!res.ok) throw new Error("Failed to fetch settings")
    return res.json()
  }

  async updateSettings(settings: Record<string, any>): Promise<AutoTradeSettings> {
    const res = await fetch(`${this.base}/api/auto-trade/settings`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    })
    if (!res.ok) throw new Error("Failed to update settings")
    return res.json()
  }
}

export const autoTradeService = new AutoTradeService()
