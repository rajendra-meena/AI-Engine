"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class OrchestratorService {
  private base = API_BASE

  async getStatus() {
    const res = await fetch(`${this.base}/api/orchestrator/status`)
    if (!res.ok) throw new Error("Failed to fetch orchestrator status")
    return res.json()
  }

  async analyze(params: Record<string, unknown>) {
    const res = await fetch(`${this.base}/api/orchestrator/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    })
    if (!res.ok) throw new Error("Analysis failed")
    return res.json()
  }

  async paperTrade(params: Record<string, unknown>) {
    const res = await fetch(`${this.base}/api/orchestrator/paper-trade`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    })
    if (!res.ok) throw new Error("Paper trade failed")
    return res.json()
  }

  async validate(params: Record<string, unknown>) {
    const res = await fetch(`${this.base}/api/orchestrator/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    })
    if (!res.ok) throw new Error("Validation failed")
    return res.json()
  }

  async getTrace(traceId: string) {
    const res = await fetch(`${this.base}/api/orchestrator/trace/${traceId}`)
    if (!res.ok) throw new Error("Trace not found")
    return res.json()
  }

  async getHistory(limit = 50) {
    const res = await fetch(`${this.base}/api/orchestrator/history?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch history")
    return res.json()
  }

  async getLastDecision() {
    const res = await fetch(`${this.base}/api/orchestrator/last-decision`)
    if (!res.ok) throw new Error("Failed to fetch last decision")
    return res.json()
  }
}

export const orchestratorService = new OrchestratorService()
