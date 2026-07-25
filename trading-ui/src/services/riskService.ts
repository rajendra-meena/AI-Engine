"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface RiskStatus {
  risk_score: number
  risk_grade: string
  trading_halt: boolean
  broker_disabled: boolean
  ai_disabled: boolean
  daily_trades: number
  daily_loss: number
  exposure: Record<string, unknown>
  drawdown: Record<string, unknown>
  config: Record<string, unknown>
  validation_stats: Record<string, unknown>
}

export interface ValidationResult {
  check: string
  status: string
  severity: string
  reason: string
  recommendation: string
  detail: Record<string, unknown>
}

export interface ValidationSummary {
  passed: boolean
  results: ValidationResult[]
  risk_score: number
  risk_grade: string
  execution_permitted: boolean
  rejected_by: string[]
  timestamp: string
}

class RiskService {
  private base = API_BASE

  async getStatus(): Promise<RiskStatus> {
    const res = await fetch(`${this.base}/api/risk/status`)
    if (!res.ok) throw new Error("Failed to fetch risk status")
    return res.json()
  }

  async getDashboard(): Promise<Record<string, unknown>> {
    const res = await fetch(`${this.base}/api/risk/dashboard`)
    if (!res.ok) throw new Error("Failed to fetch risk dashboard")
    return res.json()
  }

  async validate(intent: Record<string, unknown>): Promise<ValidationSummary> {
    const res = await fetch(`${this.base}/api/risk/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(intent),
    })
    if (!res.ok) throw new Error("Validation failed")
    return res.json()
  }

  async getLogs(limit = 100): Promise<{ logs: Record<string, unknown>[] }> {
    const res = await fetch(`${this.base}/api/risk/logs?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch risk logs")
    return res.json()
  }

  async getEvents(limit = 50): Promise<{ events: Record<string, unknown>[] }> {
    const res = await fetch(`${this.base}/api/risk/events?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch risk events")
    return res.json()
  }

  async getSettings(): Promise<Record<string, unknown>> {
    const res = await fetch(`${this.base}/api/risk/settings`)
    if (!res.ok) throw new Error("Failed to fetch risk settings")
    return res.json()
  }

  async updateSettings(settings: Record<string, unknown>): Promise<void> {
    await fetch(`${this.base}/api/risk/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    })
  }

  async emergency(action: string, reason = ""): Promise<void> {
    await fetch(`${this.base}/api/risk/emergency?action=${encodeURIComponent(action)}&reason=${encodeURIComponent(reason)}`, {
      method: "POST",
    })
  }

  async calculatePositionSize(params: Record<string, unknown>): Promise<Record<string, unknown>> {
    const res = await fetch(`${this.base}/api/risk/position-size`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    })
    if (!res.ok) throw new Error("Position sizing failed")
    return res.json()
  }
}

export const riskService = new RiskService()
