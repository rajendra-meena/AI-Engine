"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class BacktestService {
  private base = API_BASE

  async create(params: Record<string, unknown>) {
    const res = await fetch(`${this.base}/api/backtest/create`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params),
    })
    if (!res.ok) throw new Error("Failed to create backtest")
    return res.json()
  }

  async start(backtestId: string) {
    const res = await fetch(`${this.base}/api/backtest/${backtestId}/start`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to start backtest")
    return res.json()
  }

  async getStatus(backtestId: string) {
    const res = await fetch(`${this.base}/api/backtest/${backtestId}/status`)
    if (!res.ok) throw new Error("Failed to fetch status")
    return res.json()
  }

  async getResult(backtestId: string) {
    const res = await fetch(`${this.base}/api/backtest/${backtestId}/result`)
    if (!res.ok) throw new Error("Failed to fetch result")
    return res.json()
  }

  async getTrades(backtestId: string) {
    const res = await fetch(`${this.base}/api/backtest/${backtestId}/trades`)
    if (!res.ok) throw new Error("Failed to fetch trades")
    return res.json()
  }

  async getHistory() {
    const res = await fetch(`${this.base}/api/backtest/history`)
    if (!res.ok) throw new Error("Failed to fetch history")
    return res.json()
  }

  async deleteBacktest(backtestId: string) {
    const res = await fetch(`${this.base}/api/backtest/${backtestId}`, { method: "DELETE" })
    if (!res.ok) throw new Error("Failed to delete")
    return res.json()
  }

  async validateData(data: Record<string, unknown>[], timeframe = "15m") {
    const res = await fetch(`${this.base}/api/backtest/validate-data?timeframe=${timeframe}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error("Validation failed")
    return res.json()
  }
}

export const backtestService = new BacktestService()
