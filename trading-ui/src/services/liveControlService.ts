"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class LiveControlService {
  private base = API_BASE

  async getAccount() {
    const res = await fetch(`${this.base}/api/live/account`)
    if (!res.ok) throw new Error("Failed to fetch account")
    return res.json()
  }

  async getPositions() {
    const res = await fetch(`${this.base}/api/live/positions`)
    if (!res.ok) throw new Error("Failed to fetch positions")
    return res.json()
  }

  async getOrders() {
    const res = await fetch(`${this.base}/api/live/orders`)
    if (!res.ok) throw new Error("Failed to fetch orders")
    return res.json()
  }

  async getTrades() {
    const res = await fetch(`${this.base}/api/live/trades`)
    if (!res.ok) throw new Error("Failed to fetch trades")
    return res.json()
  }

  async getTradeDetail(tradeId: string) {
    const res = await fetch(`${this.base}/api/live/trades/${tradeId}`)
    if (!res.ok) throw new Error("Trade not found")
    return res.json()
  }

  async getPnl() {
    const res = await fetch(`${this.base}/api/live/pnl`)
    if (!res.ok) throw new Error("Failed to fetch P&L")
    return res.json()
  }

  async getStatus() {
    const res = await fetch(`${this.base}/api/live/status`)
    if (!res.ok) throw new Error("Failed to fetch status")
    return res.json()
  }

  async getReconciliation() {
    const res = await fetch(`${this.base}/api/live/reconciliation`)
    if (!res.ok) throw new Error("Failed to fetch reconciliation")
    return res.json()
  }

  async getEvents(limit = 100) {
    const res = await fetch(`${this.base}/api/live/events?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch events")
    return res.json()
  }

  async getHealth() {
    const res = await fetch(`${this.base}/api/live/health`)
    if (!res.ok) throw new Error("Failed to fetch health")
    return res.json()
  }
}

export const liveControlService = new LiveControlService()
