import apiClient from "@/lib/api"
import type { Prediction, PredictionStats } from "@/types"

export const predictionService = {
  async list(symbol?: string, limit = 50, status?: string): Promise<Prediction[]> {
    const { data } = await apiClient.get("/api/predictions", { params: { symbol, limit, status } })
    return data
  },

  async getStats(symbol?: string): Promise<PredictionStats> {
    const { data } = await apiClient.get("/api/predictions/stats", { params: symbol ? { symbol } : {} })
    return data
  },

  async create(prediction: Partial<Prediction>) {
    const { data } = await apiClient.post("/api/predictions", prediction)
    return data
  },

  async delete(id: number) {
    const { data } = await apiClient.delete(`/api/predictions/${id}`)
    return data
  },

  async checkResults() {
    const { data } = await apiClient.post("/api/predictions/check-results")
    return data
  },
}
