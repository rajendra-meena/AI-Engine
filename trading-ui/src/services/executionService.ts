"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class ExecutionService {
  private base = API_BASE

  async getStatus() {
    const res = await fetch(`${this.base}/api/execution/status`)
    if (!res.ok) throw new Error("Failed to fetch execution status")
    return res.json()
  }

  async getHealth() {
    const res = await fetch(`${this.base}/api/execution/health`)
    if (!res.ok) throw new Error("Failed to fetch execution health")
    return res.json()
  }

  async getPolicy(symbol = "", side = "", quantity = 0, price?: number, stopLoss?: number, target?: number) {
    const params = new URLSearchParams()
    if (symbol) params.set("symbol", symbol)
    if (side) params.set("side", side)
    if (quantity) params.set("quantity", String(quantity))
    if (price) params.set("price", String(price))
    if (stopLoss) params.set("stop_loss", String(stopLoss))
    if (target) params.set("target", String(target))
    const res = await fetch(`${this.base}/api/execution/policy?${params}`)
    if (!res.ok) throw new Error("Failed to fetch policy")
    return res.json()
  }

  async getKillSwitch() {
    const res = await fetch(`${this.base}/api/execution/kill-switch`)
    if (!res.ok) throw new Error("Failed to fetch kill switch")
    return res.json()
  }

  async activateKillSwitch(reason = "manual") {
    const res = await fetch(`${this.base}/api/execution/kill-switch/activate?reason=${encodeURIComponent(reason)}`, {
      method: "POST",
    })
    if (!res.ok) throw new Error("Failed to activate kill switch")
    return res.json()
  }

  async resetKillSwitch() {
    const res = await fetch(`${this.base}/api/execution/kill-switch/reset`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to reset kill switch")
    return res.json()
  }

  async getAudit(limit = 100) {
    const res = await fetch(`${this.base}/api/execution/audit?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch audit log")
    return res.json()
  }

  async getOrders(limit = 100) {
    const res = await fetch(`${this.base}/api/execution/orders?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch orders")
    return res.json()
  }

  async getOrder(orderId: string) {
    const res = await fetch(`${this.base}/api/execution/order/${orderId}`)
    if (!res.ok) throw new Error("Order not found")
    return res.json()
  }

  async getReconciliation() {
    const res = await fetch(`${this.base}/api/execution/reconciliation`)
    if (!res.ok) throw new Error("Failed to fetch reconciliation")
    return res.json()
  }

  async getPositionReconciliation() {
    const res = await fetch(`${this.base}/api/execution/positions/reconciliation`)
    if (!res.ok) throw new Error("Failed to fetch position reconciliation")
    return res.json()
  }

  async getConfigHash() {
    const res = await fetch(`${this.base}/api/execution/config-hash`)
    if (!res.ok) throw new Error("Failed to fetch config hash")
    return res.json()
  }

  async emergencyStop(reason = "Manual emergency stop") {
    const res = await fetch(`${this.base}/api/execution/emergency/stop?reason=${encodeURIComponent(reason)}`, {
      method: "POST",
    })
    if (!res.ok) throw new Error("Failed to trigger emergency stop")
    return res.json()
  }

  async emergencyRecover() {
    const res = await fetch(`${this.base}/api/execution/emergency/recover`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to recover from emergency stop")
    return res.json()
  }

  async simulate(mode = "happy_path") {
    const res = await fetch(`${this.base}/api/execution/simulate?mode=${mode}`, { method: "POST" })
    if (!res.ok) throw new Error("Simulation failed")
    return res.json()
  }

  async getSimulationScenarios() {
    const res = await fetch(`${this.base}/api/execution/simulate/scenarios`)
    if (!res.ok) throw new Error("Failed to fetch scenarios")
    return res.json()
  }

  // Legacy methods for backward compatibility
  async getMode() {
    const res = await fetch(`${this.base}/api/execution/mode`)
    if (!res.ok) throw new Error("Failed to fetch mode")
    return res.json()
  }

  async setMode(mode: string) {
    const res = await fetch(`${this.base}/api/execution/mode?mode=${mode}`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to set mode")
    return res.json()
  }

  async armLive() {
    const res = await fetch(`${this.base}/api/execution/arm-live`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to arm live")
    return res.json()
  }

  async disarmLive() {
    const res = await fetch(`${this.base}/api/execution/disarm-live`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to disarm")
    return res.json()
  }

  async getArmingStatus() {
    const res = await fetch(`${this.base}/api/execution/arming-status`)
    if (!res.ok) throw new Error("Failed to fetch arming status")
    return res.json()
  }

  async getHistory(limit = 50) {
    const res = await fetch(`${this.base}/api/execution/history?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch history")
    return res.json()
  }
}

export const executionService = new ExecutionService()
