/**
 * mlService.ts — ML Engine API client.
 */

import apiClient from "@/lib/api"

export interface MLModel {
  id: string
  name: string
  modelType: string
  features: string[]
  params: Record<string, unknown>
  metrics: Record<string, number>
  featureImportance: Record<string, number>
  trainingDuration: number
  status: string
  version: number
  createdAt: string
}

export interface MLFeature {
  name: string
  type: string
  category: string
}

export interface MLEvaluation {
  accuracy: number
  precision: number
  recall: number
  f1: number
  truePositives: number
  falsePositives: number
  falseNegatives: number
  totalPredictions: number
}

export interface MLPrediction {
  prediction: number
  probability: number
  confidence: number
  modelId: string
}

export interface MLDriftResult {
  driftDetected: boolean
  driftScore: number
  driftedMetrics: Record<string, boolean>
  recommendRetrain: boolean
}

export const mlService = {
  async getFeatures(): Promise<MLFeature[]> {
    const { data } = await apiClient.get("/api/ml/features")
    return data
  },

  async getModels(): Promise<MLModel[]> {
    const { data } = await apiClient.get("/api/ml/models")
    return data
  },

  async getModel(id: string): Promise<MLModel> {
    const { data } = await apiClient.get(`/api/ml/models/${id}`)
    return data
  },

  async train(name: string, modelType = "xgboost", features: string[] = [], params: Record<string, unknown> = {}): Promise<MLModel> {
    const { data } = await apiClient.post("/api/ml/train", { name, modelType, features, params })
    return data
  },

  async evaluate(modelId: string, predictions: number[], actuals: number[]): Promise<MLEvaluation> {
    const { data } = await apiClient.post("/api/ml/evaluate", { modelId, predictions, actuals })
    return data
  },

  async predict(modelId: string, features: Record<string, number>): Promise<MLPrediction> {
    const { data } = await apiClient.post("/api/ml/predict", { modelId, features })
    return data
  },

  async getRegistry(): Promise<{ champion: MLModel | null; challengers: MLModel[]; totalModels: number }> {
    const { data } = await apiClient.get("/api/ml/registry")
    return data
  },

  async setChampion(modelId: string): Promise<void> {
    await apiClient.post(`/api/ml/registry/champion/${modelId}`)
  },

  async detectDrift(): Promise<MLDriftResult> {
    const { data } = await apiClient.get("/api/ml/drift")
    return data
  },
}
