/* eslint-disable @typescript-eslint/no-explicit-any */
"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface AutoTradeEngine {
  state: string
  running: boolean
  paused: boolean
  mode: string
}

export interface ReadinessCheck {
  [system: string]: string
}

export interface ScanInfo {
  symbols_scanned: number
  candidates_found: number
  last_scan_time: string | null
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
}

export const autoTradeService = new AutoTradeService()
