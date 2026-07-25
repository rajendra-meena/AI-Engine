"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class PerformanceService {
  private base = API_BASE

  async getOverview() {
    const res = await fetch(`${this.base}/api/performance/overview`)
    if (!res.ok) throw new Error("Failed to fetch overview")
    return res.json()
  }

  async getFunnel() {
    const res = await fetch(`${this.base}/api/performance/funnel`)
    if (!res.ok) throw new Error("Failed to fetch funnel")
    return res.json()
  }

  async getPnl() {
    const res = await fetch(`${this.base}/api/performance/pnl`)
    if (!res.ok) throw new Error("Failed to fetch P&L")
    return res.json()
  }

  async getTrades(limit = 100) {
    const res = await fetch(`${this.base}/api/performance/trades?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch trades")
    return res.json()
  }

  async getRMultiple() {
    const res = await fetch(`${this.base}/api/performance/r-multiple`)
    if (!res.ok) throw new Error("Failed to fetch R-multiple")
    return res.json()
  }

  async getCalibration() {
    const res = await fetch(`${this.base}/api/performance/calibration`)
    if (!res.ok) throw new Error("Failed to fetch calibration")
    return res.json()
  }

  async getRegimes() {
    const res = await fetch(`${this.base}/api/performance/regimes`)
    if (!res.ok) throw new Error("Failed to fetch regimes")
    return res.json()
  }

  async getTimeframes() {
    const res = await fetch(`${this.base}/api/performance/timeframes`)
    if (!res.ok) throw new Error("Failed to fetch timeframes")
    return res.json()
  }

  async getSymbols() {
    const res = await fetch(`${this.base}/api/performance/symbols`)
    if (!res.ok) throw new Error("Failed to fetch symbols")
    return res.json()
  }

  async getDirections() {
    const res = await fetch(`${this.base}/api/performance/directions`)
    if (!res.ok) throw new Error("Failed to fetch directions")
    return res.json()
  }

  async getBlocked() {
    const res = await fetch(`${this.base}/api/performance/blocked`)
    if (!res.ok) throw new Error("Failed to fetch blocked")
    return res.json()
  }

  async getEquityCurve() {
    const res = await fetch(`${this.base}/api/performance/equity-curve`)
    if (!res.ok) throw new Error("Failed to fetch equity curve")
    return res.json()
  }
}

export const performanceService = new PerformanceService()
