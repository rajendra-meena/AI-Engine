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

  async createPrediction(pred: Record<string, unknown>) {
    const res = await fetch(`${this.base}/api/learning/predictions`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(pred),
    })
    if (!res.ok) throw new Error("Failed to create prediction")
    return res.json()
  }

  async getPrediction(id: string) {
    const res = await fetch(`${this.base}/api/learning/predictions/${id}`)
    if (!res.ok) throw new Error("Failed to fetch prediction")
    return res.json()
  }

  async recordOutcome(predictionId: string, outcome: Record<string, unknown>) {
    const res = await fetch(`${this.base}/api/learning/predictions/${predictionId}/outcome`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(outcome),
    })
    if (!res.ok) throw new Error("Failed to record outcome")
    return res.json()
  }

  async getOutcomes(limit = 100, offset = 0) {
    const res = await fetch(`${this.base}/api/learning/outcomes?limit=${limit}&offset=${offset}`)
    if (!res.ok) throw new Error("Failed to fetch outcomes")
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

  async refreshCalibration() {
    const res = await fetch(`${this.base}/api/learning/calibration/refresh`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to refresh calibration")
    return res.json()
  }

  async getErrors() {
    const res = await fetch(`${this.base}/api/learning/errors`)
    if (!res.ok) throw new Error("Failed to fetch errors")
    return res.json()
  }

  async getAiVsMl() {
    const res = await fetch(`${this.base}/api/learning/ai-vs-ml`)
    if (!res.ok) throw new Error("Failed to fetch AI vs ML")
    return res.json()
  }

  async getRecommendations(status?: string, limit = 50) {
    const params = new URLSearchParams({ limit: String(limit) })
    if (status) params.set("status", status)
    const res = await fetch(`${this.base}/api/learning/recommendations?${params}`)
    if (!res.ok) throw new Error("Failed to fetch recommendations")
    return res.json()
  }

  async createRecommendation(rec: Record<string, unknown>) {
    const res = await fetch(`${this.base}/api/learning/recommendations`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rec),
    })
    if (!res.ok) throw new Error("Failed to create recommendation")
    return res.json()
  }

  async approveRecommendation(id: string) {
    const res = await fetch(`${this.base}/api/learning/recommendations/${id}/approve`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to approve")
    return res.json()
  }

  async rejectRecommendation(id: string, reason = "") {
    const res = await fetch(`${this.base}/api/learning/recommendations/${id}/reject?reason=${encodeURIComponent(reason)}`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to reject")
    return res.json()
  }

  async getBlocked() {
    const res = await fetch(`${this.base}/api/learning/blocked`)
    if (!res.ok) throw new Error("Failed to fetch blocked trades")
    return res.json()
  }

  async recordBlockedTrade(blocked: Record<string, unknown>) {
    const res = await fetch(`${this.base}/api/learning/blocked`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(blocked),
    })
    if (!res.ok) throw new Error("Failed to record blocked trade")
    return res.json()
  }

  async recordTradeFeedback(feedback: Record<string, unknown>) {
    const res = await fetch(`${this.base}/api/learning/trade-feedback`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(feedback),
    })
    if (!res.ok) throw new Error("Failed to record trade feedback")
    return res.json()
  }

  async getDataQuality() {
    const res = await fetch(`${this.base}/api/learning/data-quality`)
    if (!res.ok) throw new Error("Failed to fetch data quality")
    return res.json()
  }

  async runLearning() {
    const res = await fetch(`${this.base}/api/learning/run`, { method: "POST" })
    if (!res.ok) throw new Error("Learning run failed")
    return res.json()
  }
}

export const learningService = new LearningService()
