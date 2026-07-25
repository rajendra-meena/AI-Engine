"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class LearningService {
  private base = API_BASE

  async getDashboard() {
    const res = await fetch(`${this.base}/api/learning/dashboard`)
    if (!res.ok) throw new Error("Failed to fetch learning dashboard")
    return res.json()
  }

  async getPredictions(limit = 100, offset = 0, symbol?: string, regime?: string) {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    if (symbol) params.set("symbol", symbol)
    if (regime) params.set("regime", regime)
    const res = await fetch(`${this.base}/api/learning/predictions?${params}`)
    if (!res.ok) throw new Error("Failed to fetch predictions")
    return res.json()
  }

  async getPerformance() {
    const res = await fetch(`${this.base}/api/learning/performance`)
    if (!res.ok) throw new Error("Failed to fetch performance")
    return res.json()
  }

  async getRegimes() {
    const res = await fetch(`${this.base}/api/learning/regimes`)
    if (!res.ok) throw new Error("Failed to fetch regimes")
    return res.json()
  }

  async getCalibration() {
    const res = await fetch(`${this.base}/api/learning/calibration`)
    if (!res.ok) throw new Error("Failed to fetch calibration")
    return res.json()
  }

  async getErrors() {
    const res = await fetch(`${this.base}/api/learning/errors`)
    if (!res.ok) throw new Error("Failed to fetch errors")
    return res.json()
  }

  async getRecommendations(status?: string) {
    const params = status ? `?status=${status}` : ""
    const res = await fetch(`${this.base}/api/learning/recommendations${params}`)
    if (!res.ok) throw new Error("Failed to fetch recommendations")
    return res.json()
  }

  async approveRecommendation(id: string) {
    await fetch(`${this.base}/api/learning/recommendations/${id}/approve`, { method: "POST" })
  }

  async rejectRecommendation(id: string, reason = "") {
    await fetch(`${this.base}/api/learning/recommendations/${id}/reject?reason=${encodeURIComponent(reason)}`, { method: "POST" })
  }

  async getBlocked() {
    const res = await fetch(`${this.base}/api/learning/blocked`)
    if (!res.ok) throw new Error("Failed to fetch blocked trades")
    return res.json()
  }

  async runLearning() {
    await fetch(`${this.base}/api/learning/run`, { method: "POST" })
  }
}

export const learningService = new LearningService()
