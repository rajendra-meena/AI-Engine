"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class CommandCenterService {
  private base = API_BASE

  async getCommandCenter() {
    const res = await fetch(`${this.base}/api/operations/command-center`)
    if (!res.ok) throw new Error("Failed to fetch command center data")
    return res.json()
  }

  async getStatus() {
    const res = await fetch(`${this.base}/api/operations/command-center/status`)
    if (!res.ok) throw new Error("Failed to fetch status")
    return res.json()
  }

  async getSafety() {
    const res = await fetch(`${this.base}/api/operations/command-center/safety`)
    if (!res.ok) throw new Error("Failed to fetch safety")
    return res.json()
  }

  async getSystem() {
    const res = await fetch(`${this.base}/api/operations/command-center/system`)
    if (!res.ok) throw new Error("Failed to fetch system")
    return res.json()
  }

  async getTrading() {
    const res = await fetch(`${this.base}/api/operations/command-center/trading`)
    if (!res.ok) throw new Error("Failed to fetch trading")
    return res.json()
  }

  async getRisk() {
    const res = await fetch(`${this.base}/api/operations/command-center/risk`)
    if (!res.ok) throw new Error("Failed to fetch risk")
    return res.json()
  }

  async getMarket() {
    const res = await fetch(`${this.base}/api/operations/command-center/market`)
    if (!res.ok) throw new Error("Failed to fetch market")
    return res.json()
  }

  async getBroker() {
    const res = await fetch(`${this.base}/api/operations/command-center/broker`)
    if (!res.ok) throw new Error("Failed to fetch broker")
    return res.json()
  }

  async getOrders() {
    const res = await fetch(`${this.base}/api/operations/command-center/orders`)
    if (!res.ok) throw new Error("Failed to fetch orders")
    return res.json()
  }

  async getPositions() {
    const res = await fetch(`${this.base}/api/operations/command-center/positions`)
    if (!res.ok) throw new Error("Failed to fetch positions")
    return res.json()
  }

  async getCanary() {
    const res = await fetch(`${this.base}/api/operations/command-center/canary`)
    if (!res.ok) throw new Error("Failed to fetch canary")
    return res.json()
  }

  async getRollout() {
    const res = await fetch(`${this.base}/api/operations/command-center/rollout`)
    if (!res.ok) throw new Error("Failed to fetch rollout")
    return res.json()
  }

  async getReconciliation() {
    const res = await fetch(`${this.base}/api/operations/command-center/reconciliation`)
    if (!res.ok) throw new Error("Failed to fetch reconciliation")
    return res.json()
  }

  async getIncidents() {
    const res = await fetch(`${this.base}/api/operations/command-center/incidents`)
    if (!res.ok) throw new Error("Failed to fetch incidents")
    return res.json()
  }

  async getRecovery() {
    const res = await fetch(`${this.base}/api/operations/command-center/recovery`)
    if (!res.ok) throw new Error("Failed to fetch recovery")
    return res.json()
  }

  async getIntegrity() {
    const res = await fetch(`${this.base}/api/operations/command-center/integrity`)
    if (!res.ok) throw new Error("Failed to fetch integrity")
    return res.json()
  }

  async getMetrics() {
    const res = await fetch(`${this.base}/api/operations/command-center/metrics`)
    if (!res.ok) throw new Error("Failed to fetch metrics")
    return res.json()
  }

  async getEvents(limit = 50) {
    const res = await fetch(`${this.base}/api/operations/command-center/events?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch events")
    return res.json()
  }
}

export const commandCenterService = new CommandCenterService()
