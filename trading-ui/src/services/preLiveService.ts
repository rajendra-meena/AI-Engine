"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class PreLiveService {
  private base = API_BASE

  async getStatus() {
    const res = await fetch(`${this.base}/api/pre-live/status`)
    if (!res.ok) throw new Error("Failed to fetch pre-live status")
    return res.json()
  }

  async runValidation(approvalId = "") {
    const params = approvalId ? `?approval_id=${encodeURIComponent(approvalId)}` : ""
    const res = await fetch(`${this.base}/api/pre-live/run${params}`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to run validation")
    return res.json()
  }

  async getReport(validationId: string) {
    const res = await fetch(`${this.base}/api/pre-live/report/${validationId}`)
    if (!res.ok) throw new Error("Report not found")
    return res.json()
  }

  async getHistory(limit = 10) {
    const res = await fetch(`${this.base}/api/pre-live/history?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch history")
    return res.json()
  }

  async getChecks() {
    const res = await fetch(`${this.base}/api/pre-live/checks`)
    if (!res.ok) throw new Error("Failed to fetch checks")
    return res.json()
  }

  async getBroker() {
    const res = await fetch(`${this.base}/api/pre-live/broker`)
    if (!res.ok) throw new Error("Failed to fetch broker info")
    return res.json()
  }

  async getMarketData() {
    const res = await fetch(`${this.base}/api/pre-live/market-data`)
    if (!res.ok) throw new Error("Failed to fetch market data")
    return res.json()
  }

  async getReconciliation() {
    const res = await fetch(`${this.base}/api/pre-live/reconciliation`)
    if (!res.ok) throw new Error("Failed to fetch reconciliation")
    return res.json()
  }

  async getSecurity() {
    const res = await fetch(`${this.base}/api/pre-live/security`)
    if (!res.ok) throw new Error("Failed to fetch security")
    return res.json()
  }

  async getKillSwitch() {
    const res = await fetch(`${this.base}/api/pre-live/kill-switch`)
    if (!res.ok) throw new Error("Failed to fetch kill switch")
    return res.json()
  }

  async getExecutionLock() {
    const res = await fetch(`${this.base}/api/pre-live/execution-lock`)
    if (!res.ok) throw new Error("Failed to fetch execution lock")
    return res.json()
  }

  async simulateFailure(scenario = "broker_unavailable") {
    const res = await fetch(`${this.base}/api/pre-live/simulate-failure?scenario=${encodeURIComponent(scenario)}`, {
      method: "POST",
    })
    if (!res.ok) throw new Error("Failed to simulate failure")
    return res.json()
  }
}

export const preLiveService = new PreLiveService()
