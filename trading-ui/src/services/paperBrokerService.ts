"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class PaperBrokerService {
  private base = API_BASE

  async getStatus() {
    const res = await fetch(`${this.base}/api/paper/status`)
    if (!res.ok) throw new Error("Failed to fetch status")
    return res.json()
  }

  async getAccount() {
    const res = await fetch(`${this.base}/api/paper/account`)
    if (!res.ok) throw new Error("Failed to fetch account")
    return res.json()
  }

  async getPositions() {
    const res = await fetch(`${this.base}/api/paper/positions`)
    if (!res.ok) throw new Error("Failed to fetch positions")
    return res.json()
  }

  async getOrders() {
    const res = await fetch(`${this.base}/api/paper/orders`)
    if (!res.ok) throw new Error("Failed to fetch orders")
    return res.json()
  }

  async getTrades() {
    const res = await fetch(`${this.base}/api/paper/trades`)
    if (!res.ok) throw new Error("Failed to fetch trades")
    return res.json()
  }

  async getPnl() {
    const res = await fetch(`${this.base}/api/paper/pnl`)
    if (!res.ok) throw new Error("Failed to fetch P&L")
    return res.json()
  }

  async getEvents() {
    const res = await fetch(`${this.base}/api/paper/events`)
    if (!res.ok) throw new Error("Failed to fetch events")
    return res.json()
  }

  async start() {
    return (await fetch(`${this.base}/api/paper/start`, { method: "POST" })).json()
  }

  async pause() {
    return (await fetch(`${this.base}/api/paper/pause`, { method: "POST" })).json()
  }

  async resume() {
    return (await fetch(`${this.base}/api/paper/resume`, { method: "POST" })).json()
  }

  async stop() {
    return (await fetch(`${this.base}/api/paper/stop`, { method: "POST" })).json()
  }

  async reset() {
    return (await fetch(`${this.base}/api/paper/reset`, { method: "POST" })).json()
  }

  async closePosition(tradeId: string) {
    return (await fetch(`${this.base}/api/paper/close-position/${tradeId}`, { method: "POST" })).json()
  }
}

export const paperBrokerService = new PaperBrokerService()
