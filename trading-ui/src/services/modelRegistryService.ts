/* eslint-disable @typescript-eslint/no-explicit-any */
"use client"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface ModelRegistryEntry {
  id: string
  name: string
  description: string
  version: string
  status: string
  model_type: string
  algorithm: string
  feature_set_version: string
  indicator_version: string
  parent_model_id: string
  created_at: string
  updated_at: string
}

export interface WalkForwardResult {
  window_index: number
  train_metrics: any
  val_metrics: any
  generalization: { generalization_score: number; classification: string; comparisons: any }
}

export interface PromotionRecommendation {
  decision: string
  score: number
  gates: { name: string; passed: boolean; value: any; threshold: any; detail: string }[]
  reasons: string[]
  warnings: string[]
  human_review_required: boolean
}

class ModelRegistryService {
  private base = API_BASE

  async listModels(status?: string): Promise<{ models: ModelRegistryEntry[]; total: number }> {
    let url = `${this.base}/api/models`
    if (status) url += `?status=${encodeURIComponent(status)}`
    const res = await fetch(url)
    if (!res.ok) throw new Error("Failed to list models")
    return res.json()
  }

  async getModel(id: string): Promise<ModelRegistryEntry> {
    const res = await fetch(`${this.base}/api/models/${encodeURIComponent(id)}`)
    if (!res.ok) throw new Error("Failed to fetch model")
    return res.json()
  }

  async getChampion(): Promise<ModelRegistryEntry> {
    const res = await fetch(`${this.base}/api/models/champion`)
    if (!res.ok) throw new Error("Failed to fetch champion")
    return res.json()
  }

  async getChallenger(): Promise<ModelRegistryEntry> {
    const res = await fetch(`${this.base}/api/models/challenger`)
    if (!res.ok) throw new Error("Failed to fetch challenger")
    return res.json()
  }

  async getComparison(): Promise<{ champion: ModelRegistryEntry; challenger: ModelRegistryEntry; comparison: any }> {
    const res = await fetch(`${this.base}/api/models/comparison`)
    if (!res.ok) throw new Error("Failed to fetch comparison")
    return res.json()
  }

  async getValidationHistory(modelId?: string): Promise<{ walk_forward_results: any[] }> {
    let url = `${this.base}/api/models/validation`
    if (modelId) url += `?model_id=${encodeURIComponent(modelId)}`
    const res = await fetch(url)
    if (!res.ok) throw new Error("Failed to fetch validation history")
    return res.json()
  }

  async getHistory(modelId?: string): Promise<{ history: any[] }> {
    let url = `${this.base}/api/models/history`
    if (modelId) url += `?model_id=${encodeURIComponent(modelId)}`
    const res = await fetch(url)
    if (!res.ok) throw new Error("Failed to fetch history")
    return res.json()
  }

  async getLineage(modelId: string): Promise<{ lineage: any[] }> {
    const res = await fetch(`${this.base}/api/models/lineage?model_id=${encodeURIComponent(modelId)}`)
    if (!res.ok) throw new Error("Failed to fetch lineage")
    return res.json()
  }

  async registerModel(name: string, version: string, modelType?: string, algorithm?: string): Promise<ModelRegistryEntry> {
    let url = `${this.base}/api/models/register?name=${encodeURIComponent(name)}&version=${encodeURIComponent(version)}`
    if (modelType) url += `&model_type=${encodeURIComponent(modelType)}`
    if (algorithm) url += `&algorithm=${encodeURIComponent(algorithm)}`
    const res = await fetch(url, { method: "POST" })
    if (!res.ok) throw new Error("Failed to register model")
    return res.json()
  }

  async setStatus(modelId: string, status: string, reason = ""): Promise<any> {
    const res = await fetch(`${this.base}/api/models/${encodeURIComponent(modelId)}/status?status=${encodeURIComponent(status)}&reason=${encodeURIComponent(reason)}`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to set status")
    return res.json()
  }

  async runValidation(modelId: string): Promise<any> {
    const res = await fetch(`${this.base}/api/models/validate?model_id=${encodeURIComponent(modelId)}`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to run validation")
    return res.json()
  }

  async promoteReview(challengerId: string): Promise<{ champion: any; challenger: any; recommendation: PromotionRecommendation }> {
    const res = await fetch(`${this.base}/api/models/promote-review?challenger_model_id=${encodeURIComponent(challengerId)}`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to promote review")
    return res.json()
  }

  async promoteChallenger(challengerId: string, reason = ""): Promise<any> {
    const res = await fetch(`${this.base}/api/models/promote?challenger_model_id=${encodeURIComponent(challengerId)}&reason=${encodeURIComponent(reason)}`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to promote")
    return res.json()
  }

  async rollbackReview(modelId: string, reason = "performance_degradation"): Promise<any> {
    const res = await fetch(`${this.base}/api/models/rollback-review?model_id=${encodeURIComponent(modelId)}&reason=${encodeURIComponent(reason)}`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to request rollback review")
    return res.json()
  }

  async executeRollback(rollbackId: string, reviewerId = "admin"): Promise<any> {
    const res = await fetch(`${this.base}/api/models/rollback-execute?rollback_id=${encodeURIComponent(rollbackId)}&reviewer_id=${encodeURIComponent(reviewerId)}`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to execute rollback")
    return res.json()
  }

  async archiveModel(modelId: string, reason = "archived"): Promise<any> {
    const res = await fetch(`${this.base}/api/models/archive?model_id=${encodeURIComponent(modelId)}&reason=${encodeURIComponent(reason)}`, { method: "POST" })
    if (!res.ok) throw new Error("Failed to archive model")
    return res.json()
  }
}

export const modelRegistryService = new ModelRegistryService()
