"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class LiveExecutionService {
  private base = API_BASE

  async getStatus() {
    const res = await fetch(`${this.base}/api/live-execution/status`)
    if (!res.ok) throw new Error("Failed to fetch execution status")
    return res.json()
  }

  async getBrokerSession() {
    const res = await fetch(`${this.base}/api/live-execution/broker-session`)
    if (!res.ok) throw new Error("Failed to fetch broker session")
    return res.json()
  }

  async runPreflight(symbol: string, side = "BUY", quantity = 0, price?: number, stopLoss?: number, target?: number) {
    const params = new URLSearchParams()
    params.set("symbol", symbol)
    params.set("side", side)
    params.set("quantity", String(quantity))
    if (price) params.set("price", String(price))
    if (stopLoss) params.set("stop_loss", String(stopLoss))
    if (target) params.set("target", String(target))
    const res = await fetch(`${this.base}/api/live-execution/preflight?${params.toString()}`, { method: "POST" })
    if (!res.ok) throw new Error("Preflight failed")
    return res.json()
  }

  async runDryRun(symbol: string, side = "BUY", quantity = 0, price?: number, stopLoss?: number, target?: number) {
    const params = new URLSearchParams()
    params.set("symbol", symbol)
    params.set("side", side)
    params.set("quantity", String(quantity))
    if (price) params.set("price", String(price))
    if (stopLoss) params.set("stop_loss", String(stopLoss))
    if (target) params.set("target", String(target))
    const res = await fetch(`${this.base}/api/live-execution/dry-run?${params.toString()}`, { method: "POST" })
    if (!res.ok) throw new Error("Dry run failed")
    return res.json()
  }

  async armCanary(reviewer: string, reason: string) {
    const params = new URLSearchParams()
    params.set("reviewer", reviewer)
    params.set("reason", reason)
    const res = await fetch(`${this.base}/api/live-execution/canary/arm?${params.toString()}`, { method: "POST" })
    if (!res.ok) throw new Error("Canary arm failed")
    return res.json()
  }

  async disarmCanary() {
    const res = await fetch(`${this.base}/api/live-execution/canary/disarm`, { method: "POST" })
    if (!res.ok) throw new Error("Canary disarm failed")
    return res.json()
  }

  async getCanaryStatus() {
    const res = await fetch(`${this.base}/api/live-execution/canary/status`)
    if (!res.ok) throw new Error("Failed to fetch canary status")
    return res.json()
  }

  async getOrders(limit = 50) {
    const res = await fetch(`${this.base}/api/live-execution/orders?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch orders")
    return res.json()
  }

  async getOrder(executionId: string) {
    const res = await fetch(`${this.base}/api/live-execution/orders/${executionId}`)
    if (!res.ok) throw new Error("Order not found")
    return res.json()
  }

  async getPositions() {
    const res = await fetch(`${this.base}/api/live-execution/positions`)
    if (!res.ok) throw new Error("Failed to fetch positions")
    return res.json()
  }

  async reconcile() {
    const res = await fetch(`${this.base}/api/live-execution/reconcile`, { method: "POST" })
    if (!res.ok) throw new Error("Reconciliation failed")
    return res.json()
  }

  async emergencyCancel(reason = "manual_emergency") {
    const res = await fetch(`${this.base}/api/live-execution/emergency-cancel?reason=${encodeURIComponent(reason)}`, { method: "POST" })
    if (!res.ok) throw new Error("Emergency cancel failed")
    return res.json()
  }

  async getLimits() {
    const res = await fetch(`${this.base}/api/live-execution/limits`)
    if (!res.ok) throw new Error("Failed to fetch limits")
    return res.json()
  }

  async getAudit(limit = 100) {
    const res = await fetch(`${this.base}/api/live-execution/audit?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch audit")
    return res.json()
  }
}

export const liveExecutionService = new LiveExecutionService()
