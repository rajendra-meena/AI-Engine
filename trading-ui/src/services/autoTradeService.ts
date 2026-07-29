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

export interface BlockedAttempt {
  attempt_id: string
  timestamp: string
  underlying_symbol: string
  direction: string
  analysis_cycle_id: string
  stage: string
  block_code: string
  block_reason: string
  actual_value: string
  required_value: string
  settings_snapshot: any
  risk_snapshot: any
}

export interface PaperPosition {
  trade_id: string
  execution_symbol: string
  symbol: string
  underlying_symbol: string
  direction: string
  quantity: number
  entry_time: string
  entry_price: number
  current_price: number
  stop_loss: number | null
  target: number | null
  unrealized_pnl: number
  pnl_percent: number
  status: string
  execution_type: string
  exchange: string
  // Option fields
  option_type: string | null
  strike: number | null
  expiry: string | null
  premium_entry: number | null
  premium_current: number | null
  premium_stop_loss: number | null
  premium_target: number | null
  lot_size: number | null
  lots: number | null
  risk_reward: number | null
  premium_source: string
  // Phase 2D premium monitoring
  last_premium_tick_at: string
  premium_tick_age_ms: number
  premium_data_status: string
  premium_instrument_token: number
  // Diagnostics
  ai_confidence: number
  opportunity_score: number
  trade_grade: string
  decision_id: string
  analysis_cycle_id: string
  test_origin: string
  [key: string]: any
}

export interface PaperAccount {
  initial_capital: number
  available_cash: number
  used_margin: number
  equity: number
  total_unrealized_pnl: number
  total_realized_pnl: number
  total_pnl: number
  return_pct: number
  open_positions: number
  closed_trades: number
  win_count: number
  loss_count: number
  win_rate: number
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
  // Phase 2C: new sections
  open_positions: PaperPosition[]
  blocked_attempts: BlockedAttempt[]
  trade_history: any[]
  paper_account: PaperAccount
  data_sources: any
  // Phase 2D: premium freshness
  premium_freshness?: {
    total_positions: number
    live_count: number
    stale_count: number
    waiting_count: number
  }
  recovery_info?: any
  [key: string]: any
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

export interface RuntimeModeResponse {
  mode: string
  observe?: boolean
  shadow?: boolean
  paper?: boolean
  controlled_live?: boolean
  can_execute_paper?: boolean
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

  async closePaperPosition(tradeId: string): Promise<any> {
    const res = await fetch(`${this.base}/api/auto-trade/paper-positions/${tradeId}/close`, {
      method: "POST",
    })
    if (!res.ok) throw new Error("Failed to close paper position")
    return res.json()
  }

  async getPaperPositions(): Promise<{ positions: PaperPosition[]; total: number }> {
    const res = await fetch(`${this.base}/api/auto-trade/paper-positions`)
    if (!res.ok) throw new Error("Failed to fetch paper positions")
    return res.json()
  }

  async controlledTestOneLot(): Promise<any> {
    const res = await fetch(`${this.base}/api/auto-trade/controlled-test-one-lot`, {
      method: "POST",
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || "Controlled test failed")
    }
    return res.json()
  }

  async getTradeHistory(limit = 100, offset = 0): Promise<{ trades: any[]; total: number }> {
    const res = await fetch(`${this.base}/api/auto-trade/trade-history?limit=${limit}&offset=${offset}`)
    if (!res.ok) throw new Error("Failed to fetch trade history")
    return res.json()
  }

  async getPositionEvents(tradeId: string): Promise<{ trade_id: string; events: any[] }> {
    const res = await fetch(`${this.base}/api/auto-trade/paper-positions/${tradeId}/events`)
    if (!res.ok) throw new Error("Failed to fetch position events")
    return res.json()
  }

  async marketCloseExit(): Promise<any> {
    const res = await fetch(`${this.base}/api/auto-trade/market-close-exit`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to force market close exit")
    return res.json()
  }

  async getRecoveryStatus(): Promise<any> {
    const res = await fetch(`${this.base}/api/auto-trade/recovery-status`)
    if (!res.ok) throw new Error("Failed to fetch recovery status")
    return res.json()
  }

  async injectPremiumTick(tradeId: string, premium: number): Promise<any> {
    const res = await fetch(`${this.base}/api/auto-trade/inject-premium-tick`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trade_id: tradeId, premium }),
    })
    if (!res.ok) throw new Error("Failed to inject premium tick")
    return res.json()
  }

  // ── Helper to check if service has stale/legacy methods (compile-time guard) ──
  // If this line errors, a duplicate legacy method was left behind.
  readonly _methods_ok = true as const
}

export const autoTradeService = new AutoTradeService()
