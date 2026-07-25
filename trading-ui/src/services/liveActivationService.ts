"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class LiveActivationService {
  private base = API_BASE

  async getStatus() {
    const res = await fetch(`${this.base}/api/live-activation/status`)
    if (!res.ok) throw new Error("Failed to fetch activation status")
    return res.json()
  }

  async getPrerequisites() {
    const res = await fetch(`${this.base}/api/live-activation/prerequisites`)
    if (!res.ok) throw new Error("Failed to fetch prerequisites")
    return res.json()
  }

  async validate(reviewer = "", reason = "") {
    const params = new URLSearchParams()
    if (reviewer) params.set("reviewer", reviewer)
    if (reason) params.set("reason", reason)
    const res = await fetch(`${this.base}/api/live-activation/validate${params.toString() ? "?" + params.toString() : ""}`, {
      method: "POST",
    })
    if (!res.ok) throw new Error("Validation failed")
    return res.json()
  }

  async arm(reviewer: string, reason: string, durationMinutes = 30) {
    const params = new URLSearchParams()
    params.set("reviewer", reviewer)
    params.set("reason", reason)
    params.set("activation_duration_minutes", String(durationMinutes))
    const res = await fetch(`${this.base}/api/live-activation/arm?${params.toString()}`, {
      method: "POST",
    })
    if (!res.ok) throw new Error("Arm failed")
    return res.json()
  }

  async start(confirmationToken: string) {
    const params = new URLSearchParams()
    params.set("confirmation_token", confirmationToken)
    const res = await fetch(`${this.base}/api/live-activation/start?${params.toString()}`, {
      method: "POST",
    })
    if (!res.ok) throw new Error("Start failed")
    return res.json()
  }

  async pause(reason = "") {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : ""
    const res = await fetch(`${this.base}/api/live-activation/pause${params}`, {
      method: "POST",
    })
    if (!res.ok) throw new Error("Pause failed")
    return res.json()
  }

  async revoke(reason = "") {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : ""
    const res = await fetch(`${this.base}/api/live-activation/revoke${params}`, {
      method: "POST",
    })
    if (!res.ok) throw new Error("Revoke failed")
    return res.json()
  }

  async killSwitch(reason = "") {
    const params = reason ? `?reason=${encodeURIComponent(reason)}` : ""
    const res = await fetch(`${this.base}/api/live-activation/kill-switch${params}`, {
      method: "POST",
    })
    if (!res.ok) throw new Error("Kill switch failed")
    return res.json()
  }

  async recover(reviewer: string, reason = "") {
    const params = new URLSearchParams()
    params.set("reviewer", reviewer)
    if (reason) params.set("reason", reason)
    const res = await fetch(`${this.base}/api/live-activation/recover?${params.toString()}`, {
      method: "POST",
    })
    if (!res.ok) throw new Error("Recovery failed")
    return res.json()
  }

  async getHistory(limit = 20) {
    const res = await fetch(`${this.base}/api/live-activation/history?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch history")
    return res.json()
  }

  async getAudit(limit = 100) {
    const res = await fetch(`${this.base}/api/live-activation/audit?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch audit")
    return res.json()
  }
}

export const liveActivationService = new LiveActivationService()
