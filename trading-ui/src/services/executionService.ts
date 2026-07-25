"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class ExecutionService {
  private base = API_BASE

  async getStatus() {
    const res = await fetch(`${this.base}/api/execution/status`)
    if (!res.ok) throw new Error("Failed to fetch execution status")
    return res.json()
  }

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

  async validate(params: Record<string, unknown>) {
    const res = await fetch(`${this.base}/api/execution/validate`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params),
    })
    if (!res.ok) throw new Error("Validation failed")
    return res.json()
  }

  async execute(params: Record<string, unknown>) {
    const res = await fetch(`${this.base}/api/execution/execute`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params),
    })
    if (!res.ok) throw new Error("Execution failed")
    return res.json()
  }

  async getExecution(id: string) {
    const res = await fetch(`${this.base}/api/execution/${id}`)
    if (!res.ok) throw new Error("Execution not found")
    return res.json()
  }

  async getHistory(limit = 50) {
    const res = await fetch(`${this.base}/api/execution/history?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch history")
    return res.json()
  }
}

export const executionService = new ExecutionService()
