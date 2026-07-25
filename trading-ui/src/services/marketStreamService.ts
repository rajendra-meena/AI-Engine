"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class MarketStreamService {
  private base = API_BASE

  async getStatus() {
    const res = await fetch(`${this.base}/api/market-stream/status`)
    if (!res.ok) throw new Error("Failed to fetch stream status")
    return res.json()
  }

  async getSubscriptions() {
    const res = await fetch(`${this.base}/api/market-stream/subscriptions`)
    if (!res.ok) throw new Error("Failed to fetch subscriptions")
    return res.json()
  }

  async getHealth() {
    const res = await fetch(`${this.base}/api/market-stream/health`)
    if (!res.ok) throw new Error("Failed to fetch health")
    return res.json()
  }

  async reconnect() {
    const res = await fetch(`${this.base}/api/market-stream/reconnect`, { method: "POST" })
    if (!res.ok) throw new Error("Reconnect failed")
    return res.json()
  }
}

export const marketStreamService = new MarketStreamService()
