/**
 * aiOrchestratorService.ts
 *
 * AI Orchestrator API client — provider health, metrics, cost tracking.
 */

import apiClient from "@/lib/api"

export interface AIProviderHealth {
  providers: Record<string, boolean>
  metrics: {
    totalRequests: number
    totalTokens: number
    totalCost: number
    averageLatency: number
    failedRequests: number
  }
}

export const aiOrchestratorService = {
  /** Get AI provider health status */
  async getHealth(): Promise<AIProviderHealth> {
    try {
      const { data } = await apiClient.get("/api/ai-orchestrator/health")
      return data
    } catch {
      return { providers: {}, metrics: { totalRequests: 0, totalTokens: 0, totalCost: 0, averageLatency: 0, failedRequests: 0 } }
    }
  },

  /** Get cost and usage metrics */
  async getMetrics(): Promise<AIProviderHealth["metrics"]> {
    try {
      const { data } = await apiClient.get("/api/ai-orchestrator/metrics")
      return data
    } catch {
      return { totalRequests: 0, totalTokens: 0, totalCost: 0, averageLatency: 0, failedRequests: 0 }
    }
  },

  /** Reset provider health (mark as healthy) */
  async resetHealth(provider?: string): Promise<void> {
    await apiClient.post("/api/ai-orchestrator/reset", { provider })
  },
}
